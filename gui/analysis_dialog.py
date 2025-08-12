# gui/analysis_dialog.py

"""
Диалоговое окно для выбора файлов анализа результатов тестов.

Модуль предоставляет класс :class:`AnalysisDialog`, который позволяет оператору
указать фамилию пациента и выбрать файлы результатов для трёх типов тестов:
MOLs, Spatial и PM-PWM.

Файлы выбираются автоматически — по последнему
созданному файлу в соответствующей папке,
но могут быть выбраны и вручную.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QPushButton,
    QFileDialog, QFormLayout, QHBoxLayout, QVBoxLayout
)

from PyQt6.QtGui import QPainter, QLinearGradient, QColor

from core.paths import sanitize, test_folder

# Расширения файлов результатов для каждого теста
EXTENSION = {
    "mols":    ".json",
    "spatial": ".npy",
    "pmpwm":   ".json",
}

class AnalysisDialog(QDialog):
    """Окно выбора параметров анализа результатов тестов."""

    def __init__(self, surname_default: str, style_fn, parent=None):
        """
        Параметры
        ---------
        surname_default : str
            Фамилия по умолчанию, подставляемая в поле ввода.
        style_fn : Callable
            Функция для применения общего стиля приложения к виджетам.
        parent : QWidget | None
            Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Параметры анализа")

        # Поле ввода фамилии
        self.editSurname = QLineEdit(surname_default)

        # Поля для путей к результатам тестов (только для чтения)
        self.pathMols    = QLineEdit(); self.pathMols.setReadOnly(True)
        self.pathSpatial = QLineEdit(); self.pathSpatial.setReadOnly(True)
        self.pathPmpwm   = QLineEdit(); self.pathPmpwm.setReadOnly(True)

        # Кнопки выбора файлов
        btnM, btnS, btnP = (QPushButton("…") for _ in range(3))

        # Кнопки управления
        ok = QPushButton("Начать анализ"); ok.clicked.connect(self.accept)
        cancel = QPushButton("Отмена");    cancel.clicked.connect(self.reject)
        
        # Применяем стиль ко всем виджетам
        # Функция, которую MainWindow использует, чтобы «красить» виджеты
        self._apply_style = style_fn

        # Применяем общмй стиль приложения ко всем виджетам
        for w in (self.editSurname,
                  self.pathMols, self.pathSpatial, self.pathPmpwm,
                  btnM, btnS, btnP,
                  ok, cancel):
            self._apply_style(w)

        # Макет с полями и кнопками выбора
        form = QFormLayout()
        form.addRow("Фамилия:", self.editSurname)
        for lbl, line, btn in (("MOLs-тест:", self.pathMols, btnM),
                              ("Spatial-тест:", self.pathSpatial, btnS),
                              ("PM-PWM-тест:", self.pathPmpwm, btnP)):
            row = QHBoxLayout(); row.addWidget(line); row.addWidget(btn)
            form.addRow(lbl, row)

        # Общий вертикальный макет
        v = QVBoxLayout(self); v.addLayout(form); v.addWidget(ok); v.addWidget(cancel)

        # Сигналы
        self.editSurname.editingFinished.connect(self._refresh_lists)
        for btn, test in ((btnM,"mols"), (btnS,"spatial"), (btnP,"pmpwm")):
            btn.clicked.connect(lambda _,c=test: self._pick_file(c))
        
        # Первичная подгрузка файлов
        self._refresh_lists()

        # Размеры окна
        self.resize(520, 300)       # окно откроется 520×300
        self.setMinimumWidth(480)   # и не даст ужаться слишком сильно

    # ------------------------------------------------------------------ #
    # Внутренние методы
    # ------------------------------------------------------------------ #

    def _refresh_lists(self):
        sn = sanitize(self.editSurname.text())

        def fill(line: QLineEdit, test: str):
            pattern = f"{test}_*{EXTENSION[test]}"
            latest  = next(
                iter(sorted(test_folder(sn, test).glob(pattern),
                            reverse=True)),
                None
            )
            if latest:
                line.setText(latest.name)
                line.setProperty("fullPath", str(latest))
            else:
                line.setText("— нет файлов —")
                line.setProperty("fullPath", "")

        fill(self.pathMols,    "mols")
        fill(self.pathSpatial, "spatial")
        fill(self.pathPmpwm,   "pmpwm")

    def _pick_file(self, test):
        """Открывает диалог выбора файла результата для указанного теста."""
        start_dir = test_folder(sanitize(self.editSurname.text()), test)
        extension = EXTENSION[test]
        filter_str = "NumPy (*.npy)" if extension == ".npy" else "JSON (*.json)"
        fn, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл результата",
            str(start_dir),
            filter_str
        )
        if fn:
            line = {"mols": self.pathMols,
                    "spatial": self.pathSpatial,
                    "pmpwm": self.pathPmpwm}[test]
            line.setText(Path(fn).name)
            line.setProperty("fullPath", fn)

    # ------------------------------------------------------------------ #
    # Публичные методы
    # ------------------------------------------------------------------ #

    def selections(self) -> dict:
        """Возвращает словарь с выбранными оператором путями к файлам и фамилией."""
        
        def p(line: QLineEdit):
            return Path(line.property("fullPath")) if line.property("fullPath") else None

        return {
            "surname": self.editSurname.text().strip(),
            "mols"   : p(self.pathMols),
            "spatial": p(self.pathSpatial),
            "pmpwm"  : p(self.pathPmpwm),
        }

    # ------------------------------------------------------------------ #
    # Переопределённые методы
    # ------------------------------------------------------------------ #
   
    def paintEvent(self, _):
        """Рисует градиентный фон, как в главном окне приложения."""
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#2ECC71"))
        grad.setColorAt(1.0, QColor("#1ABC9C"))
        painter.fillRect(self.rect(), grad)