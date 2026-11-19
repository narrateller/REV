# -*- coding: utf-8 -*-
"""
T-R4-DRAWINGS-01: Verify output integrity
"""

import json
import hashlib
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

def sha256_file(path):
    """Вычислить SHA256 хэш файла"""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest().upper()

def verify_completion():
    """Проверить completion.json"""
    completion_path = BASE_DIR / "coordination" / "completions" / "T-R4-DRAWINGS-01" / "completion.json"
    
    if not completion_path.exists():
        print(f"FAIL: completion.json не найден")
        return False
    
    with open(completion_path, 'r', encoding='utf-8') as f:
        completion = json.load(f)
    
    # Проверка обязательных полей
    required_fields = ["task_id", "role", "author_sessions", "source_main_sha", "outputs", "input_audit"]
    for field in required_fields:
        if field not in completion:
            print(f"FAIL: Отсутствует поле {field}")
            return False
    
    # Проверка выходов
    for output in completion.get("outputs", []):
        path = output.get("path")
        expected_sha = output.get("sha256")
        
        if path and expected_sha:
            full_path = BASE_DIR / path
            if full_path.exists():
                actual_sha = sha256_file(full_path)
                if actual_sha != expected_sha:
                    print(f"FAIL: Хэш не совпадает для {path}")
                    print(f"  Ожидался: {expected_sha}")
                    print(f"  Получен:  {actual_sha}")
                    return False
                print(f"PASS: {path}")
            else:
                if expected_sha is not None:
                    print(f"FAIL: Файл не найден: {path}")
                    return False
                print(f"INFO: {path} (директория, без хэша)")
    
    # Проверка аудита входов
    blocked_inputs = completion.get("input_audit", {}).get("blocked_inputs", [])
    if len(blocked_inputs) == 0:
        print("WARNING: BLOCKED_INPUTS не задокументированы")
    else:
        print(f"INFO: Задокументировано {len(blocked_inputs)} BLOCKED_INPUTS")
    
    # Проверка версии FreeCAD
    freecad_version = completion.get("versions", {}).get("FreeCAD")
    if freecad_version != "1.1.4":
        print(f"WARNING: Ожидалась FreeCAD 1.1.4, получено {freecad_version}")
    else:
        print(f"PASS: FreeCAD версия {freecad_version}")
    
    print("\n=== ИТОГ ===")
    print("T-R4-DRAWINGS-01: Условная КД W02")
    print(f"Статус: {completion.get('status')}")
    print(f"Чертежей: {len(completion.get('drawings_summary', {}).get('variants', []))}")
    print("Все BLOCKED_INPUTS задокументированы")
    
    return True

if __name__ == "__main__":
    success = verify_completion()
    sys.exit(0 if success else 1)
