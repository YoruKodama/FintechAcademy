"""Тесты обезличивания: ПДн не должны уходить в модель.

Все данные выдуманные. Падающие сейчас случаи отмечены xfail со ссылкой на дефект
из docs/qa (номер Issue проставить после заведения).
"""

import pytest

from app.privacy import anonymize, deanonymize


def masked(text: str) -> str:
    return anonymize(text)[0]


# --- телефоны ---------------------------------------------------------------


@pytest.mark.parametrize(
    "phone",
    [
        "+7 (912) 345-67-89",
        "+7-912-345-67-89",
        "+79123456789",
        "8 912 345 67 89",
        "89123456789",
        "8(495)123-45-67",
        "+44 20 7946 0958",
    ],
)
def test_phone_is_masked(phone):
    result = masked(f"Звоните: {phone}.")
    assert phone not in result
    assert "[ТЕЛЕФОН_1]" in result


@pytest.mark.xfail(reason="Дефект: 10-значный телефон без +7/8 не маскируется", strict=True)
def test_phone_without_prefix_is_masked():
    assert "9123456789" not in masked("телефон 9123456789")


# --- карты -----------------------------------------------------------------


@pytest.mark.parametrize(
    "card",
    ["4276 3800 1234 5678", "4276-3800-1234-5678", "4111111111111111", "5555555555554444"],
)
def test_card_is_masked(card):
    result = masked(f"Карта {card}")
    assert card not in result
    assert "[КАРТА_1]" in result


@pytest.mark.xfail(
    reason="Дефект: карта без пробелов с точкой после номера не маскируется", strict=True
)
def test_plain_card_at_end_of_sentence_is_masked():
    assert "4111111111111111" not in masked("Оплата с карты 4111111111111111.")


def test_plain_digits_failing_luhn_are_kept():
    """16 цифр без пробелов, не проходящие Луна, считаются не картой (например, сумма)."""
    assert masked("amount = 1234567812345678") == "amount = 1234567812345678"


def test_masked_card_suffix_kept():
    """Уже замаскированная карта не трогается."""
    assert masked("Карта **** **** **** 1234") == "Карта **** **** **** 1234"


# --- e-mail ----------------------------------------------------------------


@pytest.mark.parametrize("email", ["ivan.petrov@vtb.ru", "IVAN@MAIL.RU", "a.b+tag@sub.example.com"])
def test_email_is_masked(email):
    result = masked(f"Пишите на {email}")
    assert email not in result
    assert "[EMAIL_1]" in result


@pytest.mark.xfail(reason="Дефект: e-mail с кириллическим доменом не маскируется", strict=True)
def test_cyrillic_email_is_masked():
    assert "test@почта.рф" not in masked("Пишите на test@почта.рф")


# --- ФИО и банковские ПДн (дефекты) ----------------------------------------


@pytest.mark.xfail(reason="Дефект critical: ФИО не обезличиваются", strict=True)
@pytest.mark.parametrize("name", ["Иванов Иван Иванович", "Петров П.П.", "Сидорова Анна"])
def test_full_name_is_masked(name):
    assert name not in masked(f"Клиент {name} оформил перевод.")


@pytest.mark.xfail(reason="Дефект: банковские ПДн не маскируются", strict=True)
@pytest.mark.parametrize(
    "value",
    ["40817810099910004312", "7707083893", "112-233-445 95", "4510 123456"],
    ids=["счёт", "ИНН", "СНИЛС", "паспорт"],
)
def test_bank_identifiers_are_masked(value):
    assert value not in masked(f"Данные: {value}")


# --- метки и обратная подстановка -------------------------------------------


def test_same_value_gets_same_label():
    text, mapping = anonymize("+7 912 345 67 89 и снова +7 912 345 67 89, а это 8 900 111 22 33")
    assert text.count("[ТЕЛЕФОН_1]") == 2
    assert "[ТЕЛЕФОН_2]" in text
    assert len(mapping) == 2


def test_mapping_contains_original_values():
    _, mapping = anonymize("ivan@vtb.ru, 4111111111111111, +79123456789")
    assert set(mapping.values()) == {"ivan@vtb.ru", "4111111111111111", "+79123456789"}


@pytest.mark.parametrize(
    "text",
    [
        "Иванов, +7 (912) 345-67-89, ivan@vtb.ru, карта 4276 3800 1234 5678",
        "def fee(amount):\n    return amount * 0.01  # звонить 89123456789\n",
    ],
)
def test_roundtrip(text):
    masked_text, mapping = anonymize(text)
    assert deanonymize(masked_text, mapping) == text


@pytest.mark.xfail(reason="Дефект: метка во входном тексте ломает deanonymize", strict=True)
def test_roundtrip_when_input_contains_label_like_text():
    text = "x = 8 912 345 67 89; y = '[ТЕЛЕФОН_1]'"
    masked_text, mapping = anonymize(text)
    assert deanonymize(masked_text, mapping) == text


# --- граничные случаи -------------------------------------------------------


def test_empty_string():
    assert anonymize("") == ("", {})


def test_text_without_pii_is_unchanged():
    code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    assert anonymize(code) == (code, {})


def test_dates_and_amounts_are_not_masked():
    text = "Дата 2024-10-25, сумма 1 234 567,89 руб, id=42"
    assert masked(text) == text


def test_very_long_text_is_processed():
    chunk = "Клиент: ivan@vtb.ru, +79123456789, 4111111111111111\n"
    text = chunk * 5000
    masked_text, mapping = anonymize(text)
    assert "ivan@vtb.ru" not in masked_text
    assert len(mapping) == 3


@pytest.mark.xfail(
    reason="Дефект: квадратичное время на длинной строке без пробелов (регулярка e-mail)",
    strict=True,
)
def test_long_token_is_fast():
    """Кандидат может прислать длинный литерал: обезличивание не должно подвешивать сервер."""
    import time

    started = time.perf_counter()
    anonymize("a" * 50_000)
    assert time.perf_counter() - started < 1.0
