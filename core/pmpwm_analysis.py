# core/pmpwm_analysis.py

"""
Анализ результатов PM‑PWM‑теста.

Модуль предоставляет одну публичную функцию :func:`analyse_cm`, которая
принимает confusion‑matrix (матрицу ошибок распознавания мощностей) и список
PWM‑значений уровней, а возвращает словарь с метриками точности и
рекомендациями по коррекции шкалы мощности.
"""

from __future__ import annotations
import itertools
import numpy as np

# ---------------------------------------------------------------------------
# Внутренние вспомогательные функции
# ---------------------------------------------------------------------------

def _recommend(cm_norm: np.ndarray,
              acc: dict[int, float],
              pwm_vals: list[int]) -> list[str]:
    """
    Сформировать текстовые рекомендации на основе точности.

    Логика
    ------
    1. Если есть уровни с точностью < 75 %, предлагается их объединить или
       удалить, чтобы уменьшить путаницу.
    2. Если все уровни ≥ 75 %, ищем пары, где взаимная ошибка ≥ 10 % с обеих
       сторон, и советуем объединить такие уровни.
    3. В остальных случаях корректировка не требуется.
    """
    bad   = [lvl for lvl,a in acc.items() if a < .75]
    good  = [lvl for lvl in acc if lvl not in bad]
    rec   : list[str] = []

    # A) плохие уровни
    if bad:
        # Группируем подряд идущие уровни с низкой точностью
        bad.sort()
        groups = [list(g) for _,g in
                  itertools.groupby(bad, key=lambda x, c=itertools.count(): x-next(c))]
        for g in groups:
            if len(g) == 1:
                rec.append(f"Удалить уровень {g[0]} (PWM {pwm_vals[g[0]-1]}) — точность < 75 %")
            else:
                new_pwm = round(np.mean([pwm_vals[i-1] for i in g]))
                rec.append(f"Объединить уровни {g} в один (~PWM {new_pwm})")
        return rec

    # B) все уровни ≥ 75 % — ищем взаимные ошибки
    # Если «плохих» уровней нет, проверяем взаимную путаницу
    n = cm_norm.shape[0]
    pair_err = []
    for i in range(n):
        for j in range(i+1, n):
            if cm_norm[i,j] >= .10 and cm_norm[j,i] >= .10:
                pair_err.append((i+1, j+1))
    if pair_err:
        i,j = pair_err[0]
        new_pwm = round((pwm_vals[i-1] + pwm_vals[j-1]) / 2)
        rec.append(f"Сильная путаница между {i} и {j} → объединить, PWM ≈ {new_pwm}")
    else:
        rec.append("Корректировка не требуется (точность ≥ 75 %, нет сильных перекрёстных ошибок)")
    return rec

# ---------------------------------------------------------------------------
# Публичная функция
# ---------------------------------------------------------------------------

def analyse_cm(cm: np.ndarray,
               pwm_vals: list[int]) -> dict:
    """
    Анализ уже готовой confusion-matrix одного мотора.
    cm         – квадратный np.ndarray NxN (N = кол-во уровней)
    pwm_vals   – список PWM-значений уровней, длиной N
    save_png   – путь для сохранения нормированной heat-map (или None)
    """
    cm        = cm.astype(int)
    cm_norm   = cm / cm.sum(axis=1, keepdims=True).clip(min=1)
    acc       = {i+1: float(cm_norm[i, i])          for i in range(cm.shape[0])}
    mean_acc  = float(np.mean(list(acc.values())))
    recs      = _recommend(cm_norm, acc, pwm_vals)

    return {
        "confusion"      : cm.tolist(),                                 # исходная матрица
        "confusion_norm" : cm_norm.round(4).tolist(),                   # нормированная матрица
        "accuracy"       : {k: round(v, 4) for k, v in acc.items()},    # точность по уровням
        "mean_accuracy"  : round(mean_acc, 4),                          # средняя точность
        "recommendations": recs,                                        # список текстовых рекомендаций
    }