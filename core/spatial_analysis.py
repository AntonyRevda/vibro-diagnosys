# core/spatial_analysis.py

"""
Анализ ответов Spatial‑теста (распознавание областей).

Функция :func:`analyse_spatial` принимает последовательность кортежей
``(true_region, predicted_region)``, агрегирует статистику по каждой зоне и
возвращает структуру данных со сводной точностью и распределением ответов.
"""

from __future__ import annotations
from collections import defaultdict
from typing import Iterable

def analyse_spatial(answers: Iterable[tuple[int,int]]) -> dict:
    """
    Собирает статистику по Spatial‑тесту.

    Параметры
    ----------
    answers : Iterable[tuple[int, int]]
        Итератор кортежей ``(ожидаемая_область, ответ_пациента)``.

    Возвращает
    ----------
    dict
        Словарь со статистикой по областям и средней точностью.
    """
    # --- 1. Агрегация по областям ------------------------------------
    stats: dict[int, dict] = {}
    for true, pred in answers:
        st = stats.setdefault(true,
                {'total': 0, 'correct': 0,
                 'answers': defaultdict(int)})
        st['total']   += 1
        st['correct'] += int(true == pred)
        st['answers'][pred] += 1

    # --- 2. Подсчёт точности и сортировка ---------------------------
    for r, st in stats.items():
        st['accuracy'] = st['correct'] / max(1, st['total'])
        st['answers']  = dict(sorted(st['answers'].items()))

    # --- 3. Средняя точность ----------------------------------------
    mean_acc = (sum(st['correct'] for st in stats.values()) /
                max(1, sum(st['total']   for st in stats.values())))

    return {'regions': stats, 'mean_accuracy': mean_acc}
