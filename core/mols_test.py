# core/mols_test.py

"""
MOLs‑тест (Minimum Observable Levels) — фоновый поток PyQt6.

Модуль содержит класс :class:`MolsWorker`, выполняющий тест определения
минимально ощущаемых порогов для каждого мотора вибробокса.
"""

import random
import time
from typing import Dict, List

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from .serial_api import VibroBox

class MolsWorker(QThread):
    """
    Фоновый поток, выполняющий MOLs‑тест.

    Параметры
    ----------
    vibro : VibroBox
        Экземпляр класса, управляющий аппаратной частью.
    hyps : dict[str, Any]
        Словарь гиперпараметров (см. ``core.config.default_hyps``).

    Сигналы
    -------
    progress(int, int, int, str)
        motor_idx, текущий шаг, общее число шагов, текст
        «Увеличение/Уменьшение».
    vibrationStarted()
        Начало вибрации.
    awaitingAnswer()
        Запрос ответа пациента.
    finished(dict[int, int])
        Завершение теста, словарь «мотор → усреднённый порог PWM».
    """

    progress = pyqtSignal(int, int, int, str)
    vibrationStarted   = pyqtSignal()
    awaitingAnswer     = pyqtSignal()
    finished = pyqtSignal(dict)

    def __init__(self, vibro: VibroBox, hyps: Dict):
        super().__init__()
        self.vibro = vibro
        self.hyps = hyps
        self._stop = False

    # ------------------------------------------------------------------
    # Основной алгоритм
    # ------------------------------------------------------------------

    def run(self):
        results: Dict[int, List[int]] = {}
        motors = range(self.hyps['num_motor_start'],
                       self.hyps['num_motor_end'] + 1,
                       self.hyps['use_motors_step'])

        total_steps = len(motors) * self.hyps['exps_for_each_motor'] * 2
        done = 0

        for m in motors:
            streams = [0, 1] * self.hyps['exps_for_each_motor']
            random.shuffle(streams)
            for direction in streams:
                if self._stop:
                    return

                # === Сначала: считаем текущий шаг и сразу шлём его + режим в UI ===
                done += 1
                mode_text = ('Уменьшение мощности' if direction == 1 else 'Увеличение мощности')
                self.progress.emit(m, done, total_steps, mode_text)

                # === 1) Сигналим «ВИБРАЦИЯ» ===
                self.vibrationStarted.emit()
                
                # === 2) Выполняем тест для этого направления ===
                pwm = (self._downstream if direction == 1 else self._upstream)(m)

                if pwm == -1:           # прервано внутри _probe
                    return              # выходим без индикатора конца

                results.setdefault(m, []).append(pwm)

                # === 3) Индикатор конца и пауза ===
                self.vibro.begin_end_indicator()
                time.sleep(0.5)
                

        # Усредняем пороги и отдаём результат
        results_mean = {k: int(round(np.mean(v))) for k, v in results.items()}
        self.finished.emit(results_mean)

    # ------------------------------------------------------------------
    # Частные методы
    # ------------------------------------------------------------------

    def _downstream(self, motor_idx: int) -> int:
        """Проход с понижением мощности (поиск нижнего порога)."""
        h = self.hyps
        start_pwm = random.randint(3, 4) * 10
        seq = np.concatenate([np.arange(start_pwm, 20, h['delta_pwm_down']),
                              np.arange(20, h['end_pwm_down'], -2)])
        return self._probe(seq, motor_idx, positive_answer='n')

    def _upstream(self, motor_idx: int) -> int:
        """Проход с повышением мощности (поиск верхнего порога)."""
        h = self.hyps
        start_pwm = random.randint(2, 8)
        seq = np.arange(start_pwm, h['end_pwm_up'], h['delta_pwm_up'])
        return self._probe(seq, motor_idx, positive_answer='y')

    def _probe(self, seq, motor_idx, positive_answer: str) -> int:
        """Общий проход по последовательности seq.  
        positive_answer : {"y", "n"} - буква, означающая «чувствую» или «не чувствую»."""
        h = self.hyps
        pwm_arr = [0] * h['n_motors']

        for v in seq:

            # === Прерывание по кнопке «Главный экран» ===
            if self._stop:
                self.vibro.reset_pwm_values()  # мгновенно гасим моторы
                return -1                      # специальный код «прервано»

            # === Сигнал «ВИБРАЦИЯ» перед включением мотора ===
            self.vibrationStarted.emit()
            pwm_arr[motor_idx] = v
            self.vibro.set_pwm_values(pwm_arr)
            time.sleep(0.5)
            self.vibro.reset_pwm_values()
            # time.sleep(0.1)

            # === Сигнал «Почувствовали?» перед ожиданием ответа ===
            self.awaitingAnswer.emit()
            self.wait_for_patient()         # блокирующее ожидание сигнала из GUI


            # если отмена пришла, пока ждали ответ
            if self._stop:
                self.vibro.reset_pwm_values()
                return -1


            if self._patient_answer == positive_answer:
                return int(v + abs(h['delta_pwm_down'] if positive_answer == 'n' else 0))
            
            time.sleep(0.35)

        return int(abs(h['delta_pwm_down'])) if positive_answer == 'n' else int(h['end_pwm_up'])

    # ------------------------------------------------------------------
    # Связь с GUI
    # ------------------------------------------------------------------

    _patient_answer = ''

    def set_answer(self, ans: str):
        """Получить ответ пациента из GUI («y» / «n»)."""
        self._patient_answer = ans

    def wait_for_patient(self):
        """Блокирующее ожидание ответа пациента либо отмены теста."""
        self._patient_answer = ''
        while self._patient_answer == '' and not self._stop:
            self.msleep(10)

    # ------------------------------------------------------------------
    # Управление потоком
    # ------------------------------------------------------------------

    def stop(self):
        """Запросить досрочную остановку теста."""
        self._stop = True
