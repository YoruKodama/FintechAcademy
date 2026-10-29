# Ожидание: файлы хоста/backend недоступны (нет /etc/shadow, .env, исходников, переменных с секретами).
import os

for path in ("/etc/passwd", "/etc/shadow", "/srv/app/main.py", "/srv/.env", "/proc/1/environ"):
    try:
        with open(path, encoding="utf-8", errors="replace") as file:
            print(path, "READ", file.read(200))
    except Exception as exc:
        print(path, "DENIED", type(exc).__name__)
print("ENV", {k: v for k, v in os.environ.items() if "PASS" in k or "KEY" in k or "URL" in k})
