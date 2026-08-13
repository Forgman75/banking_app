"""
Главный модуль приложения.
"""
import pandas as pd
import json
import logging
from pathlib import Path
from datetime import datetime

from src.services import cashback_categories, simple_search, phone_search, investment_bank
from src.files_reader import load_transactions_excel, load_transactions
from src.service_api import load_user_settings
from src.reports import spending_by_category, spending_by_weekday
from src.views import generate_home_page, generate_events_page


def setup_logging():
    """
    Настраивает логирование:
    - Все логи (INFO и выше) → в консоль
    - Только WARNING и ERROR из модуля service_api → в файл service_api.log
                                       files_reader → в файл files_reader.log
    """
    # Создаём директорию для логов, если её нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Общий формат для всех логов
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Консольный обработчик (все уровни INFO+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # Файловый обработчик для service_api (только WARNING+)
    api_file_handler = logging.FileHandler(
        log_dir / "service_api.log",
        encoding="utf-8",
        mode="a"  # "a" — дозапись, "w" — перезапись при каждом запуске
    )
    api_file_handler.setLevel(logging.WARNING)  # ← Только WARNING и выше
    api_file_handler.setFormatter(formatter)
    
    # Файловый обработчик для files_reader (только WARNING+)
    reader_file_handler = logging.FileHandler(
        log_dir / "files_reader.log",
        encoding="utf-8",
        mode="a"  # "a" — дозапись, "w" — перезапись при каждом запуске
    )
    reader_file_handler.setLevel(logging.WARNING)  # ← Только WARNING и выше
    reader_file_handler.setFormatter(formatter)

    # Привязываем файловый обработчик  к логгеру service_api
    services_logger = logging.getLogger("src.service_api")
    services_logger.addHandler(api_file_handler)

    # Привязываем файловый обработчик  к логгеру files_reader
    services_logger = logging.getLogger("src.files_reader")
    services_logger.addHandler(reader_file_handler)
    
    # Корневой логгер (для консоли)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)


FEATURES = {
    "home_page": {
        "function": generate_home_page,
        "runner": lambda f, df, records, date: (
            f(date)
        ),
    },

    "events_page": {
        "function": generate_events_page,
        "runner": lambda f, df, records, date: (
            run_events_page(f, date)
        ),
    },

    "cashback_categories": {
        "function": cashback_categories,
        "runner": lambda f, df, records, date: (
            run_cashback(f, records, date)
        ),
    },

    "investment_bank": {
        "function": investment_bank,
        "runner": lambda f, df, records, date: (
            run_investment(f, records, date)
        ),
    },

    "simple_search": {
        "function": simple_search,
        "runner": lambda f, df, records, date: (
            run_simple_search(f, records)
        ),
    },

    "phone_search": {
        "function": phone_search,
        "runner": lambda f, df, records, date: (
            run_phone_search(f, records)
        ),
    },

    "spending_by_category": {
        "function": spending_by_category,
        "runner": lambda f, df, records, date: (
            run_category_report(f, df, date)
        ),
    },

    "spending_by_weekday": {
        "function": spending_by_weekday,
        "runner": lambda f, df, records, date: (
            run_weekday_report(f, df, date)
        ),
    },
}


def run_home_page(function, date_str):
    """Главная страница."""

    return function(date_str)


def run_events_page(function, date_str):
    """Страница событий."""

    period = (
        input(
            "Введите период "
            "(W - неделя, M - месяц, Y - год, ALL - все) [M]: "
        )
        .strip()
        .upper()
        or "M"
    )

    return function(
        date_str=date_str,
        period=period,
    )


def run_cashback(function, transactions_list, date_str):
    """Анализ категорий повышенного кешбэка."""

    target_date = pd.to_datetime(date_str)

    year = target_date.year
    month = target_date.month

    return function(
        data=transactions_list,
        year=year,
        month=month,
    )


def run_investment(function, transactions_list, date_str):
    """Расчет Инвесткопилки."""

    target_date = pd.to_datetime(date_str)

    month = target_date.strftime("%Y-%m")

    limit_input = (
        input(
            "Введите шаг округления "
            "(10, 50 или 100) [50]: "
        )
        .strip()
        or "50"
    )

    try:
        limit = int(limit_input)
    except ValueError:
        print("Некорректный шаг. Используется 50.")
        limit = 50

    return function(
        month=month,
        transactions=transactions_list,
        limit=limit,
    )


def run_simple_search(function, transactions_list):
    """Простой поиск."""

    query = input(
        "Введите текст для поиска: "
    ).strip()

    if not query:
        print("Поисковый запрос не может быть пустым.")
        return None

    return function(
        query=query,
        transactions=transactions_list,
    )


def run_phone_search(function, transactions_list):
    """Поиск транзакций по телефонам."""

    return function(
        transactions=transactions_list
    )


def run_category_report(function, transactions_df, date_str):
    """Отчет по конкретной категории."""

    category = input(
        "Введите категорию расходов: "
    ).strip()

    if not category:
        print("Категория не может быть пустой.")
        return None

    return function(
        transactions=transactions_df,
        category=category,
        date=date_str,
    )


def run_weekday_report(function, transactions_df, date_str):
    """Отчет по дням недели."""

    return function(
        transactions=transactions_df,
        date=date_str,
    )


def print_result(result):
    """Красиво выводит результат функции."""

    if result is None:
        return

    if isinstance(result, pd.DataFrame):

        if result.empty:
            print("Нет данных.")
        else:
            print()
            print(result.to_string(index=False))

    elif isinstance(result, str):

        print(result)

    else:

        print(result)


def run_feature(
    feature_name,
    feature_config,
    transactions_df,
    transactions_list,
    date_str,
):
    """Запускает любую функцию из реестра."""

    logger = logging.getLogger(__name__)

    feature = FEATURES.get(feature_name)

    if feature is None:
        print(
            f"Функция '{feature_name}' "
            f"не зарегистрирована."
        )
        return

    function = feature["function"]
    runner = feature["runner"]

    title = feature_config.get(
        "title",
        feature_name
    )

    print(f"\n⏳ {title}...")

    try:

        result = runner(
            function,
            transactions_df,
            transactions_list,
            date_str,
        )

        if result is not None:
            print_result(result)

    except Exception as e:

        logger.error(
            f"Ошибка при выполнении '{feature_name}': {e}",
            exc_info=True
        )

        print(f"Ошибка: {e}")


def get_user_date_input() -> str:
    """Запрашивает у пользователя дату или возвращает текущую."""
    while True:
        raw = input(
            "Введите дату для анализа (YYYY-MM-DD) "
            "[Enter для текущей даты]: "
        ).strip()

        if not raw:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            dt = datetime.strptime(raw, "%Y-%m-%d")
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=0)
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        except ValueError:
            print("Неверный формат даты. Пример: 2026-08-14")



