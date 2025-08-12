# core/serial_api.py

"""
Интерфейс USB‑Serial для управления VibroBox.

Модуль содержит класс :class:`VibroBox`, инкапсулирующий работу с Raspberry
Pi Pico, на котором стоит прошивка для управления N вибромоторами. Класс
предоставляет:

* автоматический поиск и подключение по VID/PID/описанию;
* методы выставления массива PWM‑значений;
* служебные индикаторы начала/конца теста;
* полный сброс моторов.
"""

import time
from typing import Optional, Sequence

import numpy as np
import serial
from serial.tools import list_ports

class VibroBox:

    """Доступ к плате VibroBox через USB‑Serial."""

    def __init__(self, n_motors: int = 10):
        self.n_motors = n_motors
        self.ser: Optional[serial.Serial] = None

    # ------------------------------------------------------------------
    # Соединение
    # ------------------------------------------------------------------

    def connect_auto(self) -> bool:
        """
        Автоматически находит плату в списке COM‑портов и подключается.
        Возвращает ``True``, если соединение успешно, иначе ``False``.
        """
        ports = list_ports.comports()
        for p in ports:
            if 'Устройство' in p.description:
                try:
                    self.ser = serial.Serial(p.device)
                    return True
                except serial.SerialException:
                    pass
        return False

    # ------------------------------------------------------------------
    # Низкоуровневые команды
    # ------------------------------------------------------------------

    def _write_array(self, arr: Sequence[int]) -> None:
        """Отправить массив PWM как сырые байты (uint8[N])."""
        if not self.ser:
            raise RuntimeError('VibroBox not connected')
        data = np.array(arr, dtype=np.uint8).tobytes()
        self.ser.write(data)

    def set_pwm_values(self, pwm_values: Sequence[int]) -> None:
        """
        Установить ШИМ для всех моторов.
        Длина последовательности *должна* совпадать с ``self.n_motors``.
        """
        if len(pwm_values) != self.n_motors:
            raise ValueError('Length of pwm_values must equal n_motors')
        self._write_array(pwm_values)

    def reset_pwm_values(self) -> None:
        """Отключить все моторы (установить PWM = 0)."""
        self.set_pwm_values([0] * self.n_motors)

    # ------------------------------------------------------------------
    # Визуально‑тактильный индикатор начала/конца теста
    # ------------------------------------------------------------------

    def begin_end_indicator(self, val: int = 20, repeats: int = 2, pause: float = .25):
        """Мигание всеми моторами для сигнала «старт/стоп теста»."""
        for _ in range(repeats):
            self.set_pwm_values([val] * self.n_motors)
            time.sleep(pause)
            self.reset_pwm_values()
            time.sleep(pause)
