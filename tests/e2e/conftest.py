"""Общие настройки e2e-тестов: адрес системы и браузер Playwright."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser, request) -> Page:
    context = browser.new_context(locale="ru-RU", viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.set_default_timeout(int(os.getenv("E2E_TIMEOUT_MS", "30000")))
    yield page
    report = getattr(request.node, "rep_call", None)
    if report is not None and report.failed:
        ARTIFACTS.mkdir(exist_ok=True)
        page.screenshot(path=str(ARTIFACTS / f"{request.node.name}.png"), full_page=True)
    context.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
