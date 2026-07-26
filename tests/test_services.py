import json
from unittest.mock import MagicMock, patch

import pytest

from src.services import (
    get_currency_rates,
    get_stock_prices,
    load_user_settings
)


def test_load_user_settings_success(tmp_path):
    """Тест успешной загрузки настроек."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        '{"user_currencies": ["USD"], "user_stocks": ["AAPL"]}'
    )

    result = load_user_settings(str(settings_file))

    assert result == {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}


def test_load_user_settings_fallback(tmp_path):
    """Тест возврата значений по умолчанию при ошибке."""
    result = load_user_settings(str(tmp_path / "non_existent.json"))
    assert result == {"user_currencies": [], "user_stocks": []}


# ─────────────────────────────────────────────
# Тесты для get_currency_rates
# ─────────────────────────────────────────────
@patch("src.services.requests.get")
def test_get_currency_rates_success(mock_get):
    """Тест успешного получения курсов валют."""
    # Настраиваем мок ответа API
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": "success",
        "conversion_rates": {"RUB": 92.50, "USD": 1.0, "EUR": 0.92},
    }
    mock_get.return_value = mock_response

    # Патчим ключ, чтобы тест не зависел от реального .env
    with patch("src.services.EXCHANGERATE_API_KEY", "test_key"):
        rates = get_currency_rates(["USD", "EUR"])

    assert len(rates) == 2
    assert rates[0] == {"currency": "USD", "rate": 92.50}
    # 92.50 / 0.92 ≈ 100.54
    assert rates[1] == {"currency": "EUR", "rate": 100.54}


@patch("src.services.requests.get")
def test_get_currency_rates_api_error(mock_get):
    """Тест обработки ошибки от API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": "error",
        "error-type": "invalid-key",
    }
    mock_get.return_value = mock_response

    with patch("src.services.EXCHANGERATE_API_KEY", "test_key"):
        rates = get_currency_rates(["USD"])

    assert rates == []


@patch("src.services.requests.get")
def test_get_currency_rates_connection_error(mock_get):
    """Тест обработки сетевой ошибки (DNS, таймаут)."""
    import requests

    mock_get.side_effect = requests.exceptions.ConnectionError("DNS failed")

    with patch("src.services.EXCHANGERATE_API_KEY", "test_key"):
        rates = get_currency_rates(["USD"])

    assert rates == []


# ─────────────────────────────────────────────
# Тесты для get_stock_prices
# ─────────────────────────────────────────────
@patch("src.services.requests.get")
def test_get_stock_prices_success(mock_get):
    """Тест успешного получения цен акций."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "chart": {"result": [{"meta": {"regularMarketPrice": 150.125}}]}
    }
    mock_get.return_value = mock_response

    prices = get_stock_prices(["AAPL"])

    assert len(prices) == 1
    assert prices[0] == {"stock": "AAPL", "price": 150.12}


@patch("src.services.requests.get")
def test_get_stock_prices_missing_data(mock_get):
    """Тест обработки ответа API без нужных данных."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"chart": {"result": []}}
    mock_get.return_value = mock_response

    prices = get_stock_prices(["AAPL"])
    assert prices == []
