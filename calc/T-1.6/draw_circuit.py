
"""Draw the ISO 1219 functional circuit using named cross-sheet connections."""
from collections import defaultdict
from html import escape
from math import ceil

from check_circuit import CIRCUIT, DESIGN, read_yaml

WIDTH = 1480
COLS = 3
COLUMN_WIDTH = 465
CARD_HEIGHT = 145
SYMBOLS = {
    "motor": '<circle r="17"/><text class="letter" y="5">M</text>',
    "fixed_pump": '<circle r="17"/><path d="M-6 3L6 3L0-8Z" class="solid"/>',
    "variable_pump": '<circle r="17"/><path d="M-6 3L6 3L0-8Z" class="solid"/>'
                     '<path d="M-22 22L22-22m-9 1l9-1-1 9"/>',
    "filter": '<path d="M-21 0L0-16L21 0L0 16Z"/><path d="M0-16V16" stroke-dasharray="2 3"/>',
    "cooler": '<path d="M-21 0L0-16L21 0L0 16Z M-7 4l8-16m2 5l-1-5-5 2 m2 10l8-16m2 5l-1-5-5 2"/>',
    "check_valve": '<path d="M-20 0h9l8-7m-8 7l8 7M6 0h14"/><circle cx="2" r="4"/>',
    "pilot_check": '<path d="M-20 0h9l8-7m-8 7l8 7M6 0h14M2 4v14" stroke-dasharray="0"/>'
                   '<circle cx="2" r="4"/>',
    "cylinder": '<rect x="-24" y="-13" width="44" height="26"/><path d="M-3-13v26m0-13h33M-17 13v8m28-8v8"/>',
    "accumulator": '<rect x="-11" y="-19" width="22" height="38" rx="11"/>'
                   '<path d="M-11 1h22M0 19v7"/>',
    "reservoir": '<path d="M-22-12v26h44v-26M-22 1h44M-10-17V7m18-24V7"/>',
    "pressurized_tank": '<rect x="-22" y="-15" width="44" height="30" rx="2"/>'
                        '<path d="M-22 1q11-9 22 0t22 0 M0-15v-8M0 15v8"/>',
    "gas_source": '<path d="M-9 17v-27q0-6 9-6t9 6v27z M0-16v-6h5"/>',
    "flow_sensor": '<circle r="14"/><path d="M-19 0h38m-16-5l5 5-5 5"/>',
    "pressure_sensor": '<circle r="13"/><path d="M-6 6l11-13m-4 2l4-2v5M0 13v8"/>',
    "position_sensor": '<rect x="-16" y="-10" width="32" height="20"/><path d="M-21 0h6M17 0h7M-6 6L6-6"/>',
    "controller": '<rect x="-17" y="-12" width="34" height="24"/><path d="M-25 0h8m34 0h8M-9 6L-3 1 1 4 9-6"/>',
    "orifice": '<path d="M-24 0h48m-29-8q7 8 0 16m10-16q-7 8 0 16"/>',
    "pipe": '<path d="M-24 0h48"/>',
    "deaerator": '<path d="M-18-11h36v22h-36zM-18 0h36"/><circle cx="-7" cy="-5" r="2"/>'
                  '<circle cx="3" cy="-7" r="1.5"/>',
    "safety_block": '<rect x="-23" y="-13" width="46" height="26" stroke-dasharray="4 3"/>'
                    '<path d="M-23 0h46M-8-5L2 5v-10L-8 5z M13 0v13"/>',
}
VALVE_TYPES = {
    "proportional_2_2", "poppet_2_2", "directional_4_3", "directional_3_2", "pressure_relief",
    "unloader", "pressure_reducing", "level_valve", "load_hold",
}
COLORS = {
    "pressure": "#a41f38", "work": "#a05813", "tank": "#236c8e", "prefill": "#116b6c",
    "pilot": "#714399", "drain": "#586473", "suction": "#2e6472",
    "cooling": "#2d7250", "gas": "#77682b",
}
LEGEND = {
    "pressure": "напор", "work": "рабочая", "tank": "слив", "prefill": "наполнение", "pilot": "пилот",
    "drain": "дренаж", "suction": "всасывание", "cooling": "охлаждение", "gas": "газ",
}


def txt(x, y, label, css="", anchor="start"):
    return (f'<text x="{x}" y="{y}" class="{css}" text-anchor="{anchor}">'
            f'{escape(str(label))}</text>')


