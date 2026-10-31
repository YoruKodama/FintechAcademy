"""Тесты обезличивания. Все данные в тестах выдуманные."""

import pytest

from app.privacy import anonymize, deanonymize

PII_CASES = [
    (
        "Клиент Иванов Пётр Сергеевич (тел. +7 (999) 123-45-67) просит перевести 1000 рублей.",
        ["Иванов", "Пётр", "Сергеевич", "+7 (999) 123-45-67", "999"],
    ),
    (
        "Пишите на ivan.petrov@example.com или support_test@mail.example.org",
        ["ivan.petrov@example.com", "support_test@mail.example.org", "petrov"],
    ),
    (
        "Карта 4276 1234 5678 9012 и вторая 4111111111111111",
        ["4276 1234 5678 9012", "4111111111111111", "5678"],
    ),
    (
        "Меня зовут Мария, номер 8 (916) 555-12-34, запасной 89161234567",
        ["Мария", "555-12-34", "89161234567"],
    ),
    (
        "Анна Петровна Смирнова оформила заявку. Заявку проверил Смирнов А.В.",
        ["Анна", "Петровна", "Смирнова", "Смирнов", "А.В."],
    ),
    (
        "Передать документы Ивану Петровичу Сидорову по адресу почты sidorov@example.net",
        ["Ивану", "Петровичу", "Сидорову", "sidorov@example.net"],
    ),
    (
        "# Владелец счёта: Козлов Дмитрий\nuser_phone = '+79161234567'",
        ["Козлов", "Дмитрий", "+79161234567"],
    ),
    (
        "Сотрудник Елена Кузнецова, +49 30 1234567, карта 5555-5555-5555-4444",
        ["Елена", "Кузнецова", "+49 30 1234567", "5555-5555-5555-4444"],
    ),
    (
        "И. И. Петров перевёл деньги Александру Сергеевичу Пушкину, e-mail a.pushkin@example.com",
        ["Петров", "Александру", "Сергеевичу", "Пушкину", "a.pushkin@example.com"],
    ),
    (
        "Получатель: Ольга Николаевна Морозова, тел 7 916 000 11 22, карта 2200 7000 1111 2222",
        ["Ольга", "Николаевна", "Морозова", "916 000 11 22", "2200 7000 1111 2222"],
    ),
]


@pytest.mark.parametrize(("text", "secrets"), PII_CASES)
def test_no_pii_leaks(text, secrets):
    cleaned, mapping = anonymize(text)
    for secret in secrets:
        assert secret not in cleaned, f"утечка {secret!r}: {cleaned}"
    assert mapping, "ожидалась хотя бы одна метка"
    assert deanonymize(cleaned, mapping) == text


def test_labels_are_stable_and_numbered():
    cleaned, mapping = anonymize("a@example.com, b@example.com, снова a@example.com")
    assert cleaned == "[EMAIL_1], [EMAIL_2], снова [EMAIL_1]"
    assert mapping == {"[EMAIL_1]": "a@example.com", "[EMAIL_2]": "b@example.com"}


def test_label_kinds():
    cleaned, _ = anonymize(
        "Клиент Иванов Иван, ivan@example.com, +7 999 111-22-33, 4111 1111 1111 1111"
    )
    assert "[ФИО_1]" in cleaned
    assert "[EMAIL_1]" in cleaned
    assert "[ТЕЛЕФОН_1]" in cleaned
    assert "[КАРТА_1]" in cleaned


def test_anonymize_is_idempotent():
    once, _ = anonymize(PII_CASES[0][0])
    twice, mapping = anonymize(once)
    assert twice == once
    assert mapping == {}


def test_empty_text():
    assert anonymize("") == ("", {})


CODE_SAMPLES = [
    '''from decimal import Decimal


@dataclass
class Account:
    """Счёт клиента банка."""

    balance: Decimal = Decimal("1000.50")


def transfer(source: Account, target: Account, amount: Decimal) -> None:
    # Проверяем остаток перед списанием. Сумма Перевода не может быть отрицательной.
    if amount <= 0 or source.balance < amount:
        raise ValueError("Недостаточно средств")
    source.balance -= amount
    target.balance += amount
''',
    """LIMIT = 80000000000
BIG = 1234567890123456  # не карта: не сходится контрольная сумма
PRICE = 8_000_000.25
mask = a @ b
version = "1.2.3.4"
# Остаток Счёта и Комиссия Банка считаются отдельно. Банк Открытие
""",
]


@pytest.mark.parametrize("code", CODE_SAMPLES)
def test_plain_code_is_not_changed(code):
    cleaned, mapping = anonymize(code)
    assert cleaned == code
    assert mapping == {}
