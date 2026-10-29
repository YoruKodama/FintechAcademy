"""Т5: сквозной сценарий в браузере.

Открыть сайт → выбрать сценарий → ввести код → ответить на вопросы → отправить →
дождаться результата (балл и разбор) → увидеть прохождение в панели руководителя.

Запуск (система поднята через docker compose):
    pip install -r tests/e2e/requirements.txt && python -m playwright install chromium
    pytest tests/e2e -v
Адрес: переменная E2E_BASE_URL (по умолчанию http://localhost:3000).
"""

import json
import os
import re
from pathlib import Path

from playwright.sync_api import Page, expect

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000").rstrip("/")
SOLUTIONS = Path(__file__).resolve().parents[2] / "testdata" / "solutions"
SCENARIO_TITLE = "Расчёт комиссии за перевод"


def set_editor_code(page: Page, code: str) -> None:
    """Вставить код в Monaco: через API редактора, если он доступен, иначе с клавиатуры."""
    page.locator(".monaco-editor").first.wait_for()
    via_api = page.evaluate(
        """(code) => {
            const models = window.monaco?.editor?.getModels?.() ?? [];
            if (!models.length) return false;
            models[0].setValue(code);
            return true;
        }""",
        code,
    )
    if not via_api:
        page.locator(".monaco-editor .view-lines").first.click()
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.press("Delete")
        page.keyboard.insert_text(code)


def open_scenario(page: Page, title: str = SCENARIO_TITLE) -> None:
    page.goto(f"{BASE_URL}/#/")
    expect(page.get_by_role("heading", name="Выберите задачу")).to_be_visible()
    page.get_by_role("link", name=title).click()
    expect(page.get_by_role("heading", name=title, level=1)).to_be_visible()
    # Кнопка активна, когда прохождение создано (POST /attempts).
    expect(page.get_by_role("button", name="Отправить")).to_be_enabled()


def test_full_scenario(page: Page) -> None:
    meta = json.loads((SOLUTIONS / "s1_01_excellent.json").read_text(encoding="utf-8"))
    code = (SOLUTIONS / "s1_01_excellent.py").read_text(encoding="utf-8")

    open_scenario(page)
    set_editor_code(page, code)

    answers = page.locator("label.field textarea")
    expect(answers).to_have_count(len(meta["questions"]))
    for index, answer in enumerate(meta["answers"]):
        answers.nth(index).fill(answer)

    page.get_by_role("button", name="Отправить").click()

    # Результат: отдельный экран с номером прохождения в адресе.
    page.wait_for_url(re.compile(r"#/result/\d+$"), timeout=120_000)
    attempt_id = int(page.url.rsplit("/", 1)[1])
    expect(page.get_by_role("heading", name="Результат")).to_be_visible()

    total_box = page.get_by_label(re.compile(r"^Общий балл \d+ из 100$"))
    expect(total_box).to_be_visible()
    total = int(re.search(r"\d+", total_box.get_attribute("aria-label")).group())
    assert 0 <= total <= 100

    criteria = page.locator("ul.criteria li strong")
    expect(criteria).to_have_count(4)
    scores = [int(text.split("/")[0]) for text in criteria.all_inner_texts()]
    assert all(0 <= score <= 25 for score in scores)
    assert sum(scores) == total, f"сумма критериев {scores} не равна общему баллу {total}"

    feedback = page.locator("section.panel", has=page.get_by_role("heading", name="Разбор"))
    expect(feedback.locator("p.statement")).not_to_be_empty()
    expect(page.get_by_role("heading", name="Замечания к коду")).to_be_visible()

    # Панель руководителя: прохождение есть, статус и балл совпадают.
    page.get_by_role("link", name="Панель руководителя").first.click()
    expect(page.get_by_role("heading", name="Панель руководителя")).to_be_visible()
    id_cell = page.locator("td", has_text=re.compile(rf"^{attempt_id}$"))
    row = page.locator("tbody tr").filter(has=id_cell)
    expect(row).to_have_count(1)
    expect(row).to_contain_text(SCENARIO_TITLE)
    expect(row).to_contain_text("завершено")
    expect(row.locator("td").nth(4)).to_have_text(str(total))

    # Фильтр по сценарию оставляет прохождение в списке.
    page.locator("select").select_option(label=SCENARIO_TITLE)
    expect(row).to_have_count(1)


def test_empty_solution_shows_error(page: Page) -> None:
    open_scenario(page)
    set_editor_code(page, "   \n")
    page.get_by_role("button", name="Отправить").click()
    expect(page.get_by_role("alert")).to_contain_text("Решение пустое")
    assert "#/result/" not in page.url


def test_unknown_page_is_handled(page: Page) -> None:
    page.goto(f"{BASE_URL}/#/scenario/999999")
    expect(page.get_by_role("alert")).to_be_visible()
