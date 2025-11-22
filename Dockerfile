FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Установка часового пояса (Астана/Алматы)
ENV TZ=Asia/Almaty
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

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