def valve_symbol(kind, default_state):
    if kind == "directional_4_3":
        return ('<path d="M-27-9h54v18h-54zM-9-9v18M9-9v18M-9-4h5m-5 8h5m8-8h5m-5 8h5'
                'M-23 4l10-8m-4 0h4v4M-23-4l10 8m-4 0h4v-4'
                'M13 4V-4m-3 3l3-3 3 3M21-4v8m-3-3l3 3 3-3"/>')
    if kind in {"pressure_relief", "pressure_reducing"}:
        return ('<path d="M-11-10H11v20h-22zM-7 0H7M2-4l5 4-5 4M11 0h5l2-4 3 8 3-8 3 4h4"/>'
                '<path d="M-9 10v7h-13V0h11" stroke-dasharray="3 2"/>')
    if kind == "directional_3_2":
        return ('<path d="M-22-9h44v18h-44zM0-9v18M-16 4l10-8m-4 0h4v4'
                'M6-4l10 8m-4 0h4v-4M12 9v7"/>')
    blank = '<path d="M-16 0h10m-5-3v6"/>'
    flow = '<path d="M5 0h12m-4-4l4 4-4 4"/>'
    if default_state == "open":
        blank = '<path d="M6 0h10m-5-3v6"/>'
        flow = '<path d="M-17 0h12m-4-4l4 4-4 4"/>'
    proportional = '<path d="M-25 12l50-24m-8 0h8l-3 7"/>' if kind == "proportional_2_2" else ""
    return '<path d="M-22-9h44v18h-44zM0-9v18m22-9h4l2-3 3 6 3-3h3"/>' + blank + flow + proportional


def card(x, y, unit, item, lines):
    center_x, center_y = x + 232, y + 84
    title = f'{unit} · {item["label"]}'
    description = f'{item["series"]} · {item["size"]}'
    default = item.get("default_state")
    limits = []
    if default == "open":
        limits.append("НО")
    elif default == "bleed":
        limits.append("НО сброс ГА")
    if item["Q_L_min"]:
        limits.append(f'Q {item["Q_L_min"]:g} л/мин')
    if item["p_design_bar"] is not None:
        limits.append(f'p {item["p_design_bar"]:g} бар')
    if setpoints := item.get("setpoint"):
        limits.extend(f"{val:g} {unit_name}" for key, val in setpoints.items()
                      for unit_name in [("кВт" if key.endswith("_kW") else "бар")]
                      if key in {"shaft_kW", "oil_gauge_bar", "relief_bar", "accumulator_bar",
                                 "maximum_actual_trip_bar", "max_inlet_at_design_flow_bar"})
    if len(description) > 69:
        description = description[:68].rstrip() + "…"
    out = [f'<g id="element-{unit}"><title>{escape(title)} · {escape(item.get("note", ""))}</title>',
           f'<rect x="{x}" y="{y}" width="449" height="{CARD_HEIGHT - 8}" rx="7" class="card"/>',
           txt(x + 12, y + 21, title, "element"),
           txt(x + 12, y + 40, description, "detail"),
           txt(x + 12, y + 124, "   ·   ".join(limits), "detail")]
    if item["type"] in VALVE_TYPES:
        symbol = valve_symbol(item["type"], item.get("default_state"))
    else:
        symbol = SYMBOLS[item["type"]]
    out.append(f'<g transform="translate({center_x} {center_y})" class="symbol">{symbol}</g>')
    ports = list(item["ports"].items())
    left = ceil(len(ports) / 2)
    for index, (port, line) in enumerate(ports):
        is_left = index < left
        pos = index if is_left else index - left
        dx = -1 if is_left else 1
        count = left if is_left else len(ports) - left
        step = min(15, 68 / max(1, count - 1))
        pin_y = center_y + (pos - (count - 1) / 2) * step
        label_x = center_x + dx * 119
        icon_pin_x = center_x + dx * 37
        line_pin_x = center_x + dx * 112
        color = COLORS[lines[line]["kind"]]
        dashed = ' stroke-dasharray="4 3"' if lines[line]["kind"] in {"pilot", "drain", "gas"} else ""
        out.append(f'<path d="M{icon_pin_x} {pin_y:g}H{line_pin_x}" stroke="{color}"{dashed}/>')
        out.append(f'<circle cx="{line_pin_x}" cy="{pin_y:g}" r="3" fill="white" stroke="{color}"/>')
        out.append(f'<a href="#line-{line}">')
        out.append(txt(label_x, pin_y + 4, f"{port} · {line}", "port", "end" if is_left else "start"))
        out.append("</a>")
    if "sensor" in item:
        out.append(txt(x + 437, y + 124, item["sensor"], "detail", "end"))
    out.append("</g>")
    return out


