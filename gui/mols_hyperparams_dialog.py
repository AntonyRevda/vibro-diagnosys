# gui/mols_hyperparams_dialog.py

"""
Диалог настроек гиперпараметров для MOLs-теста.

Позволяет пользователю задать параметры диапазона моторов, количество
повторов и параметры изменения ШИМ в режимах upstream и downstream.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QSpinBox, QDialogButtonBox, QVBoxLayout,
    QWidget, QLabel, QAbstractSpinBox
)


class MOLsHyperparamsDialog(QDialog):
    """Окно для ввода гиперпараметров MOLs-теста."""

    def __init__(self, hyps: dict, parent=None):
        """
        Параметры
        ---------
        hyps : dict
            Исходные значения гиперпараметров.
        parent : QWidget | None
            Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Параметры теста")
        self.setModal(True)
        self.resize(450, 550)

        self.hyps = hyps.copy()

        # Центральный контейнер без фона
        container = QWidget(self)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Форма
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignCenter)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(12)

        # Общий стиль для меток-подписи
        label_style = """
            background-color: rgba(255, 255, 255, 0.3);
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 14pt;
            color: #333;
        """

        # --- Helper для создания промаркированных QLabel ---
        def make_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(label_style)
            lbl.setFont(QFont("", 14))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl

        # 1. Параметры моторов
        self.sb_num_motor_start = QSpinBox()
        self.sb_num_motor_start.setRange(0,100)
        self.sb_num_motor_start.setValue(self.hyps['num_motor_start'])
        form.addRow(make_label("Первый мотор:"), self.sb_num_motor_start)

        self.sb_num_motor_end = QSpinBox()
        self.sb_num_motor_end.setRange(0,100)
        self.sb_num_motor_end.setValue(self.hyps['num_motor_end'])
        form.addRow(make_label("Последний мотор:"), self.sb_num_motor_end)

        self.sb_use_motors_step = QSpinBox()
        self.sb_use_motors_step.setRange(1,10)
        self.sb_use_motors_step.setValue(self.hyps['use_motors_step'])
        form.addRow(make_label("Шаг моторов:"), self.sb_use_motors_step)

        self.sb_exps_each = QSpinBox()
        self.sb_exps_each.setRange(1,10)
        self.sb_exps_each.setValue(self.hyps['exps_for_each_motor'])
        form.addRow(make_label("Испытаний на мотор:"), self.sb_exps_each)

        # 2. Параметры downstream
        self.sb_end_pwm_down = QSpinBox()
        self.sb_end_pwm_down.setRange(0,255)
        self.sb_end_pwm_down.setValue(abs(self.hyps['end_pwm_down']))
        form.addRow(make_label("Последний ШИМ downstream:"), self.sb_end_pwm_down)

        self.sb_delta_pwm_down = QSpinBox()
        self.sb_delta_pwm_down.setRange(1,100)
        self.sb_delta_pwm_down.setValue(abs(self.hyps['delta_pwm_down']))
        form.addRow(make_label("Шаг ШИМа downstream:"), self.sb_delta_pwm_down)

        # 3. Параметры upstream
        self.sb_end_pwm_up = QSpinBox()
        self.sb_end_pwm_up.setRange(0,255)
        self.sb_end_pwm_up.setValue(self.hyps['end_pwm_up'])
        form.addRow(make_label("Последний ШИМ upstream:"), self.sb_end_pwm_up)

        self.sb_delta_pwm_up = QSpinBox()
        self.sb_delta_pwm_up.setRange(1,100)
        self.sb_delta_pwm_up.setValue(self.hyps['delta_pwm_up'])
        form.addRow(make_label("Шаг ШИМа upstream:"), self.sb_delta_pwm_up)

        # Убираем стрелочки у всех SpinBox и стилизуем ввод
        for sb in (
            self.sb_num_motor_start, self.sb_num_motor_end,
            self.sb_use_motors_step, self.sb_exps_each,
            self.sb_end_pwm_down, self.sb_delta_pwm_down,
            self.sb_end_pwm_up, self.sb_delta_pwm_up
        ):
            sb.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            sb.setStyleSheet("""
                background-color: rgba(255,255,255,0.9);
                border: none;
                border-radius: 8px;
                padding: 6px;
                font-size: 12pt;
                color: #333;
            """)

        # Кнопки ОК / Отмена
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Стилизация кнопок
        for btn in buttons.buttons():
            btn.setStyleSheet("""
                background-color: rgba(255,255,255,0.9);
                border: none;
                border-radius: 8px;
                padding: 8px;
                font-size: 12pt;
                color: #333;
            """)

        main_layout.addLayout(form)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)

    def paintEvent(self, _):
        """Отрисовывает градиентный фон окна как в MainWindow"""
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#2ECC71"))
        grad.setColorAt(1.0, QColor("#1ABC9C"))
        painter.fillRect(self.rect(), grad)

    def get_hyps(self) -> dict:
        """Возвращает словарь с актуальными значениями гиперпараметров."""
        h = self.hyps
        h['num_motor_start']     = self.sb_num_motor_start.value()
        h['num_motor_end']       = self.sb_num_motor_end.value()
        h['use_motors_step']     = self.sb_use_motors_step.value()
        h['exps_for_each_motor'] = self.sb_exps_each.value()
        h['end_pwm_down']        = -abs(self.sb_end_pwm_down.value())
        h['delta_pwm_down']      = -abs(self.sb_delta_pwm_down.value())
        h['end_pwm_up']          = self.sb_end_pwm_up.value()
        h['delta_pwm_up']        = self.sb_delta_pwm_up.value()
        return h
