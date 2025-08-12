# core/paths.py

"""
Пути и имена файлов проекта.

Модуль отвечает за созда­ние каталогов пациента/теста и формирование
базовых имён выходных файлов с отметкой времени.
"""

from pathlib import Path
from datetime import datetime
import re

# Корневая директория, где лежат все результаты тестов
OUTPUT_ROOT = Path("outputs")

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def sanitize(name: str) -> str:
    """
    Убираем пробелы, точки и спец-символы из фамилии.
    Если после фильтрации строка пустая, возвращаем 'anon'.
    """
    return re.sub(r"[^A-Za-zА-Яа-я0-9_-]+", "_", name.strip()) or "anon"

def test_folder(surname: str, test: str) -> Path:
    """
    Возвращает .../outputs/<Фамилия>/<test>/  и гарантирует, что
    она существует.
    """
    p = OUTPUT_ROOT / sanitize(surname) / test
    p.mkdir(parents=True, exist_ok=True)
    return p

def build_file_base(surname: str, test: str) -> Path:
    """
    Базовое имя файлов БЕЗ расширения:
        outputs/<Фамилия>/<test>/<test>_<YYYY-MM-DDThh-mm-ss>
    """
    ts   = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    base = test_folder(surname, test) / f"{test}_{ts}"
    return base
