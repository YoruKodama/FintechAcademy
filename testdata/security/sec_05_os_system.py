# Ожидание: команда не выполняется или выполняется без последствий внутри изолированного контейнера.
import os

os.system("id; uname -a; ls / > /tmp/pwned.txt")
print(os.popen("whoami").read())
