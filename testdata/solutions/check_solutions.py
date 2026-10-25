"""Прогон тестовых решений на эталонных случаях сценариев S1-S3.

Запуск: python testdata/solutions/check_solutions.py
Каждое решение выполняется в отдельном процессе с таймаутом. Решения, которые вызывают
внешние команды (os.system, subprocess) или пишут на диск, вне песочницы НЕ запускаются.
Результат: доля пройденных случаев, по ней проверяется колонка correctness в expected.csv.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIMEOUT_SEC = 5
UNSAFE = re.compile(r"\bos\.system\b|\bsubprocess\b|\bpickle\.dump\b|\bopen\([^)]*['\"]w")

CASES = {
    "s1": [
        ("calc_fee", ["1000"], "Decimal('30.00')"),
        ("calc_fee", ["2000"], "Decimal('30.00')"),
        ("calc_fee", ["10000"], "Decimal('150.00')"),
        ("calc_fee", ["12345.67"], "Decimal('185.19')"),
        ("calc_fee", ["200000"], "Decimal('3000.00')"),
        ("calc_fee", ["1000000"], "Decimal('3000.00')"),
        ("calc_fee", ["0.1"], "Decimal('30.00')"),
        ("calc_fee", ["0"], "ValueError"),
        ("calc_fee", ["-100"], "ValueError"),
        ("calc_fee", ["abc"], "ValueError"),
    ],
    "s2": [
        ("is_valid_card", ["4111 1111 1111 1111"], "True"),
        ("is_valid_card", ["4111-1111-1111-1111"], "True"),
        ("is_valid_card", ["2200001234567891"], "True"),
        ("is_valid_card", ["4111 1111 1111 1112"], "False"),
        ("is_valid_card", ["4111 1111 1111"], "False"),
        ("is_valid_card", ["4111 1111 1111 111a"], "False"),
        ("is_valid_card", ["0000 0000 0000 0000 000"], "True"),
        ("mask_card", ["4111 1111 1111 1111"], "'**** **** **** 1111'"),
        ("mask_card", ["2200-0012-3456-7891"], "'**** **** **** 7891'"),
        ("mask_card", ["1234"], "ValueError"),
    ],
    "s3": [
        ("process_statement", ["Decimal('1000')", [
            {"id": "1", "type": "in", "amount": "500.50"},
            {"id": "2", "type": "out", "amount": "200.25"}]],
         "(Decimal('1300.25'), [])"),
        ("process_statement", ["Decimal('0')", [
            {"id": "a", "type": "in", "amount": "300000"},
            {"id": "b", "type": "out", "amount": "150000"},
            {"id": "c", "type": "out", "amount": "100000"}]],
         "(Decimal('50000'), ['b'])"),
        ("process_statement", ["Decimal('0.1')", [
            {"id": "1", "type": "in", "amount": "0.2"}]],
         "(Decimal('0.3'), [])"),
        ("process_statement", ["Decimal('0')", [
            {"id": "x", "type": "out", "amount": "500"}], "Decimal('100')"],
         "(Decimal('-500'), ['x'])"),
        ("process_statement", ["Decimal('0')", [{"id": "1", "type": "bonus", "amount": "1"}]],
         "ValueError"),
        ("process_statement", ["Decimal('0')", [{"id": "1", "type": "in", "amount": "-5"}]],
         "ValueError"),
        ("process_statement", ["Decimal('0')", [{"id": "1", "type": "in", "amount": "abc"}]],
         "ValueError"),
        ("process_statement", ["Decimal('0')", []], "(Decimal('0'), [])"),
        ("__immutability__", [], "True"),
        ("__repeat_call__", [], "True"),
    ],
}

RUNNER = r'''
import importlib.util, json, sys
from decimal import Decimal
spec = importlib.util.spec_from_file_location("solution", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
func, args = json.loads(sys.argv[2])
try:
    if func == "__immutability__":
        ops = [{"id": "1", "type": "in", "amount": "10"}]
        mod.process_statement(Decimal("0"), ops)
        result = ops == [{"id": "1", "type": "in", "amount": "10"}]
    elif func == "__repeat_call__":
        ops = [{"id": "b", "type": "out", "amount": "200000"}]
        mod.process_statement(Decimal("0"), ops)
        result = mod.process_statement(Decimal("0"), ops)[1] == ["b"]
    else:
        args = [eval(a) if isinstance(a, str) and a.startswith("Decimal") else a for a in args]
        result = getattr(mod, func)(*args)
    print(repr(result))
except ValueError:
    print("ValueError")
except Exception as exc:
    print("ERROR " + type(exc).__name__)
'''


def run_case(path: Path, func: str, args: list) -> str:
    try:
        done = subprocess.run(
            [sys.executable, "-I", "-c", RUNNER, str(path), json.dumps([func, args])],
            capture_output=True, text=True, timeout=TIMEOUT_SEC, cwd=HERE,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    lines = done.stdout.strip().splitlines()
    return lines[-1] if lines else "ERROR " + (done.stderr.strip().splitlines() or ["?"])[-1]


def main() -> int:
    summary = {}
    for scenario, cases in CASES.items():
        for path in sorted((HERE / scenario).glob("*.py")):
            if UNSAFE.search(path.read_text(encoding="utf-8")):
                summary[path.stem] = "не запускалось: внешние команды/запись на диск"
                print(f"{path.stem:28} SKIP (опасно вне песочницы)")
                continue
            passed = 0
            fails = []
            for func, args, expected in cases:
                got = run_case(path, func, args)
                if got == expected:
                    passed += 1
                else:
                    fails.append(f"{func}{args if len(str(args)) < 40 else '(...)'}: ждали {expected}, получили {got}")
            summary[path.stem] = f"{passed}/{len(cases)}"
            print(f"{path.stem:28} {passed:2}/{len(cases)}")
            for line in fails:
                print("    -", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
