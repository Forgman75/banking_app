"""
Тесты для модуля views.py
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.views import generate_events_page, generate_home_page, get_greeting


@patch("src.views.datetime")
def test_get_greeting_morning(mock_datetime):
    mock_datetime.now.return_value.hour = 8
    assert get_greeting(datetime.now()) == "Доброе утро"


@patch("src.views.datetime")
def test_get_greeting_day(mock_datetime):
    mock_datetime.now.return_value.hour = 14
    assert get_greeting(datetime.now()) == "Добрый день"


@patch("src.views.datetime")
def test_get_greeting_evening(mock_datetime):
    mock_datetime.now.return_value.hour = 20
    assert get_greeting(datetime.now()) == "Добрый вечер"


@patch("src.views.datetime")
def test_get_greeting_night(mock_datetime):
    mock_datetime.now.return_value.hour = 2
    assert get_greeting(datetime.now()) == "Доброй ночи"


# Тесты для generate_home_page
@patch("src.views.get_stock_prices")
@patch("src.views.get_currency_rates")
@patch("src.views.load_user_settings")
@patch("src.views.filter_by_date_range")
@patch("src.views.load_transactions")
def test_generate_home_page_success(
    mock_load_tx, mock_filter, mock_settings, mock_rates, mock_stocks
):
    """Тест успешной генерации главной страницы."""
    # Настраиваем моки
    mock_df = MagicMock()
    mock_load_tx.return_value = mock_df
    mock_filter.return_value = mock_df

    mock_settings.return_value = {
        "user_currencies": ["USD"],
        "user_stocks": ["AAPL"],
    }
    mock_rates.return_value = [{"currency": "USD", "rate": 92.5}]
    mock_stocks.return_value = [{"stock": "AAPL", "price": 150.0}]

    result_str = generate_home_page("2023-10-20 14:30:00")
    result = json.loads(result_str)

    assert "greeting" in result
    assert "cards" in result
    assert "top_transactions" in result
    assert result["currency_rates"] == [{"currency": "USD", "rate": 92.5}]
    assert result["stock_prices"] == [{"stock": "AAPL", "price": 150.0}]


@patch("src.views.load_transactions")
def test_generate_home_page_error(mock_load_tx):
    """Тест обработки ошибки при генерации главной страницы."""
    mock_load_tx.side_effect = Exception("File not found")

    result_str = generate_home_page("2023-10-20 14:30:00")
    result = json.loads(result_str)

    assert "error" in result
    assert "File not found" in result["error"]


# Тесты для generate_events_page
@patch("src.views.get_stock_prices")
@patch("src.views.get_currency_rates")
@patch("src.views.load_user_settings")
@patch("src.views.filter_by_date_range")
@patch("src.views.load_transactions")
def test_generate_events_page_success(
    mock_load_tx, mock_filter, mock_settings, mock_rates, mock_stocks
):
    """Тест успешной генерации страницы событий."""
    # Создаем фиктивный DataFrame для возврата из calculate_expenses_by_category
    mock_df = MagicMock()
    mock_load_tx.return_value = mock_df
    mock_filter.return_value = mock_df

    # Патчим функцию расчета категорий, чтобы вернуть предсказуемые данные
    with patch("src.views.calculate_expenses_by_category") as mock_calc:
        mock_calc.return_value = {
            "expenses": {"Супермаркеты": 5000, "Рестораны": 2000},
            "income": {"Зарплата": 50000},
        }

        with patch("src.views.get_transfers_and_cash") as mock_transfers:
            mock_transfers.return_value = [
                {"category": "Переводы", "amount": 1000}
            ]

            mock_settings.return_value = {
                "user_currencies": [],
                "user_stocks": [],
            }
            mock_rates.return_value = []
            mock_stocks.return_value = []

            result_str = generate_events_page(
                "2023-10-20 14:30:00", period="M"
            )
            result = json.loads(result_str)

    assert result["expenses"]["total_amount"] == 7000
    assert len(result["expenses"]["main"]) == 2  # Супермаркеты и Рестораны
    assert result["income"]["total_amount"] == 50000
    assert result["expenses"]["transfers_and_cash"][0]["amount"] == 1000