def render(circuit):
    elements, lines = circuit["elements"], circuit["lines"]
    sections = defaultdict(list)
    line_ports = defaultdict(list)
    for unit, item in elements.items():
        sections[item["section"]].append((unit, item))
        for port, line in item["ports"].items():
            line_ports[line].append((unit, port))

    panels = []
    y = 141
    for key, name in circuit["sections"].items():
        members = sections[key]
        section_height = 53 + ceil(len(members) / COLS) * CARD_HEIGHT
        panels.append(f'<rect x="25" y="{y}" width="{WIDTH - 50}" height="{section_height}" rx="9" class="panel"/>')
        panels.append(txt(45, y + 31, name, "section"))
        for index, (unit, item) in enumerate(members):
            row, col = divmod(index, COLS)
            panels.extend(card(45 + col * COLUMN_WIDTH, y + 46 + row * CARD_HEIGHT, unit, item, lines))
        y += section_height + 15

    y += 14
    panels.append(txt(45, y, "Линии и подключения", "section"))
    y += 29
    for name, item in lines.items():
        tags = [f"{unit}.{port}" for unit, port in line_ports[name]]
        panels.append(f'<g id="line-{name}">')
        panels.append(f'<rect x="45" y="{y - 16}" width="1379" height="25" rx="4" fill="#edf2f5"/>')
        panels.append(txt(56, y, name, "element"))
        panels.append(txt(144, y, f'{LEGEND[item["kind"]]} · DN {item["DN_mm"]:g} · '
                                  f'{item["Q_L_min"]:g} л/мин · {item["p_design_bar"]:g} бар', "detail"))
        y_start = y
        for index in range(0, len(tags), 10):
            chunk = tags[index:index + 10]
            if index:
                y += 20
            panels.append(txt(503, y, "  ·  ".join(chunk), "detail"))
        panels.append("</g>")
        y = max(y + 31, y_start + 31)
    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {y + 20}" width="{WIDTH}" role="img" '
        'aria-labelledby="svg-title">',
        '<title id="svg-title">T-1.6 · Принципиальная гидросхема</title>',
        '<style>text{font-family:Arial,sans-serif;fill:#182b39}.header{font-size:32px;font-weight:bold}'
        '.section{font-size:20px;font-weight:bold}.element{font-size:15px;font-weight:bold}'
        '.detail{font-size:12px;fill:#455669}.port{font-size:12px;font-weight:bold}'
        '.panel{fill:#f2f6f8;stroke:#cbd7de}.card{fill:#fff;stroke:#dce5ea}'
        '.symbol{fill:none;stroke:#192e3a;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}'
        '.solid{fill:#192e3a}.letter{fill:#192e3a;stroke:none;text-anchor:middle;font-size:12px;font-weight:bold}'
        'a:hover .port{text-decoration:underline}</style>',
        f'<rect width="{WIDTH}" height="{y + 20}" fill="#fff"/>',
        txt(30, 46, "T-1.6 · Принципиальная гидросхема · круг 2", "header"),
        txt(31, 72, "ISO 1219-1/-2, упрощённые символы. Одинаковая метка линии соединяет порты. Нажмите метку для просмотра подключений.", "detail"),
    ]
    cursor = 32
    for key, label in LEGEND.items():
        dash = ' stroke-dasharray="4 3"' if key in {"pilot", "drain", "gas"} else ""
        head.extend([f'<path d="M{cursor} 105h22" stroke="{COLORS[key]}" stroke-width="2"{dash}/>',
                     txt(cursor + 28, 109, label, "detail")])
        cursor += len(label) * 8 + 54
    return "\n".join([*head, *panels, "</svg>", ""])


if __name__ == "__main__":
    (DESIGN / "T-1.6_circuit.svg").write_text(render(read_yaml(CIRCUIT)),
                                             encoding="utf-8", newline="\n")
