# gui/spatial_hyperparams_dialog.py

"""
Диалог настройки гиперпараметров Spatial-теста.

Позволяет указать:
  1) Диапазон моторов (первый / последний).
  2) Шаг перебора моторов (для режима Single).
  3) Количество тестов (max_counter_samples).
  4) PWM вибрации (spatial_pwm).
  5) Режим работы теста: Pairs или Single.
  6) Кнопка для запуска обучения (SpatialTrainingWindow).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QSpinBox,
    QDialogButtonBox, QVBoxLayout, QLabel,
    QAbstractSpinBox, QHBoxLayout, QWidget,
    QPushButton
)

# Отложенный импорт, чтобы избежать круговой зависимости при тестах
def _train_window():
    from gui.spatial_training_window import SpatialTrainingWindow
    return SpatialTrainingWindow


class SpatialHyperparamsDialog(QDialog):
    
    """Диалоговое окно для задания гиперпараметров Spatial-теста."""
    
    def __init__(self, hyps: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Параметры Spatial-теста")
        self.resize(400, 480)
        
        # Делаем копию, чтобы не менять оригинал до подтверждения.
        self.hyps = hyps.copy()

        # ---------- Основной layout диалога----------
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ---------- Форма с подписями и полями ----------
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignCenter)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(12)

        def make_label(text: str):

            """Создаёт QLabel с единым стилем для подписей."""
            
            lbl = QLabel(text)
            lbl.setStyleSheet(
                """
                background-color: rgba(255,255,255,0.3);
                border-radius: 6px; padding:4px 8px;
                font-size: 14pt; color: #333;
                """
            )
            lbl.setFont(QFont("", 14))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl

        # 1) Первый мотор
        self.sb_start = QSpinBox()
        self.sb_start.setRange(0, 100)
        self.sb_start.setValue(self.hyps['num_motor_start'])
        form.addRow(make_label("Первый мотор:"), self.sb_start)

        # 2) Последний мотор
        self.sb_end = QSpinBox()
        self.sb_end.setRange(0, 100)
        self.sb_end.setValue(self.hyps['num_motor_end'])
        form.addRow(make_label("Последний мотор:"), self.sb_end)

        # 3) Шаг моторов (диапазон динамический)
        self.cb_step = QComboBox()
        # Подготовка внешнего вида combobox как кнопки
        self.cb_step.setStyleSheet(
            """
            QComboBox {
                background-color: rgba(255,255,255,0.9);
                border: none; border-radius: 8px;
                padding: 6px; font-size: 12pt; color: #333;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ccc;
                padding: 4px;
            }
            """
        )
        # Для режима Pairs — отображаем надпись «None»
        self.lbl_step_none = QLabel("None")
        self.lbl_step_none.setStyleSheet(
            """
            background-color: rgba(255,255,255,0.9);
            border-radius: 8px; padding:6px;
            font-size: 12pt; color:#333;
            """
        )
        step_container = QWidget()
        step_layout = QHBoxLayout(step_container)
        step_layout.setContentsMargins(0, 0, 0, 0)
        step_layout.setSpacing(10)
        step_layout.addWidget(self.cb_step)
        step_layout.addWidget(self.lbl_step_none)
        form.addRow(make_label("Шаг моторов:"), step_container)

        # 4) Число предъявлений
        self.sb_samples = QSpinBox()
        self.sb_samples.setRange(1, 100)
        self.sb_samples.setValue(self.hyps['max_counter_samples'])
        form.addRow(make_label("Количество тестов:"), self.sb_samples)

        # 5) ШИМ вибрации
        self.sb_pwm = QSpinBox()
        self.sb_pwm.setRange(0, 255)
        self.sb_pwm.setValue(self.hyps['spatial_pwm'])
        form.addRow(make_label("ШИМ вибрации:"), self.sb_pwm)

        # 6) Режим теста: Pairs или Single
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(['Pairs', 'Single'])
        initial = self.hyps.get('spatial_mode', 'pairs').capitalize()
        self.cb_mode.setCurrentText(initial)
        self.cb_mode.setStyleSheet(
            self.cb_step.styleSheet()
        )
        form.addRow(make_label("Режим теста:"), self.cb_mode)

        # ---------- Единый стиль для spinbox'ов ----------
        for sb in (self.sb_start, self.sb_end, self.sb_samples, self.sb_pwm):
            sb.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            sb.setStyleSheet(
                """
                background-color: rgba(255,255,255,0.9);
                border: none; border-radius: 8px;
                padding: 6px; font-size: 12pt; color:#333;
                """
            )

        # Кнопки OK/Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        for btn in buttons.buttons():
            btn.setStyleSheet(
                """
                background-color: rgba(255,255,255,0.9);
                border: none; border-radius: 8px;
                padding:8px; font-size:12pt; color:#333;
                """
            )

        main_layout.addLayout(form)

        # ---------- Кнопка «Пройти обучение» -----------------------------
        spin_style = """
            background-color: rgba(255,255,255,0.9);
            border:none; border-radius:8px;
            padding:6px; font-size:12pt; color:#333;
        """
        self.btn_train = QPushButton("Пройти обучение")
        self.btn_train.setStyleSheet(spin_style)

        hl_train = QHBoxLayout()
        hl_train.addStretch()
        hl_train.addWidget(self.btn_train)
        hl_train.addStretch()
        
        
        main_layout.addStretch(1)
        main_layout.addLayout(hl_train)
        main_layout.addStretch(1)

        main_layout.addWidget(buttons)

        # Связываем события
        self.cb_mode.currentTextChanged.connect(self.on_mode_changed)
        self.sb_start.valueChanged.connect(self.on_range_changed)
        self.sb_end.valueChanged.connect(self.on_range_changed)

        self.btn_train.clicked.connect(self._start_training)

        # Инициализация состояния
        self.on_mode_changed(initial)


    def paintEvent(self, _):

        """Градиентный фон"""
        
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#2ECC71"))
        grad.setColorAt(1.0, QColor("#1ABC9C"))
        painter.fillRect(self.rect(), grad)


    def compute_allowed_steps(self, total_motors: int) -> list[int]:

        """
        Возвращает допустимые шаги:
          • всегда 1;
          • 2, если total делится на 2;
          • 3, если total делится на 3.
        """
        
        steps = [1]
        if total_motors % 2 == 0:
            steps.append(2)
        if total_motors % 3 == 0:
            steps.append(3)
        return sorted(set(steps))


    def on_range_changed(self, _=None):

        """При изменении диапазона, если режим Single, пересчитывает допустимые шаги."""

        if self.cb_mode.currentText().lower() == 'single':
            self.update_steps()


    def on_mode_changed(self, display_mode: str):
        
        """
        При режиме Pairs скрываем combobox и показываем 'None'.
        При режиме Single — наоборот и пересчитываем шаги.
        """
                
        mode = display_mode.lower()

        if mode == 'pairs':
            self.cb_step.hide()
            self.lbl_step_none.show()
        else:  # 'single'
            self.lbl_step_none.hide()
            self.cb_step.show()
            self.update_steps()


    def update_steps(self):

        """Пересчитывает и выставляет значения шага."""

        total = max(1, self.sb_end.value() - self.sb_start.value() + 1)
        allowed = self.compute_allowed_steps(total)
        self.cb_step.clear()
        self.cb_step.addItems([str(s) for s in allowed])

        # По умолчанию ставим 2, если есть, иначе первый из списка.
        if '2' in [str(s) for s in allowed]:
            self.cb_step.setCurrentText('2')
        else:
            self.cb_step.setCurrentText(self.cb_step.itemText(0))


    def get_hyps(self) -> dict:
        """Возвращает словарь с актуальными значениями полей диалога."""
        h = self.hyps
        h['num_motor_start']     = self.sb_start.value()
        h['num_motor_end']       = self.sb_end.value()
        mode = self.cb_mode.currentText().lower()
        h['use_motors_step']     = 2 if mode == 'pairs' else int(self.cb_step.currentText())
        h['max_counter_samples'] = self.sb_samples.value()
        h['spatial_pwm']         = self.sb_pwm.value()
        h['spatial_mode']        = mode
        return h



    
    def _start_training(self):
        """Запуск окна обучения Spatial."""
        h = self.get_hyps()
        motors = list(range(
            h['num_motor_start'],
            h['num_motor_end'] + 1,
            h['use_motors_step']
        ))
        
        SpatialTrainingWindow = _train_window()           # ленивый импорт
        
        vibro = getattr(self.parent(), "vibro", None)     # ищем VibroBox у любого из родителей (MainWindow)
        
        self._train_win = SpatialTrainingWindow(
            vibro=vibro,
            motors=motors,
            pwm=h['spatial_pwm'],
            mode=h['spatial_mode'],
            parent=self
        )

        self._train_win.show()