# gui/mols_probe_window.py

"""
Окно MOLs‑теста.
"""

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow

class MOLsProbeWindow(QMainWindow):
    """
    Виджет для одного шага MOLs-теста, загружаемый из файла window1.ui.
    
    В .ui предполагаются объекты:
      - QLabel с objectName="instruction"
      - QLabel с objectName="TextLabel"
      - QLabel с objectName="VibrationLabel"
      - QPushButton с objectName="btnYes"
      - QPushButton с objectName="btnNo"
      - QPushButton с objectName="btnHome"
    """

    def __init__(self, total_steps: int, tests_per_motor: int, parent=None):
        """
        Инициализирует окно шага MOLs-теста.

        Параметры:
            total_steps: Общее число шагов теста (глобально).
            tests_per_motor: Число локальных шагов на один мотор.
            parent: Родительское окно (обычно MainWindow).
        """
        super().__init__(parent)

        # 1) Загрузка интерфейса из .ui
        uic.loadUi('gui/window1.ui', self)

        self.main_win = parent

        # 2) Сохраняем общее число шагов и число тестов на мотор
        self.total_steps = total_steps
        self.tests_per_motor = tests_per_motor

        # 3) Задаём начальные метки «Мотор 0» и «Шаг 0/tests_per_motor»
        self.TextLabel.setText(f'Мотор 0, шаг 0/{self.tests_per_motor}')

        # 4) Отключаем фокус у кнопок, чтобы стрелки всегда работали
        for btn in (self.btnYes, self.btnNo):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # 5) Привязываем клики мышью к обработчику ответов
        self.btnYes.clicked.connect(lambda: self.on_answer('y'))
        self.btnNo.clicked.connect(lambda: self.on_answer('n'))

        self.btnHome.clicked.connect(self._go_home)

        self.VibrationLabel.setText('')

    
    def update_status(self, motor_idx: int, step_global: int, mode: str):
        """
        Обновление статусной информации в интерфейсе.
        
        Параметры:
            motor_idx: индекс текущего мотора
            step_global: глобальный номер шага теста
            mode: режим работы ("Увеличение мощности"/"Уменьшение мощности")
        """
        local = ((step_global - 1) % self.tests_per_motor) + 1
        self.TextLabel.setText(f'Мотор {motor_idx}, шаг {local}/{self.tests_per_motor}')
        self.VibrationLabel.setText(mode)


    def on_answer(self, ans: str):
        """
        Обработчик выбора пользователя ("Чувствую"/"Не чувствую").
        Передаёт ответ потоку через родительский MainWindow.
        
        Параметры:
            ans: символ ответа ('y' - да, 'n' - нет)
        """
        # Предполагаем, что родитель — это MainWindow, у него есть self.worker
        mw = self.window()                                     # получаем корневое окно
        if hasattr(mw, 'worker') and mw.worker is not None:    # если есть рабочий поток
            mw.worker.set_answer(ans)                          # передаем ответ
    


    def _go_home(self):
        """Возврат в главное меню с корректной остановкой теста."""
        # 1) Останавливаем тестовый поток
        if hasattr(self.main_win, 'worker') and self.main_win.worker.isRunning():
            self.main_win.worker.stop()
            self.main_win.worker.wait(1000)
        # 2) Выключаем моторы
        self.main_win.vibro.reset_pwm_values()
        # 3) Закрываем окно теста
        self.close()
        # 4) Восстанавливаем главное меню
        self.main_win._build_start_ui()
        self.main_win.show()
