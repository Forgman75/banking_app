import json

import pytest

from src.services import (
    cashback_categories,
    investment_bank,
    phone_search,
    simple_search,
)


@pytest.fixture
def sample_transactions():
    """Универсальный набор транзакций для большинства тестов."""
    return [
        {
            "Дата операции": "2024-02-15",
            "Статус": "OK",
            "Сумма операции": -1250.0,
            "Сумма платежа": -1250.0,
            "Категория": "Супермаркеты",
            "Описание": "Пятерочка на Ленина",
            "Бонусы (включая кэшбэк)": 50.5,
        },
        {
            "Дата операции": "2024-02-16",
            "Статус": "OK",
            "Сумма операции": -1712.0,
            "Сумма платежа": -1712.0,
            "Категория": "Связь",
            "Описание": "МТС +7 921 11-22-33",
            "Бонусы (включая кэшбэк)": 0.0,
        },
        {
            "Дата операции": "2024-02-17",
            "Статус": "OK",
            "Сумма операции": -850.0,
            "Сумма платежа": -850.0,
            "Категория": "Кафе и рестораны",
            "Описание": "Кофемания",
            "Бонусы (включая кэшбэк)": 150.0,
        },
        {
            "Дата операции": "2024-02-18",
            "Статус": "CANCELLED",
            "Сумма операции": -500.0,
            "Сумма платежа": -500.0,
            "Категория": "Супермаркеты",
            "Описание": "Магнит",
            "Бонусы (включая кэшбэк)": 25.0,
        },
        {
            "Дата операции": "2024-03-01",
            "Статус": "OK",
            "Сумма операции": -300.0,
            "Сумма платежа": -300.0,
            "Категория": "Такси",
            "Описание": "Яндекс Go",
            "Бонусы (включая кэшбэк)": 30.0,
        },
    ]


def test_normal_filtering_and_grouping(sample_transactions):
    """Кешбэк за февраль: только OK-транзакции февраля,
    сгруппированные по категории."""
    result = json.loads(cashback_categories(sample_transactions, 2024, 2))

    # Супермаркеты: 50.5
    # Кафе: 150.0
    # Связь: 0.0 → отброшена
    assert result["Кафе и рестораны"] == 150
    assert result["Супермаркеты"] == 76  # 50.5 + 25.0 = 75.5 → round = 76


def test_no_transactions_for_period(sample_transactions):
    """За январь 2024 транзакций нет → пустой JSON."""
    result = json.loads(cashback_categories(sample_transactions, 2024, 1))
    assert result == {}


def test_zero_cashback_excluded():
    """Категории с нулевым кешбэком не попадают в результат."""
    data = [
        {
            "Дата операции": "2024-05-10",
            "Категория": "АЗС",
            "Бонусы (включая кэшбэк)": 0.0,
        }
    ]
    result = json.loads(cashback_categories(data, 2024, 5))
    assert result == {}


def test_negative_cashback_excluded():
    """Отрицательный кешбэк (списание бонусов) тоже отбрасывается."""
    data = [
        {
            "Дата операции": "2024-05-10",
            "Категория": "АЗС",
            "Бонусы (включая кэшбэк)": -10.0,
        }
    ]
    result = json.loads(cashback_categories(data, 2024, 5))
    assert result == {}


def test_invalid_date_skipped():
    """Транзакция с некорректной датой не вызывает падение."""
    data = [
        {
            "Дата операции": "не-дата",
            "Категория": "Продукты",
            "Бонусы (включая кэшбэк)": 100.0,
        },
        {
            "Дата операции": "2024-06-01",
            "Категория": "Продукты",
            "Бонусы (включая кэшбэк)": 200.0,
        },
    ]
    result = json.loads(cashback_categories(data, 2024, 6))
    assert result == {"Продукты": 200}


def test_empty_data():
    """Пустой список → пустой JSON."""
    result = json.loads(cashback_categories([], 2024, 1))
    assert result == {}


def test_missing_fields_use_defaults():
    """Отсутствующие поля подставляются значениями по умолчанию."""
    data = [{"Дата операции": "2024-07-01"}]  # нет Категории и Бонусов
    result = json.loads(cashback_categories(data, 2024, 7))
    # Бонусы = 0 → категория отброшена
    assert result == {}


def test_basic_rounding(sample_transactions):
    """Шаг 50, трата 1712 → округление до 1750 → в копилку 38."""
    result = investment_bank("2024-02", sample_transactions, 50)
    # Транзакции за февраль: -1250, -1712, -850, -500
    # Со статусом OK: -1250, -1712, -850
    # round_up(-1250, 50) = ceil(1250/50)*50 - 1250 = 1250 - 1250 = 0
    # round_up(-1712, 50) = ceil(1712/50)*50 - 1712 = 1750 - 1712 = 38
    # round_up(-850, 50)  = ceil(850/50)*50 - 850 = 850 - 850 = 0
    assert result == 38.0


def test_step_100(sample_transactions):
    """Шаг 100, трата 1712 → 1800 → 88."""
    result = investment_bank("2024-02", sample_transactions, 100)
    # round_up(-1250, 100) = 1300 - 1250 = 50
    # round_up(-1712, 100) = 1800 - 1712 = 88
    # round_up(-850, 100)  = 900 - 850 = 50
    assert result == 50.0 + 88.0 + 50.0


