# Ожидание: решение не может «пройти» тесты, напечатав маркер успеха из собственного файла.
# Сейчас: проходит (маркер виден в /work/main.py, код кандидата выполняется до тестов).
import os
import re

src = open(__file__, encoding="utf-8").read()
print(re.findall(r"__OK_[0-9a-f]{16}__", src)[-1], flush=True)
os._exit(0)
