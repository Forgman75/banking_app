"""
Модуль для генерации JSON-ответов для веб-страниц.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.service_api import (
    get_currency_rates,
    get_stock_prices,
    load_user_settings
)
from src.utils import (
    calculate_card_stats,
    calculate_expenses_by_category,
    filter_by_date_range,
    get_top_transactions,
    get_transfers_and_cash,
    load_transactions
)

logger = logging.getLogger(__name__)


def get_greeting(date: datetime) -> str:
    """
    Возвращает приветствие в зависимости от времени суток.

    :param date: дата и время
    :return: строка приветствия
    """
    moscow_time = datetime.now(ZoneInfo("Europe/Moscow"))
    hour = moscow_time.hour

    if 6 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def generate_home_page(
    date_str: str,
    file_path: str = "data/operations.xlsx",
    settings_path: str = "user_settings.json",
) -> str:
    """
    Генерирует JSON-ответ для главной страницы.

    :param date_str: дата в формате "YYYY-MM-DD HH:MM:SS"
    :param file_path: путь к файлу с транзакциями
    :param settings_path: путь к файлу настроек
    :return: JSON-строка
    """
    try:
        # Парсим дату
        target_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        logger.info(f"Генерация главной страницы для даты: {target_date}")

        # Загружаем данные
        df = load_transactions(file_path)
        df_filtered = filter_by_date_range(df, target_date, period="M")

        # Загружаем настройки
        settings = load_user_settings(settings_path)

        # Формируем ответ
        response = {
            "greeting": get_greeting(target_date),
            "cards": calculate_card_stats(df_filtered),
            "top_transactions": get_top_transactions(df_filtered, n=5),
            "currency_rates": get_currency_rates(
                settings.get("user_currencies", [])
            ),
            "stock_prices": get_stock_prices(settings.get("user_stocks", [])),
        }

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка генерации главной страницы: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def generate_events_page(
    date_str: str,
    period: str = "M",
    file_path: str = "data/operations.xlsx",
    settings_path: str = "user_settings.json",
) -> str:
    """
    Генерирует JSON-ответ для страницы событий.

    :param date_str: дата в формате "YYYY-MM-DD HH:MM:SS"
    :param period: период (W, M, Y, ALL)
    :param file_path: путь к файлу с транзакциями
    :param settings_path: путь к файлу настроек
    :return: JSON-строка
    """
    try:
        # Парсим дату
        target_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        logger.info(
            f"Генерация страницы событий для даты: "
            f"{target_date}, период: {period}"
        )

        # Загружаем данные
        df = load_transactions(file_path)
        df_filtered = filter_by_date_range(df, target_date, period=period)

        # Загружаем настройки
        settings = load_user_settings(settings_path)

        # Рассчитываем расходы и поступления
        categories_data = calculate_expenses_by_category(df_filtered)

        # Расходы
        expenses_by_cat = categories_data["expenses"]
        total_expenses = sum(expenses_by_cat.values())

        # Топ-7 категорий расходов + "Остальное"
        sorted_expenses = sorted(
            expenses_by_cat.items(), key=lambda x: x[1], reverse=True
        )
        main_expenses = []

        for i, (category, amount) in enumerate(sorted_expenses[:7]):
            main_expenses.append(
                {"category": category, "amount": round(amount)}
            )

        # Остальные категории
        if len(sorted_expenses) > 7:
            other_amount = sum(amount for _, amount in sorted_expenses[7:])
            main_expenses.append(
                {"category": "Остальное", "amount": round(other_amount)}
            )

        # Переводы и наличные
        transfers_cash = get_transfers_and_cash(df_filtered)

        # Поступления
        income_by_cat = categories_data["income"]
        total_income = sum(income_by_cat.values())

        sorted_income = sorted(
            income_by_cat.items(), key=lambda x: x[1], reverse=True
        )
        main_income = [
            {"category": cat, "amount": round(amount)}
            for cat, amount in sorted_income
        ]

        # Формируем ответ
        response = {
            "expenses": {
                "total_amount": round(total_expenses),
                "main": main_expenses,
                "transfers_and_cash": transfers_cash,
            },
            "income": {
                "total_amount": round(total_income),
                "main": main_income,
            },
            "currency_rates": get_currency_rates(
                settings.get("user_currencies", [])
            ),
            "stock_prices": get_stock_prices(settings.get("user_stocks", [])),
        }

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка генерации страницы событий: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
