"""Прогон testdata/security через API тренажёра (Т6).

Запуск (система поднята через docker compose):
    python tests/security/run_security_suite.py --api http://localhost:8000 --scenario 1

Для каждого файла: создать прохождение, отправить код, замерить время, сохранить ответ.
Итог печатается таблицей и пишется в docs/qa/security-run.json — по нему заполняется
docs/qa/security.md. После каждой атаки проверяется, что /health отвечает (сервер жив).
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = ROOT / "testdata" / "security"
OUT = ROOT / "docs" / "qa" / "security-run.json"


def call(api: str, method: str, path: str, body: dict | None = None, timeout: float = 120):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        api + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")[:2000]
    except Exception as exc:  # noqa: BLE001 — нужен любой сбой как результат проверки
        return None, f"{type(exc).__name__}: {exc}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--scenario", type=int, default=1)
    args = parser.parse_args()

    results = []
    for path in sorted(CASES_DIR.glob("sec_*.py")):
        status, attempt = call(args.api, "POST", "/attempts", {"scenario_id": args.scenario})
        if status != 201:
            results.append({"case": path.stem, "error": f"POST /attempts: {status} {attempt}"})
            continue
        started = time.perf_counter()
        status, body = call(
            args.api,
            "POST",
            f"/attempts/{attempt['id']}/submit",
            {"code": path.read_text(encoding="utf-8"), "answers": ["-", "-"]},
        )
        elapsed = round(time.perf_counter() - started, 2)
        health, _ = call(args.api, "GET", "/health", timeout=10)
        result = body.get("result") if isinstance(body, dict) else None
        results.append(
            {
                "case": path.stem,
                "http": status,
                "seconds": elapsed,
                "server_alive": health == 200,
                "total": result.get("total") if result else None,
                "findings": [f["code"] for f in result.get("findings", [])] if result else None,
                "raw": body if not isinstance(body, dict) else None,
            }
        )
        print(f"{path.stem:28} http={status} {elapsed:>6}s alive={health == 200}")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nСохранено: {OUT}")


if __name__ == "__main__":
    main()
