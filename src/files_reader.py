import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

COL_DATE = "Дата операции"
COL_DATE_PAY = "Дата платежа"
COL_AMOUNT = "Сумма операции"
COL_AMOUNT_PAY = "Сумма платежа"
COL_CATEGORY = "Категория"
COL_DESCRIPTION = "Описание"
COL_BONUS = "Бонусы (включая кэшбэк)"
COL_STATUS = "Статус"


def load_transactions(file_path: str) -> pd.DataFrame:
    """
    Загружает транзакции из Excel-файла.

    :param file_path: путь к файлу operations.xlsx
    :return: DataFrame с транзакциями
    """
    try:
        df = pd.read_excel(file_path)
        logger.info(f"Загружено {len(df)} транзакций из {file_path}")
        
        # Приводим дату к datetime
        if COL_DATE in df.columns:
            df[COL_DATE] = pd.to_datetime(
                df[COL_DATE], format="%d.%m.%Y %H:%M:%S", errors="coerce"
            )
        else:
            logger.warning(f"Колонка '{COL_DATE}' не найдена в файле")

        # Приводим сумму к числовому типу
        if COL_AMOUNT in df.columns:
            df[COL_AMOUNT] = pd.to_numeric(df[COL_AMOUNT], errors="coerce")

        return df
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {file_path}: {e}")
        raise


def load_transactions_excel(file_path: str) -> list[dict[str, Any]]:
    """
    Считывает финансовые операции из Excel-файла.
    Предполагает, что колонки называются точно:
    "Дата операции", "Сумма операции", "Категория", "Кешбэк", "Описание".
    Заменяет пропуски (None/NaN) на "" для строк и 0.0 для чисел.
    """
    logger.debug(f"Начало чтения Excel-файла: {file_path}")

    required_cols = [
        "Дата операции",
        "Дата платежа",
        "Статус",
        "Сумма операции",
        "Валюта операции",
        "Сумма платежа",
        "Категория",
        "Описание",
        "Бонусы (включая кэшбэк)",
    ]

    try:
        df = pd.read_excel(file_path)

        if df.empty:
            logger.info("Excel-файл пуст или содержит только заголовки")
            return []

        # Гарантируем наличие всех нужных колонок
        for col in required_cols:
            if col not in df.columns:
                df[col] = np.nan

        # Оставляем только нужные колонки для чистоты данных
        df = df[required_cols]

        # Приводим типы и заменяем NaN/None на безопасные значения
        # Числа -> 0.0 (чтобы не ломать математику в services.py)
        df[COL_AMOUNT] = pd.to_numeric(
            df[COL_AMOUNT], errors="coerce"
        ).fillna(0.0)
        df[COL_AMOUNT_PAY] = pd.to_numeric(
            df[COL_AMOUNT_PAY], errors="coerce"
        ).fillna(0.0)
        df[COL_BONUS] = pd.to_numeric(
            df[COL_BONUS], errors="coerce"
        ).fillna(0.0)

        # Строки -> ""
        df[COL_CATEGORY] = df[COL_CATEGORY].fillna("").astype(str)
        df[COL_DESCRIPTION] = df[COL_DESCRIPTION].fillna("").astype(str)
        df[COL_STATUS] = df[COL_STATUS].fillna("").astype(str)

        # Даты -> строка формата YYYY-MM-DD (ошибки парсинга станут "")
        df[COL_DATE] = (
            pd.to_datetime(
                df[COL_DATE],
                format="%d.%m.%Y %H:%M:%S",
                errors="coerce",
            )
            .dt.strftime("%Y-%m-%d")
            .fillna("")
        )

        df[COL_DATE_PAY] = (
            pd.to_datetime(
                df[COL_DATE_PAY],
                format="%d.%m.%Y",
                errors="coerce",
            )
            .dt.strftime("%Y-%m-%d")
            .fillna("")
        )

        logger.info(f"Успешно считано и нормализовано {len(df)} транзакций")

        # Преобразуем в список словарей
        records = df.to_dict(orient="records")

        # Заменяем любые остаточные None на "" (кроме чисел, они уже 0.0)
        return [
            {k: ("" if v is None or pd.isna(v) else v) for k, v in row.items()}
            for row in records
        ]

    except FileNotFoundError:
        logger.error(f"Excel-файл не найден: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при чтении Excel: {e}")
        return []
