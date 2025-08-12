# main.py

"""
Точка входа в приложение предпротезной диагностики вибротактильной обратной связи.

Модуль инициализирует графический интерфейс PyQt6, создавая экземпляр
:class:`gui.main_window.MainWindow`.

Если запустить файл напрямую, приложение стартует сразу.
"""

import sys
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 12))
    win = MainWindow()
    win.resize(500, 300)
    win.show()
    sys.exit(app.exec())


