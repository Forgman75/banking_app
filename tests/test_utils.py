"""
Тесты для модуля utils.py
"""

from datetime import datetime

import pandas as pd
import pytest

from src.utils import (
    calculate_card_stats,
    calculate_expenses_by_category,
    filter_by_date_range,
    get_top_transactions,
    get_transfers_and_cash
)


@pytest.fixture
def sample_df():
    """Создает тестовый DataFrame."""
    data = {
        "Дата операции": [
            datetime(2023, 10, 15, 10, 30),
            datetime(2023, 10, 20, 14, 20),
            datetime(2023, 10, 25, 9, 15),
            datetime(2023, 11, 5, 16, 45),
        ],
        "Номер карты": ["*5678", "*4321", "*5678", "*4321"],
        "Категория": ["Супермаркеты", "Рестораны", "Переводы", "Супермаркеты"],
        "Сумма операции": [-1500.50, -800.00, 5000.00, -2000.00],
        "Описание": ["Пятёрочка", "Макдоналдс", "Перевод другу", "Магнит"],
    }
    return pd.DataFrame(data)


def test_filter_by_date_range_month(sample_df):
    """Тест фильтрации по месяцу (M)."""
    target_date = datetime(2023, 10, 31, 23, 59)
    filtered = filter_by_date_range(sample_df, target_date, period="M")

    assert len(filtered) == 3  # Только октябрьские транзакции
    assert all(
        row["Дата операции"].month == 10 for _, row in filtered.iterrows()
    )


def test_filter_by_date_range_year(sample_df):
    """Тест фильтрации по году (Y)."""
    target_date = datetime(2023, 12, 31, 23, 59)
    filtered = filter_by_date_range(sample_df, target_date, period="Y")

    assert len(filtered) == 4  # Все транзакции за 2023 год


def test_calculate_card_stats(sample_df):
    """Тест расчета статистики по картам."""
    stats = calculate_card_stats(sample_df)

    assert len(stats) == 2

    # Карта 1: только расход -1500.50 (транзакция +5000.00 — поступление, не учитывается)
    card1 = next(s for s in stats if s["last_digits"] == "5678")
    assert card1["total_spent"] == 1500.50
    assert card1["cashback"] == 15.0  # 1% от 1500.50

    # Карта 2: два расхода -800.00 + -2000.00 = -2800.00
    card2 = next(s for s in stats if s["last_digits"] == "4321")
    assert card2["total_spent"] == 2800.00
    assert card2["cashback"] == 28.00  # 1% от 2800.00


def test_get_top_transactions(sample_df):
    """Тест получения топ-N транзакций."""
    top = get_top_transactions(sample_df, n=2)

    assert len(top) == 2
    # Первая должна быть "Перевод другу" (5000.00), вторая "Супермаркеты" (-2000.00)
    assert top[0]["amount"] == 5000.00
    assert top[0]["category"] == "Переводы"
    assert top[1]["amount"] == -2000.00
    assert top[1]["date"] == "05.11.2023"


def test_calculate_expenses_by_category(sample_df):
    """Тест разделения расходов и доходов."""
    result = calculate_expenses_by_category(sample_df)

    assert "expenses" in result
    assert "income" in result
    assert result["expenses"]["Супермаркеты"] == 3500.50  # 1500.50 + 2000.00
    assert result["income"]["Переводы"] == 5000.00


def test_get_transfers_and_cash(sample_df):
    """Тест фильтрации переводов и наличных."""
    result = get_transfers_and_cash(sample_df)

    assert len(result) == 1  # Только "Переводы" есть в данных
    assert result[0]["category"] == "Переводы"
    assert result[0]["amount"] == 5000.00
