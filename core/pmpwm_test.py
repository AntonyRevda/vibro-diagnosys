# core/pmpwm_test.py

"""
PM‑PWM‑тест

Пациенту предъявляется одиночный импульс с одной из заранее заданных
мощностей (PWM). Его задача — выбрать субъективный «уровень силы» (1…N).

Модуль реализует класс :class:`PMPWMWorker`, работающий в отдельном потоке
Qt. Класс управляет вибробоксом, собирает ответы и формирует результаты в
виде confusion‑matrix и основных метрик точности.
"""

from __future__ import annotations
import random, time
from typing import Dict, List, Sequence

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from core.serial_api import VibroBox


class PMPWMWorker(QThread):
    """
    Фоновый поток, выполняющий PM‑PWM‑тест.

    Сигналы класса
    --------------
    progress(int motor_idx, int done, int total)
        Ход воспроизведения для текущего мотора.
    awaitingAnswer()
        Отправлен импульс, ожидаем ответ пациента.
    finished(dict)
        Словарь с результирующими метриками и матрицей ошибок.
    """
    progress        = pyqtSignal(int, int, int)
    awaitingAnswer  = pyqtSignal()
    finished        = pyqtSignal(dict)

    motorFinished   = pyqtSignal(int)

    def __init__(self, vibro: VibroBox, hyps: Dict, motors: Sequence[int]):
        super().__init__()
        self.vibro  = vibro
        self.hyps   = hyps
        self.motors = list(motors)
        self._answer: int | None = None
        self._stop  = False

        self.results: dict[int, list[tuple[int, int]]] = {}

    # ------------------------------------------------------------------
    # Интерфейс для GUI
    # ------------------------------------------------------------------

    def set_answer(self, val: int):
        """Получить ответ пациента (уровень 1…N)."""
        self._answer = val

    def stop(self):
        """Запросить досрочную остановку теста."""
        self._stop = True

    # ------------------------------------------------------------------
    # Основной алгоритм (QThread.run)
    # ------------------------------------------------------------------

    def run(self):
        """Запустить PM‑PWM‑тест последовательно для указанного списка моторов."""
        h          = self.hyps
        pwm_values = h['pmpwm_pwm_values']
        repeats    = h['pmpwm_repeats']
        n_levels   = len(pwm_values)

        # Итоговые данные
        answers: list[tuple[int, int]] = []
        
        # Локальный подсчёт только для одного мотора
        local_total = n_levels * repeats

        # Подготовка последовательности PWM для каждого мотора
        for motor in self.motors:
            seq = pwm_values * repeats
            random.shuffle(seq)

            # Обнуляем, если «переписываем» мотор
            self.results[motor] = []

            for step_local, pwm in enumerate(seq, start=1):

                # 0) Сообщаем GUI о текущем шаге
                self.progress.emit(motor, step_local, local_total)

                # 1) Вибрация
                arr = np.zeros(self.vibro.n_motors, dtype=np.uint8)
                arr[motor] = pwm
                self.vibro.set_pwm_values(arr)
                time.sleep(h.get('time_sleep_param', 0.25))
                self.vibro.reset_pwm_values()

                # 2) Ждём ответ
                self._answer = None
                self.awaitingAnswer.emit()
                while self._answer is None and not self._stop:
                    self.msleep(10)
                if self._stop:
                    self.vibro.reset_pwm_values()
                    return

                # 3) Записываем ответ
                true_level = pwm_values.index(pwm) + 1
                self.results[motor].append((true_level, int(self._answer)))

                time.sleep(0.35)

            # 5) мотор завершён
            self.motorFinished.emit(motor)

        # Индикация конца теста
        self.vibro.begin_end_indicator()

        # ------------------------------------------------------------------
        # Пост‑обработка результатов
        # ------------------------------------------------------------------

        answers = sum(self.results.values(), [])

        correct = sum(1 for t, p in answers if t == p)

        levels = n_levels
        cm = np.zeros((levels, levels), dtype=int)
        for t, p in answers:
            cm[t-1, p-1] += 1

        per_level_acc = cm.diagonal() / cm.sum(axis=1).clip(min=1)

        result = {
            'answers': answers,
            'accuracy': float(correct / len(answers)),
            'pwm_values': pwm_values,
            'repeats'   : repeats,
            'confusion' : cm.tolist(),
            'per_level_accuracy': per_level_acc.tolist(),
            'motors'    : self.motors,
        }

        self.finished.emit(result)