def main():
    """Основная функция приложения."""

    # Настраиваем логирование ПЕРЕД всем остальным
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("Запуск приложения")

    print("=" * 60)
    print("ДОБРО ПОЖАЛОВАТЬ В БАНКОВСКУЮ АНАЛИТИКУ")
    print("=" * 60)

    # Загружаем настройки
    settings = load_user_settings()
    features_config = settings.get("features", {})

    
    try:
        transactions_df = load_transactions("data/operations.xlsx")
        transactions_list = load_transactions_excel("data/operations.xlsx")
        print(f"Загружено записей: {len(transactions_list)}\n")
        
    except Exception as e:
         logger.error( f"Не удалось загрузить транзакции: {e}", exc_info=True ) 
         print( f"Не удалось загрузить данные: {e}" )
         return

    menu_options = {}

    option_num = 1

    for feature_name, config in features_config.items():

        # Функция выключена
        if not config.get("enabled", False):
            continue

        # Функция отсутствует в Python
        if feature_name not in FEATURES:

            logger.warning(
                f"Функция '{feature_name}' "
                f"есть в JSON, но отсутствует в FEATURES."
            )

            continue

        title = config.get(
            "title",
            feature_name
        )

        menu_options[str(option_num)] = feature_name

        print(
            f"{option_num}. {title}"
        )

        option_num += 1

    # Выход
    menu_options[str(option_num)] = "exit"

    print(
        f"{option_num}. Выход"
    )

    print("-" * 60)

    # ---------------------------------------------------------
    #  Автозапуск
    # ---------------------------------------------------------

    for feature_name, config in features_config.items():

        if not config.get("enabled", False):
            continue

        if not config.get("auto_run", False):
            continue

        if feature_name not in FEATURES:
            continue

        print(
            f"\n[АВТОЗАПУСК] "
            f"{config.get('title', feature_name)}"
        )

        # Для функций с датой
        date_str = get_user_date_input()

        run_feature(
            feature_name,
            config,
            transactions_df,
            transactions_list,
            date_str,
        )

        print("-" * 60)

    # ---------------------------------------------------------
    # Основной цикл
    # ---------------------------------------------------------

    while True:

        choice = input(
            "\nВыберите действие (введите номер): "
        ).strip()

        # Неверный пункт
        if choice not in menu_options:

            print(
                "Нет такой функции. "
                "Попробуйте снова."
            )

            continue

        feature_name = menu_options[choice]

        # Выход
        if feature_name == "exit":

            print(
                "Выход из программы. "
                "До свидания!"
            )

            break

        config = features_config.get(
            feature_name,
            {}
        )

        # Получаем дату только для функций,
        # которым она действительно нужна.
        date_str = get_user_date_input()

        run_feature(
            feature_name,
            config,
            transactions_df,
            transactions_list,
            date_str,
        )

    
if __name__ == "__main__":
    main()

