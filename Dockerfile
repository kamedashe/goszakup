FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /goszakup

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Копируем скрипт запуска
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Запускаем через скрипт
CMD ["./entrypoint.sh"]