# gui/spatial_training_window.py

"""
Окно обучения Spatial-теста.

Сценарий работы:
  1) Фаза демонстрации:
      • Для режима Single — вибрация каждой области по очереди.
      • Для режима Pairs  — попеременная вибрация двух моторов пары.
  2) Режим обучения:
      • ← / → — смена области;
      • Space — повтор текущей вибрации;
      • Esc   — выход из окна.
"""

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui  import QPainter, QLinearGradient, QColor, QShortcut, QKeySequence
from PyQt6.QtWidgets import QMainWindow, QWidget, QLabel, QVBoxLayout, QPushButton
import numpy as np, time

from core.serial_api import VibroBox

# ============================================================
#      Фоновый поток для автоматической демонстрации
# ============================================================

class DemoThread(QThread):

    """
    Поток, который проигрывает сигналы вибрации для всех областей.
    Работает до конца, затем посылает сигнал finished_demo.
    """
    
    finished_demo = pyqtSignal() # Сигнал окончания демонстрации

    def __init__(self, vibro: VibroBox, motors, pwm: int, mode: str, pause=0.6):
        
        """
        Параметры:
            vibro: Объект VibroBox для управления моторами.
            motors: Список индексов моторов.
            pwm: Значение PWM для воспроизведения.
            mode: Режим теста ('single' или 'pairs').
            pause: Пауза между сигналами в секундах.
        """

        super().__init__()
        self.vibro = vibro
        self.motors = motors
        self.pwm = pwm
        self.mode = mode
        self.pause = pause


    def run(self):

        """Запускает демонстрацию всех областей."""

        arr = np.zeros(self.vibro.n_motors, dtype=np.uint8)

        for m in self.motors:
            if self.mode == 'single':
                # Включаем только один мотор
                arr[:] = 0; arr[m] = self.pwm
                self.vibro.set_pwm_values(arr)
                time.sleep(self.pause)
                self.vibro.reset_pwm_values()
            else:   # pairs — вибрация двух соседних моторов попеременно
                for mot in (m, m + 1):
                    arr[:] = 0; arr[mot] = self.pwm
                    self.vibro.set_pwm_values(arr)
                    time.sleep(self.pause / 2)
                    self.vibro.reset_pwm_values()
                    time.sleep(0.1)
            time.sleep(0.3)

        self.finished_demo.emit()


# ============================================================
#           Главное окно обучения Spatial-теста
# ============================================================

class SpatialTrainingWindow(QMainWindow):
    
    """
    Окно для обучения пользователя определять вибрацию в Spatial-тесте.

    • Режим Single:
        ← / → — смена области,
        Space — повтор,
        Esc   — выход.
    • Режим Pairs:
        области идут парами (i и i+1), вибрация попеременно.
    """
    
    def __init__(self, vibro: VibroBox, motors: list[int], pwm: int, mode: str, parent=None):
        
        super().__init__(parent)
        # Заголовок и размеры окна
        self.setWindowTitle("Обучение Spatial")
        self.resize(500, 300)
        # Параметры теста
        self.vibro = vibro
        self.motors = motors
        self.pwm = pwm
        self.mode = mode

        # ---------- UI ----------
        central = QWidget(self)
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(20)

        # Метка с информацией
        self.lbl_info = QLabel("Демонстрация сигналов…", alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setStyleSheet("font-size: 16pt;")
        v.addWidget(self.lbl_info)

        # Метка со статусом
        self.lbl_status = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 14pt;")
        v.addWidget(self.lbl_status)

        # Кнопка «Закрыть»
        btn_exit = QPushButton("Закрыть")
        btn_exit.setStyleSheet("font-size: 12pt;")
        btn_exit.clicked.connect(self.close)
        v.addWidget(btn_exit)

        # ---------- Запуск демонстрации ----------
        self.demo = DemoThread(vibro, motors, pwm, mode)
        self.demo.finished_demo.connect(self._on_demo_finished)
        self.demo.start()


    def paintEvent(self, _):

        """Градиентный фон"""
        
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor("#2ECC71"))
        g.setColorAt(1.0, QColor("#1ABC9C"))
        p.fillRect(self.rect(), g)


    def _on_demo_finished(self):
        
        """
        После завершения демонстрации:
          • обновляем lbl_info;
          • сбрасываем индекс в 0;
          • включаем горячие клавиши управления;
          • запускаем первую вибрацию.
        """
        
        self.lbl_info.setText(
            "Режим обучения:\n"
            "← / →   — смена области\n"
            "Space    — повтор\n"
            "Esc      — выход"
        )
        self._idx = 0
        self._apply_vibration()

        # Горячие клавиши
        QShortcut(QKeySequence(Qt.Key.Key_Left),  self, activated=lambda: self._step(-1))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, activated=lambda: self._step(+1))
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self._apply_vibration)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.close)


    def _step(self, delta: int):

        """Сдвигает текущий индекс на delta с циклическим переходом."""

        self._idx = (self._idx + delta) % len(self.motors)
        self._apply_vibration()


    def _apply_vibration(self):

        """
        Включает вибрацию для текущей области (одиночной или пары),
        обновляет lbl_status и выключает моторы с задержкой.
        """

        arr = np.zeros(self.vibro.n_motors, dtype=np.uint8)
        
        if self.mode == 'single':
            mot = self.motors[self._idx]
            arr[mot] = self.pwm
            self.lbl_status.setText(f"Номер области: {self._idx + 1}")
            self.vibro.set_pwm_values(arr)
        else:   # 'pairs'
            m = self.motors[self._idx]
            for mot in (m, m + 1):
                arr[:] = 0
                arr[mot] = self.pwm
                self.vibro.set_pwm_values(arr)
                time.sleep(0.25)
            self.lbl_status.setText(f"Номер области: {self._idx + 1}  (пара)")
        
        # После короткой паузы отключаем моторы
        QThread.msleep(200)
        self.vibro.reset_pwm_values()
