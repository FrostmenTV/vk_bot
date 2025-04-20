#!/bin/bash

# Создание systemd сервиса
sudo tee /etc/systemd/system/vkbot.service > /dev/null <<EOF
[Unit]
Description=VK Bot Service
After=network.target mysql.service

[Service]
User=ubuntu
WorkingDirectory=/opt/vk_bot
ExecStart=/opt/vk_bot/venv/bin/python /opt/vk_bot/src/bot.py
Restart=always
Environment="PATH=/opt/vk_bot/venv/bin:/usr/bin"

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd и запуск сервиса
sudo systemctl daemon-reload
sudo systemctl enable vkbot
sudo systemctl start vkbot

echo "Сервис установлен и запущен"
echo "Для просмотра логов: journalctl -u vkbot -f"