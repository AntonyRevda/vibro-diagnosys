# gui/pmpwm_training_window.py

"""
Окно обучения PM-PWM-теста.

Состоит из двух фаз:
  1) Демонстрация — поочередное воспроизведение PWM-сигналов
     на каждом моторе (автоматически).
  2) Ручной режим — пользователь сам переключает моторы и PWM.

Может работать в «free_mode», минуя фазу демонстрации и сразу
начиная с ручного режима.
"""

import time
import numpy as np

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui  import QPainter, QLinearGradient, QColor, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QVBoxLayout, QPushButton
)

from core.serial_api import VibroBox

# ============================================================
#       Фоновый поток для автоматической демонстрации
# ============================================================

class DemoThread(QThread):
    """
    Поток для фазы демонстрации:
    последовательно воспроизводит каждый PWM на каждом моторе.
    """

    finished_demo = pyqtSignal() # Сигнал окончания демонстрации.

    def __init__(self, vibro: VibroBox, motors, pwm_vals, pause=0.6):
        super().__init__()
        self.vibro, self.motors, self.pwms, self.pause = vibro, motors, pwm_vals, pause

    def run(self):
        """Проигрываем каждый PWM на каждом моторе по очереди."""
        arr = np.zeros(self.vibro.n_motors, dtype=np.uint8)
        for m in self.motors:
            for p in self.pwms:
                # Обнуляем все моторы
                arr[:] = 0
                # Выставляем PWM только для текущего мотора
                arr[m] = p
                self.vibro.set_pwm_values(arr)
                time.sleep(self.pause)
                # Сбрасываем значения
                self.vibro.reset_pwm_values()
                time.sleep(0.3)

        # По завершении шлём сигнал
        self.finished_demo.emit()

# ============================================================
#              Главное окно обучения PM-PWM
# ============================================================

class PMPWMTrainingWindow(QMainWindow):
    """
    Окно обучения PM-PWM-теста.

    Может работать:
      • с демонстрацией (free_mode=False) — сперва авто-показ, потом ручной режим;
      • без демонстрации (free_mode=True) — сразу ручной режим.
    """

    closed = pyqtSignal() # Сигнал закрытия окна

    def __init__(self, vibro: VibroBox, motors: list[int],
                 pwm_values: list[int], free_mode: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Обучение PM-PWM")
        self.resize(500, 300)
        self.vibro, self.motors, self.pwms = vibro, motors, pwm_values
        
        self.free_mode = free_mode

        # ---------- UI ----------
        central = QWidget(self)
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(20)

        # Метка информации (меняется при переходе в ручной режим)
        self.lbl_info = QLabel(
            "Демонстрация сигналов…", alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.lbl_info.setStyleSheet("font-size: 16pt;")
        v.addWidget(self.lbl_info)

        # Метка статуса: какой мотор и PWM сейчас активны
        self.lbl_status = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 14pt;")
        v.addWidget(self.lbl_status)

        # Кнопка «Закрыть»
        self.btn_exit = QPushButton("Закрыть")
        self.btn_exit.setStyleSheet("font-size: 12pt;")
        self.btn_exit.clicked.connect(self.close)
        v.addWidget(self.btn_exit)


        # ---------- Логика запуска ----------
        if not self.free_mode:
            # Создаём и запускаем поток демонстрации
            self.demo = DemoThread(vibro, motors, pwm_values)
            self.demo.finished_demo.connect(self._on_demo_finished)
            self.demo.start()
        else:
            # Сразу переходим к ручному обучению
            self._on_demo_finished()    # переиспользуем готовый метод


    def closeEvent(self, event):
        """Отправляет сигнал closed перед обычным закрытием."""
        super().closeEvent(event)
        self.closed.emit()


    def paintEvent(self, _):
        """Рисует вертикальный градиентный фон."""
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor("#2ECC71"))
        g.setColorAt(1.0, QColor("#1ABC9C"))
        p.fillRect(self.rect(), g)


    def _on_demo_finished(self):
        """
        Переводит интерфейс в режим ручного управления моторами/PWM.
        Добавляет горячие клавиши.
        """
        self.lbl_info.setText(
            "Режим обучения:\n"
            "← / →   — смена мотора\n"
            "+  / −   — мощность выше / ниже\n"
            "Space    — повтор\n"
            "Esc      — выход"
        )

        # Начальные значения: первый мотор, первый PWM
        self._current_motor = self.motors[0]
        self._idx_pwm = 0
        self._apply_vibration()

        # Горячие клавиши
        QShortcut(QKeySequence(Qt.Key.Key_Left),  self,
                  activated=lambda: self._step_motor(-1))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self,
                  activated=lambda: self._step_motor(+1))
        QShortcut(QKeySequence(Qt.Key.Key_Plus),  self,
                  activated=lambda: self._step_pwm(+1))
        QShortcut(QKeySequence(Qt.Key.Key_Minus), self,
                  activated=lambda: self._step_pwm(-1))
        QShortcut(QKeySequence(Qt.Key.Key_Space), self,
                  activated=self._apply_vibration)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self,
                  activated=self.close)


    def _step_motor(self, delta):
        """Сдвигает текущий мотор в списке на delta позиций по кольцу."""
        i = self.motors.index(self._current_motor)
        self._current_motor = self.motors[(i + delta) % len(self.motors)]
        self._apply_vibration()

    def _step_pwm(self, delta):
        """Сдвигает текущий PWM на delta позиций по кольцу."""
        self._idx_pwm = (self._idx_pwm + delta) % len(self.pwms)
        self._apply_vibration()

    def _apply_vibration(self):
        """
        Включает вибрацию на текущем моторе с текущим PWM,
        обновляет метку статуса и планирует авто-выключение.
        """
        arr = np.zeros(self.vibro.n_motors, dtype=np.uint8)
        arr[self._current_motor] = self.pwms[self._idx_pwm]
        self.vibro.set_pwm_values(arr)
        # Обновляем статус в UI
        self.lbl_status.setText(
            f"Мотор {self._current_motor}  |  PWM {self.pwms[self._idx_pwm]}"
        )
        # Авто-выключение через 600 мс
        QTimer.singleShot(600, self.vibro.reset_pwm_values)


