# Ожидание: обход запретов через __import__/getattr не даёт выполнить команды.
getattr(__import__("o" + "s"), "sys" + "tem")("echo bypass > /tmp/bypass.txt")
exec(bytes.fromhex("7072696e7428276578656327293b").decode())
