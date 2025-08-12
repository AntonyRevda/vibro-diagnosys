# gui/pmpwm_hyperparams_dialog.py

"""
Диалоговое окно для настройки гиперпараметров PM-PWM-теста.

Позволяет пользователю выбрать параметры теста перед запуском.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QLabel, QComboBox,
    QDialogButtonBox, QSpinBox, QLineEdit, QAbstractSpinBox, QWidget,
    QHBoxLayout, QPushButton
)

class PMPWMHyperparamsDialog(QDialog):
    """
    Диалог выбора гиперпараметров для PM-PWM-теста.

    Поля ввода:
      • Первый мотор
      • Последний мотор
      • Шаг моторов
      • Словарь PWM (список значений через запятую)
      • Rоличество повторов подачи каждого PWM
    """
    def __init__(self, hyps: dict, parent=None):
        """
        Инициализирует диалог и создаёт интерфейс.

        Параметры:
            hyps: Текущие гиперпараметры (будут скопированы).
            parent: Родительский виджет (обычно главное окно).
        """
        super().__init__(parent)
        self.setWindowTitle("Параметры PM-PWM-теста")
        self.resize(420, 420) # было 420 520

        self.hyps = hyps.copy() # Копируем, чтобы не менять исходные данные напрямую

        # ---------------- Основной layout -------------------
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(15)

        # Форма — основной контейнер для подписей и контролов ввода.
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignCenter)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(12)

        def make_label(text: str) -> QLabel:
            """
            Создаёт аккуратную подпись с лёгкой подсветкой фона.
            Стили подобраны под общую тему диалога.
            """
            lbl = QLabel(text)
            lbl.setStyleSheet("""
                background-color: rgba(255,255,255,0.3);
                border-radius: 6px; padding:4px 8px;
                font-size: 14pt; color:#333;
            """)
            lbl.setFont(QFont("", 14))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl

        # ---------------- 1) Первый и последний мотор --------------------
        self.sb_start = QSpinBox()
        self.sb_start.setRange(0, self.hyps['n_motors'] - 1)
        self.sb_start.setValue(self.hyps['num_motor_start'])

        self.sb_end = QSpinBox()
        self.sb_end.setRange(0, self.hyps['n_motors'] - 1)
        self.sb_end.setValue(self.hyps['num_motor_end'])

        form.addRow(make_label("Первый мотор:"), self.sb_start)
        form.addRow(make_label("Последний мотор:"), self.sb_end)

        # ---------------- 2) Шаг по моторам ------------------------------
        self.cb_step = QComboBox()
        self.cb_step.setStyleSheet("""
            QComboBox {
                background-color: rgba(255,255,255,0.9);
                border: none;
                border-radius: 8px;
                /* чуть больший отступ справа, чтобы текст не упирался */
                padding: 6px 12px 6px 6px;
                font-size: 12pt;
                color: #333;
            }
            /* делаем область drop-down нулевой ширины */
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 0px;
                border: none;
            }
            /* окончательно убираем саму стрелку, даже в раскрытом состоянии */
            QComboBox::down-arrow,
            QComboBox::down-arrow:on {
                image: none;
                width: 0px;
                height: 0px;
            }
            /* стиль выпадающего списка */
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ccc;
                padding: 4px;
            }
        """)

        step_container = QWidget()
        hl = QHBoxLayout(step_container)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        hl.addWidget(self.cb_step)
        form.addRow(make_label("Шаг моторов:"), step_container)

        # ---------------- 3) Список PWM-значений -------------------------
        self.le_pwms = QLineEdit()
        self.le_pwms.setPlaceholderText("14,22,36,60,100")
        self.le_pwms.setText(",".join(map(str, self.hyps['pmpwm_pwm_values'])))
        form.addRow(make_label("PWM-значения:"), self.le_pwms)

        # ---------------- 4) Повторы PWM ---------------------------------
        self.sb_repeats = QSpinBox()
        self.sb_repeats.setRange(1, 20)
        self.sb_repeats.setValue(self.hyps['pmpwm_repeats'])
        form.addRow(make_label("Повторы PWM:"), self.sb_repeats)

        # ---------------- 5) Кнопка «Начать обучение» --------------------
        self.btn_train = QPushButton("Начать обучение")
        self.btn_train.setFixedWidth(220)
        self.btn_train.setStyleSheet("""
            background-color: rgba(255,255,255,0.9);
            border:none; border-radius:8px; padding:10px 20px;
            font-size:13pt; color:#333;
        """)
        # Отдельный горизонтальный layout, чтобы кнопка была по центру
        hl_train = QHBoxLayout()
        hl_train.addStretch()
        hl_train.addWidget(self.btn_train)
        hl_train.addStretch()

        # Стилизуем spinbox'ы и combobox
        for w in (self.sb_start, self.sb_end, self.sb_repeats, self.le_pwms):
            if isinstance(w, QSpinBox):
                w.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            w.setStyleSheet("""
                background-color: rgba(255,255,255,0.9);
                border:none; border-radius:8px; padding:6px;
                font-size:12pt; color:#333;
            """)

        # ---------------- Кнопки OK / Cancel ------------------------------
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        for b in buttons.buttons():
            b.setStyleSheet("""
                background-color: rgba(255,255,255,0.9);
                border:none; border-radius:8px; padding:8px;
                font-size:12pt; color:#333;
            """)

        v.addLayout(form)
        # 1) растягиватель перед кнопкой
        v.addStretch(1)
        v.addLayout(hl_train)
        # 2) растягиватель после кнопки
        v.addStretch(1)
        v.addWidget(buttons)

        # ---------------- Сигналы/слоты ----------------------------------
        # При изменении диапазона моторов — пересчитать допустимые шаги.
        self.sb_start.valueChanged.connect(self._on_range_changed)
        self.sb_end.valueChanged.connect(self._on_range_changed)
        # Кнопка «Начать обучение» — открыть учебное окно.
        self.btn_train.clicked.connect(self._start_training)
        # Первичная инициализация доступных шагов по текущему диапазону.
        self._on_range_changed()

    # ---------------- Вспомогательные методы -----------------------------
    @staticmethod
    def _allowed_steps(total: int) -> list[int]:
        """
        Возвращает список допустимых шагов по диапазону моторов.

        Правило простое:
          - 1 всегда доступен;
          - 2 доступен, если диапазон делится на 2;
          - 3 доступен, если диапазон делится на 3.

        Параметры:
            total: Размер диапазона (кол-во моторов в выборке), >= 1.

        Возвращает:
            Отсортированный список уникальных шагов (1, 2, 3).
        """
        steps = [1]
        if total % 2 == 0:
            steps.append(2)
        if total % 3 == 0:
            steps.append(3)
        return sorted(set(steps))

    def _on_range_changed(self):
        """
        Пересчитывает доступные значения шага при изменении границ диапазона.
        """
        # Количество моторов в диапазоне: последняя позиция включительно.
        total = max(1, self.sb_end.value() - self.sb_start.value() + 1)
        allowed = self._allowed_steps(total)
        # Обновляем комбобокс значениями 1/2/3 (в зависимости от total).
        self.cb_step.clear()
        self.cb_step.addItems([str(s) for s in allowed])
        # По умолчанию выбираем шаг 2, если он допустим, иначе — первый из списка.
        self.cb_step.setCurrentText('2' if '2' in [str(s) for s in allowed] else self.cb_step.itemText(0))

    # ---------------- Рисование фона с градиентом ------------------------
    def paintEvent(self, _):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#2ECC71"))
        grad.setColorAt(1.0, QColor("#1ABC9C"))
        painter.fillRect(self.rect(), grad)

    # ---------------- Сбор итоговых гиперпараметров ----------------------
    def get_hyps(self) -> dict:
        """
        Собирает актуальные значения гиперпараметров из виджетов.

        Возвращаемое значение — та же структура ключей, что и на входе,
        но с обновлёнными полями диапазона, шага, повторов и списка PWM.

        Возвращает:
            dict[str, Any]: Обновлённые гиперпараметры.
        """
        h = self.hyps
        h['num_motor_start']  = self.sb_start.value()
        h['num_motor_end']    = self.sb_end.value()
        h['use_motors_step']  = int(self.cb_step.currentText())
        h['pmpwm_repeats']    = self.sb_repeats.value()

        # Разбор PWM-строки: поддерживаем гибкие пробелы, убираем дубли, сортируем.
        txt = self.le_pwms.text().strip()
        try:
            pwms = [int(x) for x in txt.split(',') if x.strip()]
            pwms = sorted(set(pwms))
            if not pwms:
                raise ValueError
        except Exception:
            # Если парсинг не удался — откатываем список PWM к исходному.
            pwms = self.hyps['pmpwm_pwm_values']
        h['pmpwm_pwm_values'] = pwms
        return h
    

    # ---------------- Запуск учебного окна -------------------------------
    def _start_training(self):
        """Запуск обучающего окна."""
        
        # 1) Собираем актуальные параметры из формы.
        hyps = self.get_hyps()

        # 2) Вычисляем список моторов
        motors = list(range(
            hyps['num_motor_start'],
            hyps['num_motor_end'] + 1,
            hyps['use_motors_step']
        ))

        # 3) Получаем VibroBox от главного окна
        from gui.pmpwm_training_window import PMPWMTrainingWindow
        main_win = self.parent()
        vibro = getattr(main_win, 'vibro', None)

        # 4) Создаём и показываем окно обучения.
        self.train_win = PMPWMTrainingWindow(
            vibro=vibro,
            motors=motors,
            pwm_values=hyps['pmpwm_pwm_values'],
            parent=self
        )
        self.train_win.show()

