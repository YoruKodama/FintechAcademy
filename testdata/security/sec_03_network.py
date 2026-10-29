# Ожидание: сети в песочнице нет — ошибка соединения, данные никуда не ушли.
import urllib.request

print(urllib.request.urlopen("https://example.com", timeout=5).status)
