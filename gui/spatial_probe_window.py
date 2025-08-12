# gui/spatial_probe_window.py

"""
Окно проведения Spatial-теста (этап опроса).

Показывает:
  • Информационный лейбл с инструкцией или подсказкой.
  • Сетку кнопок-ответов (номера пар), генерируемую динамически.
  • Прогресс прохождения теста.
  • Кнопку «Стоп» для завершения теста.

Кнопки-ответы и «Стоп» стилизуются внешней функцией apply_style_fn.
"""

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QLinearGradient, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QGridLayout, QHBoxLayout
)

class SpatialProbeWindow(QMainWindow):

    """
    Программно собранное окно для Spatial-теста.
    Кнопки-ответы стилизуются через функцию apply_style_fn.
    """
    
    def __init__(self, n_pairs: int, apply_style_fn, parent=None):
        super().__init__(parent)

        # Храним функцию стилизации и ссылку на главное окно
        self._apply_style = apply_style_fn
        self.main_win = parent

        # Заголовок окна и минимальная ширина
        self.setWindowTitle('Spatial-тест')
        self.setMinimumWidth(500)

        # ---------- Центральный виджет и основной layout ----------
        central = QWidget(self)
        self.setCentralWidget(central)
        main_v = QVBoxLayout(central)
        main_v.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_v.setSpacing(20)

        # ---------- Информационный лейбл ----------
        self.lbl_info = QLabel('Подготовьтесь…', self)
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setWordWrap(True)
        main_v.addWidget(self.lbl_info)

        # ---------- Сетка кнопок-ответов ----------
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        main_v.addLayout(self.grid)

        cols = 4 # Количество столбцов в сетке
        for i in range(1, n_pairs + 1):
            btn = QPushButton(str(i), self)
            btn.setMinimumSize(90, 60)
            self._apply_style(btn)
            # При клике отправляем ответ в worker главного окна
            btn.clicked.connect(lambda _, v=i: self.main_win.worker.set_answer(v))
            # Размещение по рядам и столбцам
            r, c = divmod(i - 1, cols)
            self.grid.addWidget(btn, r, c)

        # ---------- Прогресс ----------
        # Показывает «N / M» — сколько шагов пройдено из общего числа.
        self.lbl_progress = QLabel('0 / 0', self)
        self.lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_v.addWidget(self.lbl_progress)

        # ---------- Кнопка «Стоп» ----------
        bottom_h = QHBoxLayout()
        bottom_h.addStretch()
        self.btn_stop = QPushButton('Стоп', self)
        self._apply_style(self.btn_stop)
        self.btn_stop.clicked.connect(self._stop_test)
        bottom_h.addWidget(self.btn_stop)
        main_v.addLayout(bottom_h)


    def _stop_test(self):
        
        """
        Мягко останавливает тест:
          1) Отправляет сигнал остановки в worker главного окна.
          2) Закрывает окно.
        """

        self.main_win.worker.stop()
        self.close()
    
    
    def paintEvent(self, _):
        
        """Рисует градиентный фон"""
        
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#2ECC71"))
        grad.setColorAt(1.0, QColor("#1ABC9C"))
        painter.fillRect(QRect(0, 0, self.width(), self.height()), grad)
