# gui/main_window.py

"""
Главное окно приложения.

Задачи модуля:
- создание и оформление стартового окна;
- подключение к устройству VibroBox;
- запуск трёх тестов (MOLs, Spatial, PM-PWM) и обработка их завершения;
- запуск окна анализа и формирование итогового summary;
- обработка всех основных сигналов и переходов между окнами.
"""

import json
import numpy as np
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import (
    QKeySequence, QShortcut, QPainter, QLinearGradient,
    QColor
)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox, QDialog
)

from core.config import default_hyps
from core.paths  import build_file_base
from core.serial_api import VibroBox

from core.mols_test import MolsWorker
from gui.mols_probe_window import MOLsProbeWindow
from gui.mols_hyperparams_dialog import MOLsHyperparamsDialog

from core.spatial_test import SpatialWorker
from gui.spatial_probe_window import SpatialProbeWindow
from gui.spatial_hyperparams_dialog import SpatialHyperparamsDialog

from core.pmpwm_test import PMPWMWorker
from gui.pmpwm_probe_window import PMPWMProbeWindow
from gui.pmpwm_hyperparams_dialog import PMPWMHyperparamsDialog

from gui.analysis_dialog import AnalysisDialog
from core.report_utils import generate_summary 


class MainWindow(QMainWindow):
    """
    Главное окно приложения: стартовое меню, подключение, запуск тестов.
    """
    def __init__(self):
        super().__init__()
        self.resize(600, 400)
        self.setWindowTitle('Вибротактильная диагностика')
        
        # --- Основные переменные состояния ---
        self.vibro = VibroBox()             # Интерфейс к устройству. Создаётся один раз при инициализации окна.
        self.worker = None                  # Текущий фоновый поток выполняемого теста. Между тестами равен None.
        self.current_surname: str = ""      # Текущая фамилия пациента; сохраняется между тестами в пределах сессии.

        self._build_start_ui()

    # =====================================================================
    #                       UI-ПОМОЩНИКИ
    # =====================================================================
    
    def _apply_widget_style(self, w):
        """
        Применяет единый стиль для кнопок и полей ввода:
        закруглённый белый фон с небольшим паддингом.
        """
        w.setStyleSheet("""
            background-color: rgba(255,255,255,0.9);
            border: none;
            border-radius: 12px;
            padding: 8px;
            font-size: 12pt;
            color: #333;
        """ )


    def paintEvent(self, event):
        """Градиентный фон: сверху-зелёный, снизу-бирюзовый."""
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#2ECC71"))
        grad.setColorAt(1.0, QColor("#1ABC9C"))
        painter.fillRect(QRect(0, 0, self.width(), self.height()), grad)


    def _set_connected_ui(self) -> None:
        """Отображает статус «Подключено» и разблокирует кнопки тестов."""
        self.lbl_status.setText('✔️ Подключено')
        self.lbl_status.setStyleSheet("""
            background-color: rgba(255,255,255,0.3);
            border-radius: 8px;
            padding: 4px 12px;
            font-size: 11pt;
            color: #27ae60;
        """)

        for b in (self.btn_start, self.btn_spatial, self.btn_pmpwm):
            b.setEnabled(True)

    # =====================================================================
    #             ПОСТРОЕНИЕ СТАРТОВОГО ЭКРАНА / ГЛАВНОГО МЕНЮ
    # =====================================================================

    def _build_start_ui(self):
        """Создаёт стартовое окно с кнопками запуска тестов."""
        
        # Создаём контейнер для элементов
        w = QWidget()
        self.setCentralWidget(w)

        # Поле ввода фамилии
        self.le_name = QLineEdit(self.current_surname)
        self.le_name.setPlaceholderText('Фамилия пациента')
        # Когда оператор закончил вводить фамилию ‒ запоминаем её
        self.le_name.editingFinished.connect(
            lambda: setattr(self, "current_surname",
                            self.le_name.text().strip()))
        self.le_name.setMaximumWidth(400)
        self._apply_widget_style(self.le_name)

        # Кнопка "Подключиться"
        self.btn_connect = QPushButton('Подключиться')
        self.btn_connect.setMaximumWidth(400)
        self._apply_widget_style(self.btn_connect)

        # Кнопка "Начать MOLs-тест тест"
        self.btn_start = QPushButton('Начать MOLs-тест')
        self.btn_start.setMaximumWidth(400)
        self.btn_start.setEnabled(False)
        self._apply_widget_style(self.btn_start)

        # Кнопка "Начать Spatial-тест"
        self.btn_spatial = QPushButton('Начать Spatial-тест')
        self.btn_spatial.setMaximumWidth(400)
        self.btn_spatial.setEnabled(False)
        self._apply_widget_style(self.btn_spatial)

        # Кнопка "Начать PM-PWM-тест"
        self.btn_pmpwm = QPushButton('Начать PM-PWM-тест')
        self.btn_pmpwm.setMaximumWidth(400)
        self.btn_pmpwm.setEnabled(False)
        self._apply_widget_style(self.btn_pmpwm)

        # Кнопка "Провести анализ" 
        self.btn_analyze = QPushButton('Провести анализ')
        self.btn_analyze.setMaximumWidth(400)
        self._apply_widget_style(self.btn_analyze)
        
        # Статус подключения
        self.lbl_status = QLabel('❌ Не подключено')
        self.lbl_status.setMaximumWidth(200)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("""
            background-color: rgba(255,255,255,0.3);
            border-radius: 8px;
            padding: 4px 12px;
            font-size: 11pt;
            color: #e74c3c;
        """)

        # Layout: центральные виджеты по центру, статус ниже
        layout = QVBoxLayout(w)
        layout.addStretch()
        layout.addWidget(self.le_name)
        layout.addWidget(self.btn_connect)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_spatial)
        layout.addWidget(self.btn_pmpwm)
        layout.addWidget(self.btn_analyze)
        layout.addStretch()
        layout.addWidget(self.lbl_status)

        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 40, 0, 20)
        layout.setSpacing(16)

        # Подключение сигналов кнопок
        self.btn_connect.clicked.connect(self._connect)
        self.btn_start.clicked.connect(self._start_test)
        self.btn_spatial.clicked.connect(self._start_spatial_test)
        self.btn_pmpwm.clicked.connect(self._start_pmpwm_test)
        self.btn_analyze.clicked.connect(self.open_analysis_dialog)

        # Если устройство уже подключено — сразу отобразить статус
        if self.vibro.ser and self.vibro.ser.is_open:
            self._set_connected_ui()

    # =====================================================================
    #                         ПОДКЛЮЧЕНИЕ
    # =====================================================================
    
    def _connect(self) -> None:
        """
        Подключение к VibroBox.

        При повторном нажатии:
        • если порт уже открыт — просто обновляем UI;
        • иначе пытаемся открыть новый.
        """
        
        # Порт уже открыт → UI-обновление без попытки reconnect
        if self.vibro.ser and self.vibro.ser.is_open:
            self._set_connected_ui()
            return

        # Порт закрыт → обычное автоматическое подключение
        if self.vibro.connect_auto():
            self._set_connected_ui()
        else:
            QMessageBox.critical(
                self, 'Ошибка', 'VibroBox не найден.'
            )

    # =====================================================================
    #                          MOLs-ТЕСТ
    # =====================================================================

    def _start_test(self):
        """Запускает процедуру MOLs-теста."""
        
        # 1) Собираем базовые гиперпараметры по фамилии
        surname = self.current_surname or 'anon'
        
        # Импортируем здесь, чтобы не загружать модуль раньше времени
        import core.config
        self.hyps = core.config.default_hyps(surname)

        # 2) Показываем диалог редактирования гиперпараметров
        dlg = MOLsHyperparamsDialog(self.hyps, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return   # пользователь отменил — остаёмся на стартовом экране
        # Обновляем self.hyps новыми значениями
        self.hyps = dlg.get_hyps()

        # 3) Мигаем индикатором начала
        self.vibro.begin_end_indicator()

        # 4) Через 1.5 с запускаем остальную логику теста
        QTimer.singleShot(1500, self._start_test_after_delay)

    def _start_test_after_delay(self):
        """
        Создаёт поток MOLs, окно опроса и соединяет все сигналы.
        Запускает тест и назначает горячие клавиши «да/нет».
        """

        # 1) Берём уже отредактированные гиперпараметры
        hyps = self.hyps

        motor_count     = ((hyps['num_motor_end'] - hyps['num_motor_start']) // hyps['use_motors_step'] + 1)
        total_steps     = motor_count * hyps['exps_for_each_motor'] * 2
        tests_per_motor = hyps['exps_for_each_motor'] * 2

        # 2) Создаём воркер
        self.worker = MolsWorker(self.vibro, hyps)

        # 3) Создаём окно теста
        # Передаём parent=self, чтобы ProbeWindow видел MainWindow
        self.probe_win = MOLsProbeWindow(total_steps, tests_per_motor, parent=self)
        self.probe_win.worker = self.worker     # Окно может слать ответы в поток

        # 4) Подключаем сигналы
        self.worker.progress.connect(
            lambda m, done, total, mode: self.probe_win.update_status(m, done, mode)
        )
        self.worker.vibrationStarted.connect(
            lambda: self.probe_win.ProcessLabel.setText('ВИБРАЦИЯ')
        )
        self.worker.awaitingAnswer.connect(
            lambda: self.probe_win.ProcessLabel.setText('Почувствовали?')
        )
        self.worker.finished.connect(lambda res: self._on_finished(res, hyps))

        # 5) Показываем окно теста и скрываем главное
        self.probe_win.show()
        self.hide()

        # 6) Запускаем тест
        self.worker.start()

        # 7) Глобальные шорткаты
        QShortcut(QKeySequence(Qt.Key.Key_Left),  self.probe_win,
                  activated=lambda: self.worker.set_answer('y'))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self.probe_win,
                  activated=lambda: self.worker.set_answer('n'))


    def _on_finished(self, results: dict, hyps: dict):
        """Завершение MOLs‑теста: сохранение JSON и возврат в главное меню."""
             
        base = build_file_base(hyps["user_surname"], "mols")

        json_path = base.parent / f"{base.name}_results.json"

        with open(json_path, "w", encoding="utf8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        QMessageBox.information(
            self, "MOLs-тест завершён",
            f"Результаты сохранены в\n{json_path}"
        )

        # Закрываем окно теста и возвращаем главное
        self.probe_win.close()
        self.show()
        self._build_start_ui()

    # ==================================================================
    #                           SPATIAL-ТЕСТ
    # ==================================================================

    def _start_spatial_test(self):
        """Запускает процедуру Spatial-теста."""

        # 1) Берём базовые гиперпараметры по фамилии
        surname = self.current_surname or 'anon'
        self.hyps = default_hyps(surname)

        # 2) Показываем диалог Spatial-гиперпараметров
        dlg = SpatialHyperparamsDialog(self.hyps, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return  # если отменили, остаёмся на стартовом экране
        self.hyps = dlg.get_hyps()

        # 3) Индикатор начала, как для MOLs-теста
        self.vibro.begin_end_indicator()
        QTimer.singleShot(1500, self._start_spatial_after_delay)


    def _start_spatial_after_delay(self):
        """Создаёт поток/окно Spatial и связывает сигналы/слоты."""

        # 1) Берём уже отредактированные гиперпараметры
        hyps = self.hyps
        
        # 2) Запускаем воркер
        self.worker = SpatialWorker(self.vibro, hyps, mode=hyps['spatial_mode'])
        self.worker.awaitingAnswer.connect(self._spatial_wait)
        self.worker.progress.connect(self._spatial_progress)
        self.worker.finished.connect(self._spatial_finished)
        self.worker.start()

        # 3) Открываем окно вопросов
        total_motors = hyps['num_motor_end'] - hyps['num_motor_start'] + 1      # Считаем число моторов включительно:
        n_pairs = total_motors // hyps['use_motors_step']                       # И только потом делим на шаг
        self.probe_win = SpatialProbeWindow(n_pairs, self._apply_widget_style, parent=self)
        self.probe_win.show()

        # Закрываем главное окно
        self.hide()


    def _spatial_wait(self):
        """Меняет подсказку в окне."""
        self.probe_win.lbl_info.setText('Где ощущение? Нажмите номер…')


    def _spatial_progress(self, done: int, total: int):
        """Выводит краткий прогресс «N / M» на экране опроса."""
        self.probe_win.lbl_progress.setText(f'{done} / {total}')


    def _spatial_finished(self, result: dict):
        """Завершение Spatial‑теста: сохранение .npy и возврат в главное меню."""

        # 1) Закрываем окно опроса
        self.probe_win.close()

        # 2) Строим имя .npy-файла по той же логике с таймштампом и фамилией
        base   = build_file_base(self.current_surname, "spatial") 
        npy_path  = base.parent / f"{base.name}_results.npy"

        # 3) Подготавливаем массив ответов
        answers = np.array(result['answers'], dtype=int)

        # 4) Убедимся, что папка существует и сохраняем
        npy_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(npy_path, answers)

        # 5) Показываем пользователю сообщение и возвращаем UI
        QMessageBox.information(
            self,
            'Spatial-тест завершён',
            f"Результаты сохранены в файле:\n{npy_path}"
        )
        self._build_start_ui()
        self.show()
    

    # ==================================================================
    #                           PM-PWM-ТЕСТ
    # ==================================================================

    def _start_pmpwm_test(self):
        """
        Запускает процедуру PM‑PWM‑теста.
        
        Логика аналогична другим тестам.
        """

        surname = self.current_surname or 'anon'
        self.hyps = default_hyps(surname)

        dlg = PMPWMHyperparamsDialog(self.hyps, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.hyps = dlg.get_hyps()

        self.vibro.begin_end_indicator()
        QTimer.singleShot(1500, self._start_pmpwm_after_delay)


    # Переменные, которые используются при перезаписывании данных
    _pending_queue:     list[int] = []      # Очередь моторов к дозапуску
    motors_all:         list[int] = []      # Полный список моторов
    motors_completed:   set[int]  = set()   # Завершённые моторы
    results_pmpwm:      dict[int, list[tuple[int,int]]] = {}


    def drop_partial_pmpwm_data(self, motor_idx: int):
        """
        Удаляет частично собранные ответы конкретного мотора.

        Используется при уходе пользователя в «Обучение»:
        если мотор не был завершён, его промежуточные ответы стираются,
        чтобы переписать их заново.
        """

        if hasattr(self, "results_pmpwm"):
            self.results_pmpwm.pop(motor_idx, None)


    def _launch_pmpwm_worker(self, motors_list: list[int]):
        """
        Запускает новый поток PM-PWM-теста.
        
        Если старый воркер ещё жив (теоретически), аккуратно останавливает его.
        """

        # 1)  создаём новый воркер с нужной очередью моторов
        h = self.hyps
        self.worker = PMPWMWorker(self.vibro, h, motors_list)

        # 2)  (пере-)подключаем сигналы к текущему probe-окну
        self.worker.progress.connect(
            lambda m, d, t: self.probe_win.update_status(m, d, t)
        )
        self.worker.awaitingAnswer.connect(
            lambda: self.probe_win.lbl_prompt.setText("Какой уровень?")
        )
        self.worker.motorFinished.connect(self._on_motor_done)
        self.worker.finished.connect(self._on_partial_finished)

        self.worker.start()


    def _start_pmpwm_after_delay(self):
        """Старт PM‑PWM по всем моторам диапазона, затем дозапуск очереди."""

        h = self.hyps
        motors = list(range(
            h['num_motor_start'], h['num_motor_end'] + 1, h['use_motors_step']
        ))

        self.motors_all       = motors             # Список всех моторов
        self.motors_completed = set()              # Какие уже готовы
        self.results_pmpwm    = {}                 # {motor: [...]}
        self._pending_queue   = []                 # Список моторов, которые ждут запуска

        # Создаём окно опроса и показываем
        n_levels = len(h['pmpwm_pwm_values'])
        self.probe_win = PMPWMProbeWindow(
            n_levels, self._apply_widget_style, parent=self
        )

        self.probe_win.show()
        self.hide()
        
        # Первый запуск — полный список
        self._launch_pmpwm_worker(motors)


    def _on_motor_done(self, motor: int):
        """
        Слот «мотор завершён»: переносим ответы из потока в общий словарь
        и проверяем, все ли моторы уже готовы.
        """
        self.motors_completed.add(motor)
        # Копируем свежие ответы
        self.results_pmpwm[motor] = self.worker.results[motor]

        if self.motors_completed == set(self.motors_all):
            self.probe_win.show_finish()    # Кнопка «Завершить тест»


    def _on_partial_finished(self, _):
        """
        Слот «поток завершился» (полный или одиночный).
        Если есть очередь `_pending_queue` — дозапускаем её одним пакетом.
        """

        if self._pending_queue:
            next_batch = self._pending_queue.copy()
            self._pending_queue.clear()
            self._launch_pmpwm_worker(next_batch)


    def _finish_pmpwm(self):
        """Финализация PM‑PWM: агрегация метрик, построение матриц ошибок."""
        
        # 1) Собираем общий список ответов
        all_ans = sum(self.results_pmpwm.values(), [])

        # 2) Точность по каждому мотору
        per_motor_acc: dict[int, float] = {}
        for m in self.motors_all:
            local = self.results_pmpwm.get(m, [])
            if not local:
                per_motor_acc[m] = 0.0
                continue
            ok = sum(t == p for t, p in local)
            per_motor_acc[m] = ok / len(local)

        mean_acc = np.mean(list(per_motor_acc.values())) if per_motor_acc else 0.0

        # 3) Локальные confusion‑матрицы по моторам
        pwm_vals = self.hyps["pmpwm_pwm_values"]
        levels   = len(pwm_vals)
        conf_per_motor: dict[int, np.ndarray] = {}
        for m, pairs in self.results_pmpwm.items():
            cm_local = np.zeros((levels, levels), dtype=int)
            for t, p in pairs:
                cm_local[t-1, p-1] += 1
            conf_per_motor[m] = cm_local

        # 4) Общая confusion‑matrix
        pwm_vals = self.hyps["pmpwm_pwm_values"]
        levels   = len(pwm_vals)
        cm = np.zeros((levels, levels), dtype=int)
        for t, p in all_ans:
            cm[t-1, p-1] += 1

        # 5) Формируем словарь результатов
        res = {
            "answers": all_ans,
            "per_motor_accuracy": per_motor_acc,
            "mean_accuracy": mean_acc,
            "confusion": cm.tolist(),
            "pwm_values": pwm_vals,
            "repeats": self.hyps["pmpwm_repeats"],
            "confusion_per_motor": {m: cm.tolist()
                        for m, cm in conf_per_motor.items()},
        }
        self._pmpwm_finished(res)


    def _run_pmpwm_for_motor(self, motor: int):
        """Перезапуск PM‑PWM только для одного мотора."""
        
        # 1) Останавливаем текущий воркер аккуратно
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1000)

        # 2) Удаляем старые данные мотора, чтобы переписать с нуля
        self.motors_completed.discard(motor)
        self.results_pmpwm.pop(motor, None)

        # 3) Формируем pending-очередь = (все ещё не завершённые, кроме выбранного)
        rest = [m for m in self.motors_all
                if m not in self.motors_completed and m != motor]
        self._pending_queue = rest

        # 4) Запускаем воркер только на выбранный мотор
        self._launch_pmpwm_worker([motor])


    def _pmpwm_finished(self, res: dict):
        """
        Сохранение результатов PM‑PWM и информирование пользователя.

        Сохраняем:
        • NPY с парами (true_level, predicted_level);
        • JSON с метриками и confusion-matrix;
        • PNG общей и помоторных confusion-matrix;
        • PNG scatter‑графиков PM‑PWM для каждого мотора.
        """

        # 1) Определяем дериктории
        base   = build_file_base(self.current_surname, "pmpwm")
        json_path = base.parent / f"{base.name}_results.json"
        npy_path  = base.parent / f"{base.name}_results.npy"
        png_path  = base.parent / f"{base.name}_conf.png"

        # 2) Сохраняем NPY
        np.save(npy_path, np.array(res["answers"], dtype=int))

        # 3) Сохраняем JSON
        try:
            with open(json_path, "w", encoding="utf8") as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
        except Exception as e:
            json_path = f"Ошибка сохранения JSON: {e}"

        # 4a) PNG общей confusion-matrix
        try:
            import matplotlib.pyplot as plt

            cm = np.array(res["confusion"])
            plt.figure(figsize=(4, 4))
            plt.imshow(cm, cmap="Blues")

            '''
            Шесть нижних строчек кода нужны для того,
            чтоб в CM нормально прописывались оценки 1-5, а не 0-4
            '''
            pwm_vals = self.hyps["pmpwm_pwm_values"]
            levels   = len(pwm_vals)
            ticks  = np.arange(levels)
            labels = [str(i) for i in range(1, levels+1)]
            plt.xticks(ticks, labels)
            plt.yticks(ticks, labels)

            plt.colorbar()
            for (i, j), val in np.ndenumerate(cm):
                plt.text(j, i, str(val), ha="center", va="center", color="black")
            plt.xlabel("Предсказано")
            plt.ylabel("Истина")
            plt.tight_layout()
            plt.savefig(png_path, dpi=150)
            plt.close()
        except Exception as e:
            png_path = f"PNG-не сохранён ({e})"
        
        # 4b) PNG confusion-matrix по каждому мотору
        png_paths_motors = []
        for m, cm_local in res.get("confusion_per_motor", {}).items():
            png_m = base.parent / f"{base.name}_motor{m}_conf.png"
            plt.figure(figsize=(4, 4))
            plt.imshow(np.array(cm_local), cmap="Blues")

            plt.title(f"Мотор {m}", fontsize=14, pad=8)

            '''
            Шесть нижних строчек кода нужны для того,
            чтоб в CM нормально прописывались оценки 1-5, а не 0-4
            '''
            pwm_vals = self.hyps["pmpwm_pwm_values"]
            levels   = len(pwm_vals)
            ticks  = np.arange(levels)
            labels = [str(i) for i in range(1, levels+1)]
            plt.xticks(ticks, labels)
            plt.yticks(ticks, labels)

            plt.colorbar()
            for (i, j), val in np.ndenumerate(cm_local):
                plt.text(j, i, str(val), ha="center", va="center", color="black")
            plt.xlabel("Предсказано"); plt.ylabel("Истина")
            plt.tight_layout(); plt.savefig(png_m, dpi=150); plt.close()
            png_paths_motors.append(png_m)

        # 4c) PNG scatter‑графика по каждому мотору
        pwm_vals = self.hyps["pmpwm_pwm_values"]
        png_paths_pm = []

        for m, pairs in self.results_pmpwm.items():
            if not pairs:
                continue

            x_pwm   = [pwm_vals[t-1] for t, _ in pairs]     # Истинный PWM
            y_stage = [p for _, p in pairs]                 # Предсказанный уровень

            plt.figure(figsize=(5, 3))
            plt.scatter(x_pwm, y_stage, marker='o')
            plt.title(f'PM-PWM motor {m}')
            plt.xlabel('PWM');  plt.ylabel('PM (уровень)')
            plt.yticks(range(1, len(pwm_vals)+1))
            plt.grid(True);  plt.tight_layout()

            png_sc = base.parent / f"{base.name}_motor{m}_pm_pwm.png"
            plt.savefig(png_sc, dpi=150); plt.close()
            png_paths_pm.append(png_sc)

        # 5) Сводка точности по моторам
        per_lines = [
            f"Мотор {m}: {acc*100:.1f} %"
            for m, acc in sorted(res["per_motor_accuracy"].items())
        ]
        per_text = "\n".join(per_lines)

        # 6) Сообщение пользователю
        msg_png_list = "\n".join(str(p) for p in
                         [png_path, *png_paths_motors, *png_paths_pm])
        QMessageBox.information(
            self,
            "PM-PWM-тест завершён",
            f"{per_text}\n─ Средняя: {res['mean_accuracy']*100:.1f} %\n\n"
            f"JSON: {json_path}\nNPY : {npy_path}\nPNG : \n{msg_png_list}"
        )

        # 7) Возвращаемся на главный экран
        self.probe_win.close()      # Закрыли окно опроса
        self._build_start_ui()      # Пересоздали центральный виджет
        self.show()                 # Снова делаем главное окно видимым
    
    # ==================================================================
    #                               АНАЛИЗ
    # ==================================================================

    def open_analysis_dialog(self):
        """
        Открывает диалог выбора входных файлов и запуска анализа.

        Проверяет существование выбранных файлов. Если всё в порядке —
        вызывает ``generate_summary`` и сообщает путь к финальному отчёту.
        """

        dlg = AnalysisDialog(self.current_surname, self._apply_widget_style, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        
        sel = dlg.selections()
        if not all(p.exists() for p in sel.values() if isinstance(p, Path)):
            QMessageBox.warning(self, "Ошибка", "Не все файлы существуют.")
            return
        
        out = generate_summary(sel)
        QMessageBox.information(self, "Анализ завершён", f"Итог сохранён в {out}")
