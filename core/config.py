# core/config.py

"""
Конфигурация проекта.

Функция модуля (:func:`default_hyps`) позволяет
сформировать базовый набор гиперпараметров для пациента

"""

def default_hyps(user_surname: str) -> dict:
    """
    Создаёт словарь гиперпараметров по умолчанию для пациента.

    Параметры
    ----------
    user_surname : str
        Фамилия пациента, используется для организации выходных каталогов.

    Возвращает
    ----------
    dict[str, Any]
        Словарь с настройками для всех тестов (MOLs, Spatial, PM‑PWM).
    """
    return {
        # --- Общие параметры -------------------------------------------------
        'user_surname': user_surname,
        'motor_num': 0,
        'n_motors': 10,
        'time_sleep_param': 0.25,
        'num_motor_start': 0,
        'num_motor_end': 5,
        'use_motors_step': 2,

        # --- MOLs‑тест -------------------------------------------------------
        'exps_for_each_motor': 3,
        'end_pwm_down': 0,
        'end_pwm_up': 30,
        'delta_pwm_down': -5,
        'delta_pwm_up': 2,

        # --- Spatial‑тест ----------------------------------------------------
        'max_counter_samples': 20,  # сколько предъявлений всего
        'spatial_pwm': 30,          # базовый PWM для Spatial
        'spatial_mode': 'pairs',    # 'pairs' или 'single'

        # --- PM‑PWM‑тест -----------------------------------------------------
        'pmpwm_pwm_values': [14, 22, 36, 60, 100],
        'pmpwm_repeats': 4,         # сколько предъявлений на каждый PWM
    }