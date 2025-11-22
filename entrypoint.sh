#!/bin/bash

# 1. Запускаем фейковый сервер в фоне
python fake_ncalayer.py &

# 2. Ждем пару секунд, чтобы он поднялся
sleep 3

# 3. Запускаем основного бота (Playwright)
python browser.py