import json
import logging
import math
import re
from datetime import datetime
from functools import reduce
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def cashback_categories(
    data: List[Dict[str, Any]], year: int, month: int
) -> str:
    """
    Анализ выгодных категорий повышенного кешбэка.

    :param data: список транзакций с полями "Дата операции", "Категория",
    "Бонусы (включая кэшбэк)"
    :param year: год для анализа
    :param month: месяц для анализа
    :return: JSON-строка вида {"Категория": сумма_кешбэка}
    """

    def parse_date(date_str: str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def get_year_month(t: Dict[str, Any]):
        d = parse_date(t.get("Дата операции", ""))
        return (d.year, d.month) if d else (None, None)

    # Фильтрация транзакций по году и месяцу
    filtered = list(filter(lambda t: get_year_month(t) == (year, month), data))

    # Группировка по категории и суммирование кешбэка через reduce
    def accumulate(acc: dict, t: Dict[str, Any]) -> dict:
        category = t.get("Категория", "Без категории")
        cashback = t.get("Бонусы (включая кэшбэк)", 0)
        acc[category] = acc.get(category, 0) + cashback
        return acc

    category_cashback = reduce(accumulate, filtered, {})

    # Отбрасываем категории с нулевым кешбэком и округляем
    result = {k: round(v) for k, v in category_cashback.items() if v > 0}

    return json.dumps(result, ensure_ascii=False)


def investment_bank(
    month: str, transactions: List[Dict[str, Any]], limit: int
) -> float:
    """
    Расчет суммы, отложенной в Инвесткопилку за счет округления трат.

    :param month: месяц в формате 'YYYY-MM'
    :param transactions: список транзакций с полями "Дата операции",
    "Сумма платежа"
    :param limit: шаг округления (10, 50 или 100)
    :return: сумма, которую удалось бы отложить

    Пример: шаг 50 ₽, покупка 1712 ₽ → округление до 1750 ₽ → в копилку 38 ₽
    """
    if limit <= 0:
        return 0.0

    def round_up(amount: float) -> float:
        """Разница между суммой, округленной вверх до кратного limit,
        и исходной суммой."""
        if amount >= 0:
            return 0.0
        abs_amount = abs(amount)
        return math.ceil(abs_amount / limit) * limit - abs_amount

    def compare_dates(target_month: str, date_trans: str) -> bool:
        if not date_trans or len(date_trans) < 7:
            return False
        return date_trans[:7] == target_month[:7]

    # Фильтрация транзакций по месяцу
    filtered = list(
        filter(
            lambda t: (
                compare_dates(month, str(t.get("Дата операции", "")))
                and str(t.get("Статус", "")) == "OK"
            ),
            transactions,
        )
    )

    # Извлекаем суммы, вычисляем разницу округления и суммируем через reduce
    total = reduce(
        lambda acc, amount: acc + round_up(amount),
        map(lambda t: t.get("Сумма платежа", 0), filtered),
        0.0,
    )

    return round(total, 2)


def simple_search(query: str, transactions: List[Dict[str, Any]]) -> str:
    """
    Простой поиск транзакций по вхождению подстроки в описание или категорию.

    :param query: строка для поиска (регистронезависимо)
    :param transactions: список транзакций
    :return: JSON-строка со списком найденных транзакций
    """
    query_lower = query.lower()

    def matches(t: Dict[str, Any]) -> bool:
        description = str(t.get("Описание", "")).lower()
        category = str(t.get("Категория", "")).lower()
        return query_lower in description or query_lower in category

    filtered = list(filter(matches, transactions))
    return json.dumps(filtered, ensure_ascii=False, default=str)


def phone_search(transactions: List[Dict[str, Any]]) -> str:
    """
    Поиск транзакций, в описании которых встречаются мобильные номера.

    Пример описаний:
        "Я МТС +7 921 11-22-33"
        "Тинькофф Мобайл +7 995 555-55-55"
        "МТС Mobile +7 981 333-44-55"

    :param transactions: список транзакций
    :return: JSON-строка со списком найденных транзакций
    """
    phone_pattern = re.compile(
        r"\+7[\s\-]?\d{3}[\s\-]?\d{2,3}[\s\-]?\d{2}[\s\-]?\d{2}"
    )

    filtered = list(
        filter(
            lambda t: bool(phone_pattern.search(str(t.get("Описание", "")))),
            transactions,
        )
    )
    return json.dumps(filtered, ensure_ascii=False, default=str)
