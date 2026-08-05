import os
import glob
import pandas as pd
import pytest

from src.reports import (
    save_report,
    spending_by_category,
    spending_by_weekday,
)


#  ФИКСТУРЫ
@pytest.fixture
def sample_df():
    """DataFrame с транзакциями за март-апрель-май 2024."""
    data = {
        "Дата операции": [
            # Март 2024
            "2024-03-04",  # Пн (рабочий)
            "2024-03-09",  # Сб (выходной)
            "2024-03-15",  # Пт (рабочий)
            # Апрель 2024
            "2024-04-01",  # Пн (рабочий)
            "2024-04-06",  # Сб (выходной)
            "2024-04-12",  # Пт (рабочий)
            # Май 2024
            "2024-05-03",  # Пт (рабочий)
            "2024-05-11",  # Сб (выходной)
            # За пределами 3-месячного окна от 2024-05-15
            "2024-01-10",
            # Положительная сумма (не трата) — должна игнорироваться
            "2024-05-10",
        ],
        "Сумма операции": [
            -1000,
            -2000,
            -1500,
            -1200,
            -2500,
            -1800,
            -1300,
            -2200,
            -999,
            500,
        ],
        "Категория": [
            "Супермаркеты",
            "Кафе",
            "Супермаркеты",
            "Кафе",
            "Супермаркеты",
            "Кафе",
            "Супермаркеты",
            "Кафе",
            "Такси",
            "Кэшбэк",
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture(autouse=True)
def cleanup_reports():
    """Удаляет все сгенерированные файлы отчётов после каждого теста."""
    yield
    for pattern in ("report_*.csv", "report_*.xlsx", "custom_*.csv"):
        for f in glob.glob(pattern):
            try:
                os.remove(f)
            except OSError:
                pass


#  ТЕСТЫ ДЕКОРАТОРА


def test_default_filename():
    """Без параметра создаёт файл с автоименем."""

    @save_report
    def dummy(df):
        return df

    dummy(pd.DataFrame({"a": [1]}))
    files = glob.glob("report_dummy_*.csv")
    assert len(files) == 1


def test_custom_filename_csv():
    """С параметром создаёт файл с заданным именем (CSV)."""

    @save_report(filename="custom_name.csv")
    def dummy(df):
        return df

    dummy(pd.DataFrame({"a": [1]}))
    assert os.path.exists("custom_name.csv")


def test_custom_filename_xlsx():
    """С параметром .xlsx создаёт Excel-файл."""

    @save_report(filename="custom_name.xlsx")
    def dummy(df):
        return df

    dummy(pd.DataFrame({"a": [1]}))
    assert os.path.exists("custom_name.xlsx")


def test_returns_original_dataframe():
    """Декоратор возвращает тот же DataFrame, что и функция."""

    @save_report(filename="custom_ret.csv")
    def dummy(df):
        return df

    original = pd.DataFrame({"a": [1, 2, 3]})
    result = dummy(original)
    pd.testing.assert_frame_equal(result, original)


#  ТЕСТЫ: spending_by_category


def test_category_total(sample_df):
    """Сумма трат по категории 'Супермаркеты' за 3 месяца до 2024-05-15."""
    result = spending_by_category(sample_df, "Супермаркеты", "2024-05-15")
    # В окне: -1000, -1500, -2500, -1300 → сумма 6300
    assert result.iloc[0]["Сумма трат"] == 6300.0
    assert result.iloc[0]["Категория"] == "Супермаркеты"


def test_missing_category(sample_df):
    """Несуществующая категория → сумма 0."""
    result = spending_by_category(sample_df, "Несуществующая", "2024-05-15")
    assert result.iloc[0]["Сумма трат"] == 0.0


def test_default_date_is_now(sample_df):
    """Без даты используется текущая — все транзакции старые, результат 0."""
    result = spending_by_category(sample_df, "Супермаркеты")
    assert result.iloc[0]["Сумма трат"] == 0.0


def test_empty_dataframe():
    """Пустой DataFrame → сумма 0."""
    result = spending_by_category(pd.DataFrame(), "Супермаркеты", "2024-05-15")
    assert result.iloc[0]["Сумма трат"] == 0.0


def test_positive_amounts_ignored(sample_df):
    """Положительные суммы (кэшбэк) не учитываются."""
    result = spending_by_category(sample_df, "Кэшбэк", "2024-05-15")
    assert result.iloc[0]["Сумма трат"] == 0.0


#  ТЕСТЫ: spending_by_weekday


def test_returns_seven_rows(sample_df):
    """Всегда возвращается 7 строк (по числу дней недели)."""
    result = spending_by_weekday(sample_df, "2024-05-15")
    assert len(result) == 7
    assert list(result.columns) == ["День недели", "Средние траты"]


def test_weekday_names(sample_df):
    """Названия дней недели в правильном порядке."""
    result = spending_by_weekday(sample_df, "2024-05-15")
    expected = [
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
        "Воскресенье",
    ]
    assert list(result["День недели"]) == expected


def test_saturday_average(sample_df):
    """Средние траты по субботам."""
    result = spending_by_weekday(sample_df, "2024-05-15")
    saturday_row = result[result["День недели"] == "Суббота"]
    # В окне 3 субботы: 2024-03-09, 2024-04-06, 2024-05-11 → суммы 2000+2500+2200=6700
    # Количество суббот в периоде 2024-02-15..2024-05-15: ~13
    assert saturday_row.iloc[0]["Средние траты"] > 0


def test_empty_dataframe():
    """Пустой DataFrame → все нули."""
    result = spending_by_weekday(pd.DataFrame(), "2024-05-15")
    assert (result["Средние траты"] == 0.0).all()
