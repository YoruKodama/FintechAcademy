# Тестовые данные (Т3)

Все данные **выдуманы**. Номера карт — тестовые/сгенерированные с верной контрольной суммой
Луна, телефоны и e-mail не принадлежат реальным людям (домены `example.*`).

## `pii/` — тексты для проверки обезличивания

10 текстов (`pii_01.txt` … `pii_10.txt`) с ФИО, телефонами, e-mail и картами в разных
форматах: в ответах кандидата, в коде, в логах, в списках. `pii_10.txt` — сложные случаи
(кириллический домен, телефон без кода, счёт, ИНН, СНИЛС, паспорт, метка в исходном тексте).

`expected.json`: для каждого файла
- `pii` — значения по видам (`fio`, `phone`, `email`, `card`, `account`, `inn`, `snils`, `passport`),
  которых **не должно быть** в тексте после `anonymize()`;
- `must_keep` — похожие на ПДн значения, которые трогать нельзя (суммы, даты, маски карт).

Автопроверка: `backend/tests/privacy/test_pii_dataset.py`.

## `solutions/` — решения для оценки качества модели

3 сценария × 6–7 решений (20 всего), от отличного до опасного. Условия и вопросы — из
`backend/app/db/seed/scenarios.json` (основа — `solutions/scenarios.md`).

Формат совместим с `scripts/eval.py` (`load_samples` в `app/scoring/evaluation.py`),
папка плоская:

- `sN_MM_<описание>.py` — решение (`sN` — сценарий);
- `sN_MM_<описание>.json` — `task`, `questions`, `answers`, `expected` (эталонный балл),
  а также `scenario` и `answers_level` для справки. Ключа `findings` нет намеренно:
  замечания находит анализатор.

Прогон через модель: `LLM_PROVIDER=ollama python scripts/eval.py`.

`expected.csv`:

| Колонка | Что это |
|---|---|
| `solution` | файл решения |
| `scenario` | `s1` / `s2` / `s3` |
| `meta` | файл с условием, вопросами, ответами и эталоном |
| `expected_total` | эталонный балл 0–100 = сумма четырёх критериев |
| `correctness`, `code_quality`, `safety`, `explanation` | эталон по критериям, 0–25 |
| `expected_findings` | что **должен найти анализатор**: только его 8 кодов, `КОД:severity` через `;` |
| `expected_notes` | проблемы, которые анализатор не ищет (для оценки модели): `код:severity` |
| `notes` | почему такой балл |

Автопроверки: `backend/tests/testdata/test_testdata_integrity.py` (формат и суммы) и
`backend/tests/testdata/test_testdata_analyzer.py` (анализатор находит `expected_findings`;
лишние замечания — известные ложные срабатывания, отмечены xfail).

Поведение решений: `python testdata/check_solutions.py` — каждое решение в отдельном процессе
с таймаутом 5 с; решения с `os.system`/`subprocess`/записью на диск вне песочницы не
запускаются.

| Решение | Тесты | Анализатор |
|---|---|---|
| s1_01_excellent | 10/10 | — |
| s1_02_good | 9/10 | — |
| s1_03_float | 0/10 | FLOAT_MONEY |
| s1_04_no_limits | 0/10 | FLOAT_MONEY, BARE_EXCEPT |
| s1_05_dangerous | не запускается | EVAL_EXEC, FLOAT_MONEY, NO_INPUT_VALIDATION |
| s1_06_long_function | 10/10 | LONG_FUNCTION |
| s1_07_missing_return | 9/10 | MISSING_RETURN |
| s2_01_excellent | 10/10 | — (ложное NO_INPUT_VALIDATION) |
| s2_02_good | 10/10 | — (ложное NO_INPUT_VALIDATION) |
| s2_03_no_luhn | 6/10 | NO_INPUT_VALIDATION |
| s2_04_logs_pan | 6/10 | NO_INPUT_VALIDATION |
| s2_05_broken | 0/10 (зависает) | BARE_EXCEPT, NO_INPUT_VALIDATION |
| s2_06_unused_variable | 10/10 | UNUSED_VARIABLE |
| s2_07_unused_and_missing_return | 8/10 | UNUSED_VARIABLE, MISSING_RETURN |
| s3_01_excellent | 10/10 | — (ложное DEEP_NESTING) |
| s3_02_good | 9/10 | — (ложное DEEP_NESTING) |
| s3_03_mutates | 5/10 | NO_INPUT_VALIDATION |
| s3_04_float_hardcode | 2/10 | FLOAT_MONEY, DEEP_NESTING, BARE_EXCEPT |
| s3_05_dangerous | не запускается | EVAL_EXEC, NO_INPUT_VALIDATION |
| s3_06_deep_nesting | 10/10 | DEEP_NESTING |

### Коды в `expected_findings` (анализатор)

`FLOAT_MONEY`, `BARE_EXCEPT`, `EVAL_EXEC`, `NO_INPUT_VALIDATION`, `LONG_FUNCTION`,
`UNUSED_VARIABLE`, `DEEP_NESTING`, `MISSING_RETURN` — severity как у анализатора.

### Коды в `expected_notes` (анализатор их не ищет)

| Код | Что значит |
|---|---|
| `wrong_result` | неверный результат на эталонных случаях |
| `silent_error` | ошибка глушится, результат неверный |
| `infinite_loop` | цикл без выхода |
| `os_command` | `os.system`, `subprocess` с `shell=True` |
| `network_access` | обращение в сеть из решения |
| `hardcoded_secret` | токен/пароль в коде |
| `pan_in_logs` | полный номер карты в логах |
| `mutable_default` | изменяемый аргумент по умолчанию |
| `input_mutation` | изменяет входные данные |
| `unsafe_deserialization` | `pickle` и т. п. |
| `no_input_validation` | слабая проверка входа, которую анализатор не ловит |
| `magic_numbers` | константы зашиты в код |
| `duplicated_code` | повтор кода |
| `print_debug` | отладочный `print` |
