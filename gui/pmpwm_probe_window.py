# gui/pmpwm_probe_window.py

"""
Окно опроса уровней ощущения в PM-PWM тесте.

Здесь пользователь отвечает на вопрос «какой уровень?»
нажатием по кнопке или с помощью клавиатуры.

Окно также позволяет:
 • остановить текущий тест и вернуться в главное меню;
 • «переписать» (повторить) уже завершённый мотор;
 • временно уйти в режим обучения и затем корректно
   вернуться к тесту с правильной очередью моторов.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QKeySequence, QShortcut


class PMPWMProbeWindow(QMainWindow):
    """
    Окно опроса во время PM-PWM-теста.

    Пользователь видит:
      • текущий мотор и прогресс «N из M»;
      • сетку кнопок 1…n_levels для ответа «Какой уровень?»;
      • кнопки «Обучение», «Переписать», «Завершить тест», «Стоп».

    Горячие клавиши:
      • цифры 1…n_levels дублируют нажатие одноимённых кнопок.
    """

    def __init__(self, n_levels: int, style_fn, parent=None):
        """
        Создаёт окно опроса с сеткой кнопок 1…n_levels.

        Параметры:
            n_levels: Сколько уровней доступно пользователю (кол-во кнопок).
            style_fn: Функция стилизации виджетов (применяется к кнопкам).
            parent: Родительское окно.
        """
                
        super().__init__(parent)
        
        # Текущий мотор, для которого идёт опрос; заполняется в update_status().
        self._current_motor: int | None = None

        # Базовые параметры окна.
        self.setWindowTitle("PM-PWM-тест")
        self.setMinimumWidth(520)

        # Сохраняем внешние зависимости.
        self._apply_style = style_fn
        self.main_win     = parent

        # ---------- Центральная компоновка ----------
        central = QWidget(self)
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setAlignment(Qt.AlignmentFlag.AlignTop)
        v.setSpacing(20)

        # Заголовок (мотор и прогресс) — обновляется в update_status().
        self.lbl_title = QLabel('', alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet('font-size: 18pt;')
        v.addWidget(self.lbl_title)

        # Подсказка к опросу.
        self.lbl_prompt = QLabel('Какой уровень?', alignment=Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.lbl_prompt)

        # ---------- Сетка ответов 1…n_levels ----------
        # Кнопки 1…N
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(12)
        v.addLayout(g)

        cols = 5 # Кнопки делим на 5 столбцов (визуально компактно).
        for i in range(1, n_levels + 1):
            # Создаём кнопку с цифрой i
            btn = QPushButton(str(i))
            btn.setMinimumSize(75, 60)
            # Снимаем фокус, чтобы стрелки/цифры работали без «залипания».
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._apply_style(btn)
            btn.clicked.connect(lambda _, val=i: self._send_answer(val))
            r, c = divmod(i - 1, cols)
            g.addWidget(btn, r, c)

            # Горячая клавиша: нажатие цифры на клавиатуре эквивалентно клику.
            QShortcut(QKeySequence(str(i)), self,
                      activated=lambda val=i: self._send_answer(val))
        


        # ---------- Нижняя панель действий (слева направо) ----------
        hl_bottom = QHBoxLayout()
        hl_bottom.addStretch()

        # Кнопка «Обучение»: временно останавливает тест и открывает тренажёр.
        self.btn_train = QPushButton("Обучение")
        self._apply_style(self.btn_train)
        # вставляем *перед* btn_rewrite, чтобы оказаться слева
        hl_bottom.addWidget(self.btn_train, 0)      # индекс 0 ⇒ первый в ряду
        self.btn_train.clicked.connect(self._open_training)

        # Кнопка «Переписать»: повторный прогон конкретного уже завершённого мотора.
        self.btn_rewrite = QPushButton("Переписать")
        self._apply_style(self.btn_rewrite)
        self.btn_rewrite.clicked.connect(self._rewrite)
        hl_bottom.addWidget(self.btn_rewrite)

        # Кнопка «Завершить тест»: отображается только когда тест действительно готов.
        self.btn_finish = QPushButton("Завершить тест")
        self._apply_style(self.btn_finish)
        self.btn_finish.clicked.connect(self.main_win._finish_pmpwm)
        self.btn_finish.hide()                       # скрыта до ready
        hl_bottom.addWidget(self.btn_finish)

        hl_bottom.addStretch()
        v.addLayout(hl_bottom)

        # ---------- Отдельная строка с кнопкой «Стоп» ----------
        # «Стоп» мягко завершает текущий поток и возвращает на старт.
        hl = QHBoxLayout()
        hl.addStretch()
        self.btn_stop = QPushButton('Стоп')
        self._apply_style(self.btn_stop)
        self.btn_stop.clicked.connect(self._stop_test)
        hl.addWidget(self.btn_stop)
        v.addLayout(hl)

    # ======================================================================
    #                    СЛУЖЕБНЫЕ / ТЕХНИЧЕСКИЕ МЕТОДЫ
    # ======================================================================

    def paintEvent(self, _):
        """Рисует вертикальный градиентный фон для всего окна."""
        p = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#2ECC71"))
        grad.setColorAt(1.0, QColor("#1ABC9C"))
        p.fillRect(self.rect(), grad)

    # ======================================================================
    #                          ПУБЛИЧНЫЕ МЕТОДЫ API
    # ======================================================================

    def update_status(self, motor_idx: int, done: int, total: int):
        """Обновляет строку состояния: какой мотор сейчас и прогресс по нему."""
        # Запоминаем номер текущего мотора, чтобы кнопка «Обучение»
        # могла корректно обработать «возврат в тест».
        self._current_motor = motor_idx

        self.lbl_title.setText(f"Мотор {motor_idx} — {done}/{total}")


    def show_finish(self):
        """Делает видимой кнопку «Завершить тест»."""
        self.btn_finish.show()

    # ======================================================================
    #                           ОБРАБОТКА ДЕЙСТВИЙ
    # ======================================================================

    def _send_answer(self, val: int):
        """Отправляет ответ пользователя в рабочий поток."""
        w = self.main_win.worker
        if w:
            w.set_answer(val)


    def _stop_test(self):
        """Прерывает тест и возвращает пользователя на стартовый экран."""
        # 1) Мягко останавливаем поток
        w = self.main_win.worker
        if w and w.isRunning():
            w.stop()        # ставим флаг _stop=True
            w.wait(1000)    # ждём до 1 с, чтобы поток точно завершился

        # 2) Выключаем все моторы
        self.main_win.vibro.reset_pwm_values()

        # 3) Закрываем окно опроса
        self.close()

        # 4) Восстанавливаем главное меню
        self.main_win._build_start_ui()   # пересоздаёт центральный layout
        self.main_win.show()              # снова делает окно видимым


    def _rewrite(self):
        """Запросить перезапись одного из уже завершённых моторов."""
        finished = sorted(self.main_win.motors_completed)

        if not finished:
            QMessageBox.information(
                self, "Нет данных", "Сначала завершите хотя бы один мотор."
            )
            return

        # Диалог выбора мотора для перезаписи.
        motor_str, ok = QInputDialog.getItem(
            self, "Переписать мотор",
            "Выберите мотор:", [str(m) for m in finished], 0, False
        )
        if not ok:
            return
        motor = int(motor_str)

        # 1) Останавливаем текущий воркер аккуратно
        w = self.main_win.worker
        if w and w.isRunning():
            w.stop()
            w.wait(1000)

        # 2) Если мотор уже считался, удаляем его данные
        self.main_win.motors_completed.discard(motor)
        self.main_win.results_pmpwm.pop(motor, None)

        # 3) Формируем очередь: сначала переписываем motor,
        #    затем всё, что ещё НЕ завершено
        rest = [m for m in self.main_win.motors_all
                if m not in self.main_win.motors_completed and m != motor]
        self.main_win._pending_queue = rest          # запомнили «хвост»

        # 4) Запускаем воркер только для выбранного мотора
        self.main_win._launch_pmpwm_worker([motor])


    def _open_training(self):
        """
        Ставит текущий тест на паузу (с удалением частичных данных текущего незавершённого мотора),
        открывает окно обучения в «свободном» режиме и при закрытии тренажёра
        корректно возобновляет тест по сохранённой очереди.
        """
        w = self.main_win.worker
        if w and w.isRunning():
            # 1) Какой мотор сейчас в работе?
            current_motor = self._current_motor         # поле уже есть в воркере
            # 2) Останавливаем поток полностью (не pause, а именно stop/wait)
            w.stop()
            w.wait(1000)

            # 3) Удаляем частичные ответы этого мотора, если что-то накопили
            self.main_win.drop_partial_pmpwm_data(current_motor)

            # 4) Формируем очередь: этот мотор + все незавершённые
            pending = [current_motor] + [
                m for m in self.main_win.motors_all
                if m not in self.main_win.motors_completed and m != current_motor
            ]

            self.main_win._pending_queue = pending
        else:
            # Поток уже завершён — очищаем очередь «на всякий».
            self.main_win._pending_queue = []

        # 5) Открываем обучающее окно в free-mode
        from gui.pmpwm_training_window import PMPWMTrainingWindow # локальный импорт, чтобы не плодить зависимость
        self._train_win = PMPWMTrainingWindow(
            vibro=self.main_win.vibro,
            motors=self.main_win.motors_all,
            pwm_values=self.main_win.hyps['pmpwm_pwm_values'],
            free_mode=True,
            parent=self,
        )
        self._train_win.closed.connect(self._resume_test)
        self._train_win.show()


    def _resume_test(self, _=None):
        """
        Возобновляет тест после закрытия окна обучения.

        Если очередь `_pending_queue` не пуста — запускаем воркер по ней.
        Если пуста — значит тест завершён, поэтому возвращаемся на главный экран.
        """
        queue = getattr(self.main_win, "_pending_queue", [])
        if queue:
            self.main_win._launch_pmpwm_worker(queue)
            # Очередь отработала — очищаем, чтобы не перезапуститься повторно
            self.main_win._pending_queue.clear()
        else:
            # Ничего не осталось — возвращаем пользователя на главный экран
            self.main_win._build_start_ui()
            self.main_win.show()









