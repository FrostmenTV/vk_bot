#!/bin/bash

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка Python зависимостей
pip install -r config/requirements.txt

# Создание папки для логов
mkdir -p logs

echo "Установка завершена. Для запуска:"
echo "source venv/bin/activate && python3 src/bot.py"