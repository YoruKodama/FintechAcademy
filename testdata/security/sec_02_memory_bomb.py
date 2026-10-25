# Ожидание: процесс убит по лимиту памяти (SANDBOX_MEMORY_MB), хост не тормозит.
chunks = []
while True:
    chunks.append(bytearray(100 * 1024 * 1024))