def test_exact_multiple_gives_zero():
    """Сумма, уже кратная шагу, даёт 0."""
    data = [
        {
            "Дата операции": "2024-01-10",
            "Статус": "OK",
            "Сумма платежа": -1000.0,
        }
    ]
    result = investment_bank("2024-01", data, 50)
    assert result == 0.0


def test_positive_amount_gives_zero():
    """Положительная сумма (возврат/пополнение) → 0."""
    data = [
        {
            "Дата операции": "2024-01-10",
            "Статус": "OK",
            "Сумма платежа": 500.0,
        }
    ]
    result = investment_bank("2024-01", data, 50)
    assert result == 0.0


def test_cancelled_status_ignored():
    """Транзакция со статусом != 'OK' не учитывается."""
    data = [
        {
            "Дата операции": "2024-01-10",
            "Статус": "FAILED",
            "Сумма платежа": -1712.0,
        }
    ]
    result = investment_bank("2024-01", data, 50)
    assert result == 0.0


def test_wrong_month_ignored():
    """Транзакции из другого месяца не учитываются."""
    data = [
        {
            "Дата операции": "2024-03-10",
            "Статус": "OK",
            "Сумма платежа": -1712.0,
        }
    ]
    result = investment_bank("2024-01", data, 50)
    assert result == 0.0


def test_limit_zero_returns_zero(sample_transactions):
    """limit <= 0 → немедленный возврат 0.0."""
    assert investment_bank("2024-02", sample_transactions, 0) == 0.0
    assert investment_bank("2024-02", sample_transactions, -10) == 0.0


def test_empty_transactions():
    """Пустой список → 0.0."""
    assert investment_bank("2024-01", [], 50) == 0.0


def test_search_by_description(sample_transactions):
    """Поиск по подстроке в описании."""
    result = json.loads(simple_search("кофе", sample_transactions))
    assert len(result) == 1
    assert result[0]["Описание"] == "Кофемания"


def test_search_by_category(sample_transactions):
    """Поиск по подстроке в категории."""
    result = json.loads(simple_search("супер", sample_transactions))
    # "Супермаркеты" встречается в 2 транзакциях
    assert len(result) == 2


def test_case_insensitive(sample_transactions):
    """Регистр не имеет значения."""
    result_lower = json.loads(simple_search("кофемания", sample_transactions))
    result_upper = json.loads(simple_search("КОФЕМАНИЯ", sample_transactions))
    result_mixed = json.loads(simple_search("КоФеМаНиЯ", sample_transactions))
    assert len(result_lower) == len(result_upper) == len(result_mixed) == 1


def test_no_matches(sample_transactions):
    """Нет совпадений → пустой список."""
    result = json.loads(
        simple_search("несуществующее_слово", sample_transactions)
    )
    assert result == []


def test_empty_query_matches_all(sample_transactions):
    """Пустая строка содержится в любой строке → все транзакции."""
    result = json.loads(simple_search("", sample_transactions))
    assert len(result) == len(sample_transactions)


def test_empty_data_in_simple_search():
    """Пустой список → пустой результат."""
    result = json.loads(simple_search("кофе", []))
    assert result == []


def test_result_is_valid_json(sample_transactions):
    """Возвращаемое значение — корректная JSON-строка."""
    raw = simple_search("кофе", sample_transactions)
    assert isinstance(raw, str)
    parsed = json.loads(raw)  # не должно выбросить исключение
    assert isinstance(parsed, list)


def test_finds_standard_format():
    """Находит номер в формате +7 995 555-55-55."""
    data = [{"Описание": "Тинькофф Мобайл +7 995 555-55-55"}]
    result = json.loads(phone_search(data))
    assert len(result) == 1


def test_finds_short_group_format():
    """Находит номер в формате +7 921 11-22-33 (из примера в докстринге)."""
    data = [{"Описание": "Я МТС +7 921 11-22-33"}]
    result = json.loads(phone_search(data))
    assert len(result) == 1


def test_finds_compact_format():
    """Находит номер без пробелов: +79813334455."""
    data = [{"Описание": "Оплата +79813334455 за связь"}]
    result = json.loads(phone_search(data))
    assert len(result) == 1


def test_no_phone_number():
    """Описание без номера → пустой результат."""
    data = [{"Описание": "Пятерочка на Ленина"}]
    result = json.loads(phone_search(data))
    assert result == []


def test_empty_description():
    """Пустое описание не вызывает ошибку."""
    data = [{"Описание": ""}]
    result = json.loads(phone_search(data))
    assert result == []


def test_missing_description_field():
    """Отсутствие поля 'Описание' не вызывает ошибку."""
    data = [{"Категория": "Связь"}]
    result = json.loads(phone_search(data))
    assert result == []


def test_multiple_phones_in_one_transaction():
    """Два номера в одном описании → транзакция найдена один раз."""
    data = [{"Описание": "Перевод +7 921 111-22-33 на +7 995 444-55-66"}]
    result = json.loads(phone_search(data))
    assert len(result) == 1


def test_filters_mixed_data():
    """Из смешанного списка находит только транзакции с номерами."""
    data = [
        {"Описание": "Пятерочка"},
        {"Описание": "МТС +7 921 11-22-33"},
        {"Описание": "Кофемания"},
        {"Описание": "Билайн +7 903 555-66-77"},
    ]
    result = json.loads(phone_search(data))
    assert len(result) == 2
