# Ожидание: лимит процессов (pids-limit) останавливает размножение.
import os

while True:
    os.fork()
