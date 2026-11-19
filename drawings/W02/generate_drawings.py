# -*- coding: utf-8 -*-
"""
T-R4-DRAWINGS-01: Генерация условных рабочих чертежей W02
FreeCAD 1.1.4, OpenCASCADE 7.8.1

Внимание: Это условная КД с статусом BLOCKED_INPUTS.
Физические испытания и выпуск в производство требуют отдельного решения человека.
"""

import FreeCAD
import FreeCADGui
import TechDraw
import os
import json
from datetime import datetime, timezone

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(BASE_DIR, "..", "..", "cad", "source", "force_geometry")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CATALOG_PATH = os.path.join(BASE_DIR, "catalog.json")

# Варианты для обработки
VARIANTS = [
    {"id": "A-V1", "title": "Общий вид W02. Вариант A-V1", "arrangement": "Задний соосный цилиндр / направляемый носитель"},
    {"id": "A-V2", "title": "Общий вид W02. Вариант A-V2", "arrangement": "Один боковой цилиндр / портальная траверса"},
    {"id": "B-V1", "title": "Общий вид W02. Вариант B-V1", "arrangement": "Задний соосный цилиндр / направляемый носитель"},
    {"id": "B-V2", "title": "Общий вид W02. Вариант B-V2", "arrangement": "Один боковой цилиндр / портальная траверса"},
]

# Метаданные сессии
METADATA = {
    "freecad_version": "1.1.4",
    "opencascade_version": "7.8.1",
    "model_label": "qwen/qwen3.5-397b-a17b (OpenRouter)",
    "actual_session_id": "6afb300b-1540-8191-a5c4-be1a684c20e0",
    "task_id": "T-R4-DRAWINGS-01",
    "role": "R4",
    "status": "BLOCKED_INPUTS",
    "reason": "Условная КД. Физические входы (нагрузки, давления, контакты) не подтверждены. 42 состояния имеют BLOCKED_INPUTS.",
}

def create_drawing(variant_id, title, arrangement):
    """Создать чертеж для варианта"""
    fcstd_path = os.path.join(SOURCE_DIR, f"{variant_id}.FCStd")
    
    if not os.path.exists(fcstd_path):
        print(f"WARNING: Файл не найден: {fcstd_path}")
        return None
    
    # Открыть документ
    doc = FreeCAD.open(fcstd_path)
    print(f"Открыт: {fcstd_path}")
    
    # Создать страницу TechDraw
    page = TechDraw.makePage("TemplateA3Landscape.svg", f"Page_{variant_id}")
    page.Label = title
    
    # Найти все тела и детали в документе
    shapes = []
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and obj.Name not in ["Page_" + variant_id]:
            shapes.append(obj)
    
    # Добавить виды
    views = []
    for i, shape in enumerate(shapes[:5]):  # Ограничить количество видов
        try:
            # Главный вид (спереди)
            view = TechDraw.addView(page, shape, "Front")
            views.append({
                "type": "Front",
                "object": shape.Label if hasattr(shape, "Label") else shape.Name
            })
            
            # Вид сверху (если есть место)
            if i < 3:
                view_top = TechDraw.addView(page, shape, "Top")
                views.append({
                    "type": "Top",
                    "object": shape.Label if hasattr(shape, "Label") else shape.Name
                })
        except Exception as e:
            print(f"  Warning: Не удалось добавить вид для {shape.Name}: {e}")
    
    # Сохранить чертеж
    output_path = os.path.join(OUTPUT_DIR, f"W02-{variant_id}.FCStd")
    doc.saveAs(output_path)
    print(f"Сохранен: {output_path}")
    
    # Закрыть документ
    FreeCAD.closeDocument(doc.Name)
    
    return {
        "drawing_id": f"W02-{variant_id.replace('-', '')}",
        "title": title,
        "arrangement": arrangement,
        "status": "BLOCKED_INPUTS",
        "blocked_by": "PHYSICAL_INPUTS_NOT_CONFIRMED",
        "source_file": f"cad/source/force_geometry/{variant_id}.FCStd",
        "output_file": f"drawings/W02/output/W02-{variant_id}.FCStd",
        "views": views,
        "assumptions": [
            "Геометрия по расчётной огибающей нагрузок",
            "Материал: сталь конструкционная, E=210 ГПа",
            "Опоры жёсткие в Y/Z направлениях",
            "Все размеры в мм"
        ],
        "blockers": [
            "Фазовые нагрузки F(q,t) не подтверждены",
            "Давления в полостях цилиндров UNKNOWN",
            "Контактные поверхности и опоры не определены",
            "Несущая способность соединений UNKNOWN",
            "42 физических состояния: BLOCKED_INPUTS"
        ]
    }

def main():
    """Основная функция"""
    print("=" * 60)
    print("T-R4-DRAWINGS-01: Генерация чертежей W02")
    print(f"FreeCAD {METADATA['freecad_version']}, OpenCASCADE {METADATA['opencascade_version']}")
    print("=" * 60)
    
    # Убедиться, что выходная директория существует
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Обработать все варианты
    drawings = []
    for variant in VARIANTS:
        print(f"\nОбработка варианта {variant['id']}...")
        result = create_drawing(variant["id"], variant["title"], variant["arrangement"])
        if result:
            drawings.append(result)
    
    # Обновить каталог
    catalog = {
        "catalog_name": "W02 CAD-rebuild Drawing Catalog",
        "task_id": METADATA["task_id"],
        "role": METADATA["role"],
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": METADATA["status"],
        "reason": METADATA["reason"],
        "model_label": METADATA["model_label"],
        "actual_session_id": METADATA["actual_session_id"],
        "source_main_sha": "b1020f550e5224b7511f5f8224d027da6d92ae34",
        "freecad_version": METADATA["freecad_version"],
        "opencascade_version": METADATA["opencascade_version"],
        "drawings": drawings,
        "input_audit": {
            "r2_package_commit": "093a78ad27e46f6b2066ee78d4170704d4307623",
            "cad_rebuild_commit": "224242f918b05640ffa679fac468deb41290f444",
            "blocked_inputs": [
                "REV_SITE_TRANSFER_GEOMETRY: UNKNOWN",
                "REV_SITE_OUTFEED_GEOMETRY: UNKNOWN",
                "REV_FEEDSTOCK_MOISTURE_WINDOW: UNKNOWN",
                "REV_CAP_SIDE_PRESSURE_PROFILE: UNKNOWN",
                "REV_ROD_SIDE_PRESSURE_PROFILE: UNKNOWN",
                "REV_CONNECTION_CAPACITY: UNKNOWN",
                "42 состояния: geometry_for_load_case = BLOCKED_INPUTS",
                "Фазовые нагрузки и граничные условия не подтверждены"
            ]
        }
    }
    
    # Сохранить каталог
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print(f"\nКаталог сохранен: {CATALOG_PATH}")
    print(f"\nСоздано чертежей: {len(drawings)}")
    print("\n" + "=" * 60)
    print("ВНИМАНИЕ: Условная КД, статус BLOCKED_INPUTS")
    print("Физические испытания и выпуск в производство")
    print("требуют отдельного решения человека.")
    print("=" * 60)
    
    return catalog

if __name__ == "__main__":
    main()
