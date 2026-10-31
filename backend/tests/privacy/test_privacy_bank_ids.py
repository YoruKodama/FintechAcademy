"""Банковские идентификаторы: счёт, ИНН, СНИЛС, паспорт, короткий телефон, метки, скорость."""

import time

import pytest

from app.privacy import anonymize, deanonymize

VALID_INN_10 = "7707083893"
VALID_INN_12 = "500100732259"


def masked(text: str) -> str:
    return anonymize(text)[0]


def test_account_is_masked_with_own_label():
    text, mapping = anonymize("Счёт 40817810099910004312 открыт")
    assert "40817810099910004312" not in text
    assert "[СЧЁТ_1]" in text
    assert mapping["[СЧЁТ_1]"] == "40817810099910004312"


@pytest.mark.parametrize("value", [VALID_INN_10, VALID_INN_12])
def test_bare_inn_with_valid_checksum_is_masked(value):
    assert value not in masked(f"Организация {value}.")


@pytest.mark.parametrize("value", ["1234567890", "1234567890123", "123456789012"])
def test_numbers_that_are_not_inn_stay_in_code(value):
    code = f"LIMIT = {value}\n"
    assert masked(code) == code


def test_inn_with_cue_is_masked_even_with_wrong_checksum():
    assert "1234567890" not in masked("ИНН 1234567890")


def test_snils_with_spaces_and_dashes():
    assert "112-233-445 95" not in masked("СНИЛС 112-233-445 95")
    assert "112-233-445-95" not in masked("СНИЛС 112-233-445-95")


@pytest.mark.parametrize("value", ["4510 123456", "45 10 123456"])
def test_passport_is_masked(value):
    assert value not in masked(f"Паспорт {value}, выдан давно")


@pytest.mark.parametrize("value", ["9161234567", "(916) 123-45-67", "916 123 45 67"])
def test_phone_without_country_code_is_masked(value):
    text, mapping = anonymize(f"Звоните {value}")
    assert value not in text
    assert "[ТЕЛЕФОН_1]" in text


def test_ten_digit_number_starting_with_nine_is_phone_not_inn():
    text, mapping = anonymize("номер 9161234567")
    assert "[ТЕЛЕФОН_1]" in text
    assert "[ИНН_1]" not in text


def test_cyrillic_email_domain():
    assert "ivanov@почта.рф" not in masked("пишите ivanov@почта.рф сегодня")


def test_card_at_end_of_sentence_and_before_comma():
    assert "2200001234567891" not in masked("Карта 2200001234567891.")
    assert "2200001234567891" not in masked("Карта 2200001234567891, остальное позже")


def test_decimal_numbers_are_not_cards():
    text = "значение 1234567890123456.78 в отчёте"
    assert masked(text) == text


def test_existing_label_in_input_does_not_break_deanonymize():
    text = "x = 8 912 345 67 89; y = '[ТЕЛЕФОН_1]'"
    masked_text, mapping = anonymize(text)
    assert "[ТЕЛЕФОН_2]" in masked_text
    assert deanonymize(masked_text, mapping) == text


@pytest.mark.parametrize(
    "text",
    ["a" * 300_000, "я" * 300_000, "1" * 300_000, "a@" * 150_000, "Иван " * 60_000],
    ids=["latin", "cyrillic", "digits", "at-signs", "names"],
)
def test_long_inputs_are_fast(text):
    started = time.perf_counter()
    anonymize(text)
    assert time.perf_counter() - started < 5.0
