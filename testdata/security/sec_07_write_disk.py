# Ожидание: файловая система только для чтения или квотирована; запись гигабайтов невозможна.
with open("/tmp/big.bin", "wb") as file:
    for _ in range(10_000):
        file.write(b"\0" * 1024 * 1024)
print("written")
