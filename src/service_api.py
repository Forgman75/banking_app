"""
Модуль для получения данных из внешних API (валюты, акции).
"""

import json
import logging
import os

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "..", ".env")
load_dotenv(file_path)

# API ключи из .env
EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY", "")


def load_user_settings(settings_path: str = "user_settings.json") -> dict:
    """
    Загружает пользовательские настройки.

    :param settings_path: путь к файлу настроек
    :return: словарь с настройками
    """
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        logger.debug(f"Загружены настройки из {settings_path}")
        return settings
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек: {e}")
        return {"user_currencies": [], "user_stocks": []}


def get_currency_rates(currencies: list[str]) -> list[dict]:
    """
    Получает курсы валют через API.

    :param currencies: список кодов валют (USD, EUR, etc.)
    :return: список словарей с курсами
    """
    if not currencies:
        return []

    rates = []

    if not EXCHANGERATE_API_KEY:
        logger.error("EXCHANGERATE_API_KEY не найден в переменных окружения")

    try:
        # Используем exchangerate-api.com
        url = (
            f"https://v6.exchangerate-api.com/v6/"
            f"{EXCHANGERATE_API_KEY}/latest/USD"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data.get("result") == "success":
            conversion_rates = data.get("conversion_rates", {})
            # Курс RUB относительно USD
            rub_per_usd = conversion_rates.get("RUB", 0)
            if rub_per_usd == 0:
                logger.error("Не удалось получить курс RUB от API")

            for currency in currencies:
                if currency == "USD":
                    # 1 USD = rub_per_usd RUB
                    rate = rub_per_usd
                elif currency == "RUB":
                    rate = 1.0
                else:
                    # Курс валюты относительно USD
                    currency_per_usd = conversion_rates.get(currency, 0)
                    if currency_per_usd > 0:
                        # Сколько RUB за 1 единицу валюты
                        rate = rub_per_usd / currency_per_usd
                    else:
                        logger.warning(
                            f"Не удалось получить курс для {currency}"
                        )

                rates.append({"currency": currency, "rate": round(rate, 2)})
        else:
            error_type = data.get("error-type", "unknown")
            logger.warning(f"API вернул ошибку: {error_type}")

    except requests.exceptions.ConnectionError as e:
        logger.error(
            f"Ошибка соединения с API валют (возможно, DNS-ошибка): {e}"
        )
    except requests.exceptions.Timeout as e:
        logger.error(f"Таймаут при обращении к API валют: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к API валют: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении курсов: {e}")

    return rates


def get_stock_prices(stocks: list[str]) -> list[dict]:
    """
    Получает цены акций через API.

    :param stocks: список тикеров акций (AAPL, AMZN, etc.)
    :return: список словарей с ценами
    """
    if not stocks:
        return []

    prices = []

    try:
        # Используем Yahoo Finance API (бесплатный)
        for stock in stocks:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()

            data = response.json()
            if "chart" in data and "result" in data["chart"]:
                result = data["chart"]["result"][0]
                if "meta" in result and "regularMarketPrice" in result["meta"]:
                    price = result["meta"]["regularMarketPrice"]
                    prices.append({"stock": stock, "price": round(price, 2)})
            else:
                logger.warning(f"Не удалось получить цену для {stock}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к API акций: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении цен акций: {e}")

    return prices
