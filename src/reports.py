"""
Модуль reports.py
Формирование аналитических отчётов по транзакциям.
"""

import functools
import logging
from datetime import datetime
from typing import Optional, Callable

import pandas as pd

logger = logging.getLogger(__name__)


#  ДЕКОРАТОР: сохранение результата отчёта в файл
def save_report(
    func: Optional[Callable] = None, *, filename: Optional[str] = None
):
    """
    Декоратор для функций-отчётов. Сохраняет возвращаемый DataFrame в файл.

    Использование:
    @save_report                            # имя файла генерируется автоматически
    @save_report(filename="my_report.csv")  # указанное имя файла
    @save_report(filename="my_report.xlsx") # формат определяется по расширению
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)

            # Формируем имя файла
            if filename:
                fname = filename
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                fname = f"report_{f.__name__}_{timestamp}.csv"

            # Сохраняем в зависимости от расширения
            try:
                if fname.lower().endswith(".xlsx"):
                    result.to_excel(fname, index=False)
                else:
                    result.to_csv(fname, index=False, encoding="utf-8-sig")
                logger.info(f"Отчёт '{f.__name__}' сохранён в файл: {fname}")
            except Exception as e:
                logger.error(f"Ошибка при сохранении отчёта в {fname}: {e}")

            return result

        return wrapper

    # Поддержка вызова как @save_report и @save_report(filename="...")
    if func is None:
        return decorator
    return decorator(func)


#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def _prepare_dataframe(transactions: pd.DataFrame, date: Optional[str] = None):
    """
    Фильтрует транзакции за последние 3 месяца от указанной даты.
    Возвращает: (отфильтрованный df с колонкой 'date', ref_date, start_date)
    """
    if transactions is None or transactions.empty:
        return pd.DataFrame(), pd.Timestamp.now(), pd.Timestamp.now()

    df = transactions.copy()

    # Парсим опорную дату
    ref_date = pd.to_datetime(date) if date else pd.Timestamp.now()
    start_date = ref_date - pd.DateOffset(months=3)

    # Приводим дату операции к datetime
    df["date"] = pd.to_datetime(df["Дата операции"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Фильтр по периоду [start_date; ref_date]
    mask = (df["date"] >= start_date) & (df["date"] <= ref_date)
    filtered = df.loc[mask].copy()

    return filtered, ref_date, start_date


def _filter_spending(df: pd.DataFrame) -> pd.DataFrame:
    """Оставляет только траты (отрицательные суммы) и добавляет
    колонку amount (модуль)."""
    df = df[df["Сумма операции"] < 0].copy()
    df["amount"] = df["Сумма операции"].abs()
    return df


#  ОТЧЁТ 1: Траты по категории
@save_report
def spending_by_category(
    transactions: pd.DataFrame, category: str, date: Optional[str] = None
) -> pd.DataFrame:
    """
    Сумма трат по заданной категории за последние 3 месяца от указанной даты.

    :param transactions: DataFrame с транзакциями
    :param category: название категории
    :param date: опорная дата (строка, например '2024-05-15').
    По умолчанию — сегодня.
    :return: DataFrame с колонками ['Категория', 'Период', 'Сумма трат']
    """
    filtered, ref_date, start_date = _prepare_dataframe(transactions, date)
    if filtered.empty:
        return pd.DataFrame(
            {
                "Категория": [category],
                "Период": ["нет данных"],
                "Сумма трат": [0.0],
            }
        )

    spending = _filter_spending(filtered)
    cat_spending = spending[spending["Категория"] == category]
    total = round(cat_spending["amount"].sum(), 2)

    period_str = (
        f"{start_date.strftime('%Y-%m-%d')} — {ref_date.strftime('%Y-%m-%d')}"
    )

    return pd.DataFrame(
        {
            "Категория": [category],
            "Период": [period_str],
            "Сумма трат": [total],
        }
    )


#  ОТЧЁТ 2: Средние траты по дням недели
@save_report
def spending_by_weekday(
    transactions: pd.DataFrame, date: Optional[str] = None
) -> pd.DataFrame:
    """
    Средние траты в каждый из дней недели за последние 3 месяца.

    Среднее считается как: (сумма трат в этот день недели) /
    (количество таких дней в периоде).

    :return: DataFrame с колонками ['День недели', 'Средние траты']
    """
    filtered, ref_date, start_date = _prepare_dataframe(transactions, date)

    weekday_names = [
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
        "Воскресенье",
    ]

    if filtered.empty:
        return pd.DataFrame(
            {
                "День недели": weekday_names,
                "Средние траты": [0.0] * 7,
            }
        )

    spending = _filter_spending(filtered)
    spending["weekday"] = spending["date"].dt.weekday

    # Сумма трат по дням недели
    sums = spending.groupby("weekday")["amount"].sum()

    # Количество каждого дня недели в периоде
    all_days = pd.date_range(start=start_date, end=ref_date, freq="D")
    weekday_counts = all_days.weekday.value_counts()

    # Среднее = сумма / количество дней
    averages = (
        (sums / weekday_counts).reindex(range(7), fill_value=0.0).round(2)
    )

    return pd.DataFrame(
        {
            "День недели": weekday_names,
            "Средние траты": averages.values,
        }
    )
