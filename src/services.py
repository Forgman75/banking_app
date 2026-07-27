import json
import re
import math
from functools import reduce
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict


def cashback_categories(data: List[Dict[str, Any]], year: int, month: int) -> str:
    """
    Анализ выгодных категорий повышенного кешбэка.
    
    :param data: список транзакций с полями "Дата операции", "Категория", "Кешбэк"
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
        cashback = t.get("Кешбэк", 0)
        acc[category] = acc.get(category, 0) + cashback
        return acc

    category_cashback = reduce(accumulate, filtered, {})

    # Отбрасываем категории с нулевым кешбэком и округляем
    result = {k: round(v) for k, v in category_cashback.items() if v > 0}

    return json.dumps(result, ensure_ascii=False)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Расчет суммы, отложенной в Инвесткопилку за счет округления трат.
    
    :param month: месяц в формате 'YYYY-MM'
    :param transactions: список транзакций с полями "Дата операции", "Сумма операции"
    :param limit: шаг округления (10, 50 или 100)
    :return: сумма, которую удалось бы отложить
    
    Пример: шаг 50 ₽, покупка 1712 ₽ → округление до 1750 ₽ → в копилку 38 ₽
    """
    if limit <= 0:
        return 0.0

    def round_up(amount: float) -> float:
        """Разница между суммой, округленной вверх до кратного limit, и исходной суммой."""
        if amount <= 0:
            return 0.0
        return math.ceil(amount / limit) * limit - amount

    # Фильтрация транзакций по месяцу
    filtered = list(filter(
        lambda t: t.get("Дата операции", "").startswith(month),
        transactions
    ))

    # Извлекаем суммы, вычисляем разницу округления и суммируем через reduce
    total = reduce(
        lambda acc, amount: acc + round_up(abs(amount)),
        map(lambda t: t.get("Сумма операции", 0), filtered),
        0.0
    )

    return total


def simple_search(query: str, transactions: List[Dict[str, Any]]) -> str:
    """
    Простой поиск транзакций по вхождению подстроки в описание или категорию.
    
    :param query: строка для поиска (регистронезависимо)
    :param transactions: список транзакций
    :return: JSON-строка со списком найденных транзакций
    """
    query_lower = query.lower()

    def matches(t: Dict[str, Any]) -> bool:
        description = t.get("Описание", "").lower()
        category = t.get("Категория", "").lower()
        return query_lower in description or query_lower in category

    filtered = list(filter(matches, transactions))
    return json.dumps(filtered, ensure_ascii=False)


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
    phone_pattern = re.compile(r'\+7\s?\d{3}\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}')

    filtered = list(filter(
        lambda t: bool(phone_pattern.search(t.get("Описание", ""))),
        transactions
    ))
    return json.dumps(filtered, ensure_ascii=False)


