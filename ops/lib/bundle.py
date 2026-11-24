import json

from ops.lib.config import BUNDLE_FILES, RunnerError
from ops.lib.io import atomic_text, parse_json
from ops.lib.workspace import contained_path


REVIEW_DIFF_BYTES = 60_000


def collect_files(worktree, run_dir):
    metrics = {}
    defects = []
    for name in BUNDLE_FILES:
        try:
            source = contained_path(worktree, name)
            if source.is_symlink() or not source.is_file():
                raise ValueError("expected regular file")
            payload = source.read_bytes()
            content = payload.decode("utf-8-sig")
            if name == "report.md":
                if not content.strip():
                    raise ValueError("empty report")
            else:
                data = parse_json(content)
                if not isinstance(data, dict):
                    raise ValueError("expected JSON object")
                if name == "metrics.json":
                    metrics = data
            (run_dir / name).write_bytes(payload)
        except (OSError, ValueError, RunnerError) as error:
            defects.append(f"{name}: {error}")
    return metrics, defects


def review_package(root, card, run_dir, meta, metrics, gates, diffstat):
    with (run_dir / "patch.diff").open("rb") as stream:
        raw = stream.read(REVIEW_DIFF_BYTES + 1)
    truncated = len(raw) > REVIEW_DIFF_BYTES
    excerpt = raw[:REVIEW_DIFF_BYTES]
    if truncated and b"\n" in excerpt:
        excerpt = excerpt.rsplit(b"\n", 1)[0] + b"\n"
    if excerpt and not excerpt.endswith(b"\n"):
        excerpt = excerpt[:REVIEW_DIFF_BYTES - 1] + b"\n"
    excerpt = excerpt.decode("utf-8", errors="ignore")
    mode = "dry-run" if meta["dry_run"] else "codex"
    content = [
        f"# {card.id} — PASS",
        f"- Режим **{mode}**",
        f"- Этап {card.data.get('stage', '—')} · роль {card.data['role']}",
        f"- Бэкенд {meta['backend']} · модель {meta['model']} · effort {meta['reasoning_effort']}",
        f"- Раунд {meta['round']} · ResultBundle {run_dir.relative_to(root).as_posix()}",
        card.data["objective"].strip(),
        "## Метрики\n\n~~~json\n" + json.dumps(metrics, ensure_ascii=False, indent=2) + "\n~~~",
        "## Гейты\n\n" + "\n".join(
            f"- {gate['id']} **{gate['status']}**" + (
                f" · {gate['details']['reason']}" if gate["details"].get("reason") else ""
            )
            for gate in gates
        ),
        "## Diffstat\n\n" + ("\n".join(f"    {line}" for line in diffstat.splitlines()) or "Пустой diff."),
        "## Фрагмент diff\n\n~~~diff\n" + excerpt + "~~~",
    ]
    if truncated:
        content.append("Полный diff сохранён в ResultBundle.")
    result = "\n\n".join(content) + "\n"
    atomic_text(run_dir / "review.md", result)
    queued = root / "ops" / "review_queue" / f"{card.id}.md"
    if meta["dry_run"] and queued.exists():
        if "- Режим **dry-run**" not in queued.read_text(encoding="utf-8").splitlines()[:5]:
            return run_dir / "review.md"
    atomic_text(queued, result)
    return queued
