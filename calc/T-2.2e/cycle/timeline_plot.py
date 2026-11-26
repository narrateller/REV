"""Render the two interlock windows of the realistic cycle."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


INK = "#132b39"
DIM = "#4b6270"
MOTION = "#146b69"
HYDRAULIC = "#466e9c"
VERIFY = "#c27635"
GRID = "#d7e1e6"


def draw_timeline(cycle, path):
    reference = cycle["references"]["realistic"]
    image = Image.new("RGB", (1560, 520), "#f7fafc")
    canvas = ImageDraw.Draw(image)
    fonts = Path("C:/Windows/Fonts")
    regular = str(fonts / "arial.ttf")
    bold = str(fonts / "arialbd.ttf")
    title = ImageFont.truetype(bold, 38)
    heading = ImageFont.truetype(bold, 25)
    body = ImageFont.truetype(regular, 19)
    small = ImageFont.truetype(regular, 17)
    canvas.text((44, 30), "Совмещение поворота муфт с движениями пресса", font=title, fill=INK)
    canvas.text((45, 84), "Эталон A4VSO180, доза 0,83 кг и насыпная плотность 90 кг/м³",
                font=body, fill=DIM)

    end_rotate_s = cycle["actuator"]["turn_s"]
    left = (
        ("Муфты", [(reference["lock_start_s"], reference["lock_start_s"] + end_rotate_s, MOTION),
                   (reference["lock_start_s"] + end_rotate_s, reference["lock_confirmed_s"], VERIFY)]),
        ("Быстрый подвод", [(reference["prefill_start_s"], reference["earliest_verified_material_contact_s"], HYDRAULIC)]),
    )
    right = (
        ("Муфты", [(reference["unlock_start_s"], reference["unlock_start_s"] + end_rotate_s, MOTION),
                   (reference["unlock_start_s"] + end_rotate_s, reference["unlock_confirmed_s"], VERIFY)]),
        ("Выдача", [(reference["events"]["eject"]["start_s"], reference["eject_end_s"], HYDRAULIC)]),
        ("Подъём", [(reference["shoe_up_start_s"], reference["events"]["pre_up"]["end_s"], HYDRAULIC)]),
    )

    def panel(origin, title_text, time_range, step, event_rows, note, marker_s):
        left_px, right_px = origin + 184, origin + 696
        start_s, end_s = time_range

        def pixel(time_s):
            return left_px + (time_s - start_s) / (end_s - start_s) * (right_px - left_px)

        canvas.rounded_rectangle((origin, 131, origin + 722, 444), radius=13, outline=GRID, fill="white", width=2)
        canvas.text((origin + 21, 151), title_text, font=heading, fill=INK)
        for i in range(round((end_s - start_s) / step) + 1):
            tick_s = start_s + i * step
            tick = pixel(tick_s)
            canvas.line((tick, 198, tick, 359), fill=GRID, width=1)
            canvas.text((tick, 371), f"{tick_s:.2f}".replace(".", ","), font=small, fill=DIM, anchor="ma")
        for i, (label, segments) in enumerate(event_rows):
            y = 221 + i * 49
            canvas.text((origin + 21, y + 3), label, font=body, fill=INK)
            for begin_s, stop_s, fill in segments:
                a, b = pixel(max(start_s, begin_s)), pixel(min(end_s, stop_s))
                if b > a:
                    canvas.rectangle((a, y, b, y + 26), fill=fill)
        x = pixel(marker_s)
        for y in range(196, 360, 9):
            canvas.line((x, y, x, y + 4), fill=INK, width=1)
        canvas.text((origin + 21, 408), note, font=small, fill=DIM)
        canvas.text((right_px + 10, 371), "с", font=small, fill=DIM)

    panel(44, "Замыкание", (.62, .80), .03, left,
          "Пунктир отмечает самый ранний контакт с дозой.", reference["earliest_verified_material_contact_s"])
    panel(794, "Отпирание", (3.70, 4.10), .10, right,
          "Пунктир отмечает прохождение хвоста дозы через x = 220 мм.", reference["unlock_start_s"])
    for x, label, color in ((44, "Поворот муфт", MOTION), (249, "Подтверждение положения", VERIFY),
                            (582, "Гидравлическое движение", HYDRAULIC)):
        canvas.rectangle((x, 473, x + 19, 492), fill=color)
        canvas.text((x + 30, 473), label, font=body, fill=INK)
    image.save(path, format="PNG", optimize=True)

