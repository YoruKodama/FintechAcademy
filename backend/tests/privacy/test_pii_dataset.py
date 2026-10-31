"""Прогон набора testdata/pii через обезличивание.

Для каждого файла проверяем: ни одно значение из expected.json["pii"] не осталось в тексте,
значения из "must_keep" не тронуты, обратная подстановка возвращает исходный текст.
Виды ПДн, которые anonymize() пока не умеет, отмечены xfail (см. KNOWN_GAPS).
"""

import json
from pathlib import Path

import pytest

privacy = pytest.importorskip("app.privacy", reason="модуль app.privacy ещё не влит")
if not hasattr(privacy, "anonymize"):
    pytest.skip("anonymize() ещё не влита в эту ветку", allow_module_level=True)
anonymize = privacy.anonymize
deanonymize = privacy.deanonymize

PII_DIR = Path(__file__).resolve().parents[3] / "testdata" / "pii"
EXPECTED = json.loads((PII_DIR / "expected.json").read_text(encoding="utf-8"))

# Виды ПДн, которые anonymize() сейчас не маскирует (дефекты в Issues).
KNOWN_GAPS: set[str] = set()
# Конкретные значения, которые сейчас не маскируются: (файл, значение).
KNOWN_VALUE_GAPS: set[tuple[str, str]] = set()


def _cases():
    for name, spec in sorted(EXPECTED.items()):
        for kind, values in spec["pii"].items():
            for value in values:
                gap = kind in KNOWN_GAPS or (name, value) in KNOWN_VALUE_GAPS
                xfail = pytest.mark.xfail(reason=f"дефект: {kind} не маскируется", strict=True)
                marks = [xfail] if gap else []
                yield pytest.param(name, value, id=f"{name}-{kind}-{value}", marks=marks)


def _text(name: str) -> str:
    return (PII_DIR / name).read_text(encoding="utf-8")


def test_dataset_has_ten_files():
    assert len(EXPECTED) == 10
    assert all((PII_DIR / name).exists() for name in EXPECTED)


@pytest.mark.parametrize(("name", "value"), list(_cases()))
def test_pii_value_is_removed(name, value):
    masked, _ = anonymize(_text(name))
    assert value not in masked


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_non_pii_is_kept(name):
    masked, _ = anonymize(_text(name))
    for value in EXPECTED[name]["must_keep"]:
        if value == "[ТЕЛЕФОН_1]":
            continue  # проверяется в test_roundtrip
        assert value in masked


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_roundtrip(name):
    text = _text(name)
    masked, mapping = anonymize(text)
    assert deanonymize(masked, mapping) == text
