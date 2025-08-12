# core/report_utils.py

"""
Утилиты формирования итогового отчёта по проведённым тестам.

Основная точка входа — функция :func:`generate_summary`, которая принимает
словарь с путями к отдельным JSON/NPY‑файлам тестов и формирует сводный
'summary_<timestamp>.json' и краткий текстовый отчёт 'summary_<timestamp>.txt'
в папке пациента.

Формат входного словаря 'sel':

    sel = {
        "surname": "Иванов",
        "pmpwm" : Path(".../pmpwm_2025-08-05T12-30.json"),
        "mols"  : Path(".../mols_2025-08-05T12-15.json"),
        "spatial": Path(".../spatial_2025-08-05T12-45.npy"),
    }
"""

import json
from pathlib import Path
from datetime import datetime
from core.paths import OUTPUT_ROOT, sanitize
from core.pmpwm_analysis import analyse_cm
from core.spatial_analysis import analyse_spatial
import numpy as np


def generate_summary(sel: dict) -> Path:
    """
    Формирует сводный отчёт по результатам тестов с рекомендациями для КАЖДОГО мотора.
    
    Параметры
    ----------
    sel : dict
        Обязательные ключи:
        ``surname`` — фамилия пациента,
        ``pmpwm``   — путь к JSON‑файлу PM‑PWM‑теста.
        Необязательные: ``mols`` (JSON) и ``spatial`` (NPY).

    Возвращает
    ----------
    pathlib.Path
        Путь к созданному ``summary_<timestamp>.json``.
    """

    # ------------------------------------------------------------------
    # 1. Читаем входные файлы
    # ------------------------------------------------------------------

    # ---------- 1-A. PM-PWM -------------------------------------------
    with open(sel["pmpwm"], encoding="utf8") as f:
        src = json.load(f)

    pwm_values   = src["pwm_values"]
    conf_by_mtr  = {int(k): np.array(v)
                    for k, v in src["confusion_per_motor"].items()}
    
    # ---------- 1-B. MOLs ---------------------------------------------
    mols_data = None
    if sel.get("mols"):
        with open(sel["mols"], encoding="utf8") as f:
            mols_data = {int(k): int(v) for k, v in json.load(f).items()}  # {motor: pwm}
    
    # ---------- 1-C. Spatial (.npy) -----------------------------------
    spatial_data = None
    if sel.get("spatial"):
        answers = np.load(sel["spatial"]).tolist()  # [(true,pred)…]
        spatial_data = analyse_spatial(answers)

    # ------------------------------------------------------------------
    # 2. Каталог пациента и метка времени
    # ------------------------------------------------------------------

    surname_root = OUTPUT_ROOT / sanitize(sel["surname"])
    surname_root.mkdir(parents=True, exist_ok=True)
    ts           = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    # ------------------------------------------------------------------
    # 3. Анализируем каждый мотор PM‑PWM
    # ------------------------------------------------------------------
    
    summary_per_motor = {}
    for motor_id, cm in conf_by_mtr.items():
        summary_per_motor[motor_id] = analyse_cm(cm, pwm_values)

    # ------------------------------------------------------------------
    # 4. Сохраняем JSON и TXT
    # ------------------------------------------------------------------
    out_json = {
        "surname"   : sel["surname"],
        "datetime"  : ts,
        "mols"     : mols_data,
        "spatial"   : spatial_data,
        "pmpwm"    : {
            "pwm_values": pwm_values,
            "motors"    : summary_per_motor
        }
    }

    json_path = surname_root / f"summary_{ts}.json"
    json_path.write_text(json.dumps(out_json, ensure_ascii=False, indent=2),
                         encoding="utf8")

    # Человеко-читаемый TXT (кратко)
    txt_path = surname_root / f"summary_{ts}.txt"
    
    with open(txt_path, "w", encoding="utf8") as f:
        # 0) Фамилия
        f.write(f"Фамилия: {sel['surname']}\n\n")

        # 1) MOLs-тест
        f.write("===  MOLs-тест ===\n")
        if mols_data:
            for m, pwm in sorted(mols_data.items()):
                f.write(f"{m} → {pwm} PWM\n")
        else:
            f.write("Файл не выбран\n")
        f.write("\n")

        # 2) Spatial-тест
        f.write("===  Spatial-тест ===\n")
        if spatial_data:
            for reg, st in sorted(spatial_data["regions"].items()):
                acc = st["accuracy"] * 100
                f.write(f"{reg} область: {acc:.0f} %\n")
                if acc < 100:
                    f.write("    Ответы:\n")
                    for ans, n in st["answers"].items():
                        f.write(f"        {ans} область – {n}\n")
            f.write(f"\nСредняя точность: "
                    f"{spatial_data['mean_accuracy']*100:.1f} %\n")
        else:
            f.write("Файл не выбран\n")
        f.write("\n")

        # 3) PM-PWM-тест
        f.write("===  PM-PWM-тест ===\n")
        for m, r in sorted(summary_per_motor.items()):
            f.write(f"Мотор {m}: средняя точность {r['mean_accuracy']*100:4.1f} %\n")
            for k, a in r["accuracy"].items():
                f.write(f"  Уровень {k}: {a*100:4.1f} %\n")
            f.write("  Рекомендации:\n")
            for rec in r["recommendations"]:
                f.write(f"   • {rec}\n")
            f.write("\n")

    # Вызов функции, которая будет делать report по необходимым стандартам
    create_report()


    return json_path

def create_report():
    '''
    Эта функция будет первичный анализ превращать в итоговый отчёт
    '''
    return None