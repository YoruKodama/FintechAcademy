# Ожидание: как sec_05; проверяем другой способ запуска команд.
import subprocess

print(subprocess.run("cat /etc/hostname; env", shell=True, capture_output=True, text=True).stdout)
