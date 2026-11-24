from datetime import datetime, timedelta, timezone
import re

from ops.lib.config import RunnerError
from ops.lib.io import file_lock, read_json, write_json


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
LIMIT = re.compile(r"\b(?:usage limit|try again at)\b", re.IGNORECASE)
CLOCK = r"(?P<hour>\d{1,2}):(?P<minute>\d{2})(?:\s*(?P<meridiem>am|pm)\b)?"
MONTH = r"(?P<month>Jan\w*|Feb\w*|Mar\w*|Apr\w*|May|Jun\w*|Jul\w*|Aug\w*|Sep\w*|Oct\w*|Nov\w*|Dec\w*)\b"
DAY = r"(?P<day>\d{1,2})(?:st|nd|rd|th)?"
YEAR = r"(?:[ ,]+(?P<year>\d{4})\b)?"
ZONE = r"(?:\s*(?P<zone>UTC|GMT|Z|[+-]\d{2}:?\d{2})\b)?"
RESET = re.compile(rf"\btry again at\s+{CLOCK}(?:\s+on\s+{DAY}\s+{MONTH}{YEAR})?{ZONE}", re.I)
RESET_DATE_FIRST = re.compile(rf"\btry again at\s+{MONTH}\s+{DAY}{YEAR}[ ,]+(?:at\s+)?{CLOCK}{ZONE}", re.I)
MONTHS = {name: index for index, name in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1
)}
DEFAULT_COOLDOWN = timedelta(hours=1)


def _reset_time(match, now):
    parts = match.groupdict()
    zone = parts["zone"]
    tz = now.tzinfo
    if zone:
        if zone.upper() in {"UTC", "GMT", "Z"}:
            tz = timezone.utc
        else:
            digits = zone[1:].replace(":", "")
            sign = 1 if zone[0] == "+" else -1
            tz = timezone(sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:])))
    local_now = now.astimezone(tz)
    hour, minute = int(parts["hour"]), int(parts["minute"])
    meridiem = parts["meridiem"]
    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError("invalid 12-hour time")
        hour = hour % 12 + (12 if meridiem.lower() == "pm" else 0)
    if parts["month"]:
        year = int(parts["year"]) if parts["year"] else local_now.year
        month, day = MONTHS[parts["month"][:3].lower()], int(parts["day"])
        reset = datetime(year, month, day, hour, minute, tzinfo=tz)
        if not parts["year"] and reset < local_now - timedelta(days=180):
            reset = reset.replace(year=year + 1)
    else:
        reset = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if reset <= local_now:
            reset += timedelta(days=1)
    if reset <= local_now:
        raise ValueError("reset time already passed")
    return reset.astimezone(timezone.utc)


def detect_limit(output, now=None):
    """Return an aware UTC reset time for a quota error, or None."""
    clean = ANSI.sub("", output)
    if not LIMIT.search(clean):
        return None
    now = now if now is not None else datetime.now().astimezone()
    for pattern in (RESET_DATE_FIRST, RESET):
        for match in pattern.finditer(clean):
            try:
                return _reset_time(match, now)
            except (ValueError, OverflowError):
                continue
    return (now + DEFAULT_COOLDOWN).astimezone(timezone.utc)


class Quota:
    def __init__(self, path):
        self.path = path

    def _read(self):
        try:
            data = read_json(self.path)
        except FileNotFoundError:
            return {}
        if not isinstance(data, dict):
            raise RunnerError(f"{self.path}: expected a backend quota mapping")
        return data

    @staticmethod
    def _until(entry):
        until = datetime.fromisoformat(entry["exhausted_until"])
        if until.tzinfo is None:
            raise ValueError("quota reset time lacks time zone")
        return until

    def available(self, backends, now):
        data = self._read()
        exhausted = []
        for backend in backends:
            try:
                until = self._until(data[backend.alias]) if backend.alias in data else now
            except (KeyError, TypeError, ValueError) as error:
                raise RunnerError(f"{self.path}: invalid quota entry for {backend.alias}") from error
            if until <= now:
                return backend, None
            exhausted.append(until)
        return None, min(exhausted)

    def exhaust(self, alias, until):
        with file_lock(self.path.with_suffix(".lock"), timeout_s=10):
            data = self._read()
            if alias in data:
                until = max(until, self._until(data[alias]))
            data[alias] = {"exhausted_until": until.isoformat()}
            write_json(self.path, data)
