"""
Модуль для загрузки и обработки данных из Excel-файла.
Отделяет бизнес-логику от источника данных.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

COL_DATE = 'Дата операции'
COL_AMOUNT = 'Сумма операции'
COL_CATEGORY = 'Категория'
COL_CARD = 'Номер карты'
COL_DESCRIPTION = 'Описание'


def load_transactions(file_path: str) -> pd.DataFrame:
    """
    Загружает транзакции из Excel-файла.
    
    :param file_path: путь к файлу operations.xlsx
    :return: DataFrame с транзакциями
    """
    try:
        df = pd.read_excel(file_path)
        logger.info(f"Загружено {len(df)} транзакций из {file_path}")
        logger.info(f"Колонки в файле: {list(df.columns)}")  # Диагностика
        
        # Приводим дату к datetime
        if COL_DATE in df.columns:
            df[COL_DATE] = pd.to_datetime(
                df[COL_DATE],
                format='%d.%m.%Y %H:%M:%S',
                errors='coerce'
            )
        else:
            logger.warning(f"Колонка '{COL_DATE}' не найдена в файле")


        # Приводим сумму к числовому типу
        if COL_AMOUNT in df.columns:
            df[COL_AMOUNT] = pd.to_numeric(df[COL_AMOUNT], errors='coerce')

        
        return df
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {file_path}: {e}")
        raise


def filter_by_date_range(
    df: pd.DataFrame,
    target_date: datetime,
    period: str = "M"
) -> pd.DataFrame:
    """
    Фильтрует транзакции по диапазону дат.
    
    :param df: DataFrame с транзакциями
    :param target_date: целевая дата
    :param period: период (W - неделя, M - месяц, Y - год, ALL - все данные) 
    :return: отфильтрованный DataFrame
    """
    if COL_DATE not in df.columns:
        logger.warning("Колонка 'Дата операции' не найдена")
        return df
    
    # Дополнительная проверка типа
    if not pd.api.types.is_datetime64_any_dtype(df[COL_DATE]):
        logger.error(
            f"Колонка '{COL_DATE}' имеет тип {df[COL_DATE].dtype}, "
            f"а не datetime. Проверьте load_transactions."
        )
        return df
    
    # Удаляем строки с невалидными датами (NaT)
    df_clean = df.dropna(subset=[COL_DATE]).copy()

    
    # Определяем начало периода
    if period == "W":
        start_date = target_date - timedelta(days=target_date.weekday())
    elif period == "M":
        start_date = target_date.replace(day=1)
    elif period == "Y":
        start_date = target_date.replace(month=1, day=1)
    elif period == "ALL":
        start_date = df_clean[COL_DATE].min()
    else:
        start_date = target_date.replace(day=1)  # По умолчанию - месяц
    
    # Фильтруем
    mask = (df_clean[COL_DATE] >= start_date) & (df_clean[COL_DATE] <= target_date)
    filtered = df_clean[mask].copy()
    
    logger.info(f"Отфильтровано {len(filtered)} транзакций за период {period}")
    return filtered


def get_card_operations(df: pd.DataFrame) -> pd.DataFrame:
    """Получает операции по картам (исключает наличные и переводы)."""
    if COL_CATEGORY not in df.columns:
        return df
    
    # Исключаем наличные и переводы
    mask = ~df[COL_CATEGORY].isin(['Наличные', 'Перевод'])
    return df[mask].copy()


def calculate_card_stats(df: pd.DataFrame) -> list[dict]:
    """
    Рассчитывает статистику по каждой карте.
    
    :return: список словарей с информацией о картах
    """
    if COL_CARD not in df.columns or COL_AMOUNT not in df.columns:
        logger.warning(f"Колонки '{COL_CARD}' или '{COL_AMOUNT}' не найдены")
        return []
    
    stats = []
    for card_number in df[COL_CARD].dropna().unique():
        card_df = df[df[COL_CARD] == card_number]
        
        # Берем последние 4 цифры
        last_digits = str(card_number)[-4:]
        
        # Сумма расходов (отрицательные значения)
        total_spent = abs(card_df[card_df[COL_AMOUNT] < 0][COL_AMOUNT].sum())
        
        # Кешбэк (1% от расходов)
        cashback = round(total_spent * 0.01, 2)
        
        stats.append({
            "last_digits": last_digits,
            "total_spent": round(total_spent, 2),
            "cashback": cashback
        })
    
    return stats


def get_top_transactions(df: pd.DataFrame, n: int = 5) -> list[dict]:
    """
    Получает топ-N транзакций по абсолютной сумме.
    
    :param df: DataFrame с транзакциями
    :param n: количество транзакций
    :return: список словарей
    """
    if COL_AMOUNT not in df.columns:
        return []
    
    # Сортируем по абсолютному значению суммы
    df_sorted = df.copy()
    df_sorted['abs_amount'] = df_sorted[COL_AMOUNT].abs()
    df_sorted = df_sorted.sort_values('abs_amount', ascending=False).head(n)
    
    transactions = []
    for _, row in df_sorted.iterrows():
        date_val = row.get(COL_DATE)
        if pd.notna(date_val):
            try:
                date_str = date_val.strftime('%d.%m.%Y')
            except AttributeError:
                date_str = str(date_val)
        else:
            date_str = ""
        
        transactions.append({
            "date": date_str,
            "amount": round(row[COL_AMOUNT], 2) if pd.notna(row[COL_AMOUNT]) else 0,
            "category": row.get(COL_CATEGORY, ''),
            "description": row.get(COL_DESCRIPTION, '')
        })

    
    return transactions


def calculate_expenses_by_category(df: pd.DataFrame) -> dict:
    """
    Рассчитывает расходы по категориям.
    
    :return: словарь с расходами и поступлениями
    """
    if COL_AMOUNT not in df.columns or COL_CATEGORY not in df.columns:
        logger.warning(f"Колонки '{COL_AMOUNT}' или '{COL_CATEGORY}' не найдены")
        return {"expenses": {}, "income": {}}
    
    # Разделяем расходы и поступления
    expenses_df = df[df[COL_AMOUNT] < 0].copy()
    income_df = df[df[COL_AMOUNT] > 0].copy()
    
    # Расходы по категориям
    expenses_by_cat = (
        expenses_df.groupby(COL_CATEGORY)[COL_AMOUNT]
        .sum()
        .abs()
        .to_dict()
    )
    
    # Поступления по категориям
    income_by_cat = (
        income_df.groupby(COL_CATEGORY)[COL_AMOUNT]
        .sum()
        .to_dict()
    )
    
    return {
        "expenses": expenses_by_cat,
        "income": income_by_cat
    }


def get_transfers_and_cash(df: pd.DataFrame) -> list[dict]:
    """Получает сумму по категориям 'Наличные' и 'Переводы'."""
    if COL_CATEGORY not in df.columns or COL_AMOUNT not in df.columns:
        return []
    
    transfers_cash = df[df[COL_CATEGORY].isin(['Наличные', 'Перевод'])]
    
    result = []
    for category in ['Наличные', 'Переводы']:
        cat_df = transfers_cash[transfers_cash[COL_CATEGORY] == category]
        if not cat_df.empty:
            amount = abs(cat_df[COL_AMOUNT].sum())
            result.append({
                "category": category,
                "amount": round(amount, 2)
            })
    
    # Сортируем по убыванию
    result.sort(key=lambda x: x['amount'], reverse=True)
    return result

