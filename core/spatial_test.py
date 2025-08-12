# core/spatial_test.py

"""
Spatial‑тест — распознавание пространственных областей.

Модуль содержит класс :class:`SpatialWorker`, выполняющий тест определения
области (пары или одиночного мотора) в отдельном потоке Qt. Алгоритм
последовательно предъявляет стимулы и собирает ответы пациента.
"""

from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np, random, time
from core.serial_api import VibroBox

class SpatialWorker(QThread):
    """
    Фоновый поток, выполняющий Spatial‑тест.

    Сигналы класса
    --------------
    progress(int done, int total)
        Количество завершённых предъявлений и общее их число.
    awaitingAnswer()
        Импульс отправлен — ожидаем ответ пациента.
    finished(dict result)
        Словарь с полями ``answers`` и ``mode``.
    
    Параметры
    ----------
    vibro : VibroBox
        Экземпляр класса управления аппаратной частью.
    hyps : dict[str, Any]
        Гиперпараметры, см. ``core.config.default_hyps``.
    mode : {"pairs", "single"}, optional
        Режим предъявления: пара моторов (``"pairs"``) либо одиночный
        мотор (``"single"``). По умолчанию ``"pairs"``.
    """
    progress = pyqtSignal(int, int)        # done, total
    awaitingAnswer = pyqtSignal()
    finished = pyqtSignal(dict)

    def __init__(self, vibro: VibroBox, hyps: dict, mode: str = 'pairs'):
        super().__init__()
        self.vibro = vibro
        self.hyps = hyps
        self.mode = mode                   # 'pairs' | 'single'
        self._answer = None
        self._stop = False

    # ------------------------------------------------------------------
    # API для GUI
    # ------------------------------------------------------------------

    def set_answer(self, value: int):
        """Получить ответ пациента (номер области)."""
        self._answer = value

    def stop(self):
        """Запросить досрочное завершение теста."""
        self._stop = True

    # ------------------------------------------------------------------
    # Основной алгоритм (QThread.run)
    # ------------------------------------------------------------------

    def run(self):
        """Запустить тест и последовательно обработать все предъявления."""
        h = self.hyps
        start = h['num_motor_start']
        end = h['num_motor_end']
        step = h['use_motors_step']

        # --- Формируем список стартовых моторов для областей ----------
        if self.mode == 'pairs':
            # исключаем неполные пары, поэтому range до end, не включая последнюю точку
            uses = list(range(start, end, step))
        else:
            # для single — все моторы равномерно
            uses = list(range(start, end + 1))
        if not uses:
            return # некорректные гиперпараметры


        max_samples = h['max_counter_samples']    # общее число предъявлений
        count_uses  = len(uses)                   # сколько разных областей мы используем
        q, r = divmod(max_samples, count_uses)    # целые «полные» циклы и остаток

        # q полных повторов и r случайных дополнительных
        seq = []
        for _ in range(q):
            seq.extend(uses)                      # добавляем полный набор областей q раз
        if r > 0:
            seq.extend(random.sample(uses, r))    # + r случайных, чтобы довести счётчик

        # Затем перемешиваем
        random.shuffle(seq)


        answers = []
        total = len(seq)

        for idx, m0 in enumerate(seq):
            if self._stop:
                break

            self.progress.emit(idx + 1, total)

            # --- Определяем моторы для стимуляции и true_region ---
            if self.mode == 'pairs':
                motors = (m0, m0 + 1)
                true_region = (m0 - start) // step + 1
            else:
                motors = (m0,)
                true_region = (m0 - start) // step + 1

            # --- Подаём вибрацию ----------------------------------
            for mot in motors:
                vals = np.zeros(h['n_motors'], dtype=np.uint8)
                if 0 <= mot < h['n_motors']:
                    vals[mot] = h.get('spatial_pwm', 0)
                self.vibro.set_pwm_values(vals)
                time.sleep(h.get('time_sleep_param', 0.25))
            self.vibro.reset_pwm_values()

            # --- Ожидаем ответ ------------------------------------
            self._answer = None
            self.awaitingAnswer.emit()
            while self._answer is None and not self._stop:
                self.msleep(50)

            if self._stop or self._answer is None:
                break

            answers.append((true_region, self._answer))

            # Пауза после ответа перед следующим шагом
            time.sleep(0.5)

        # ------------------------------------------------------------------
        # Подведение итогов
        # ------------------------------------------------------------------
        
        result = {
            'answers': answers,
            'mode': self.mode,
        }
        self.finished.emit(result)
