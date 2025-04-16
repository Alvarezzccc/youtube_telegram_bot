#!/bin/bash

SERVICE_NAME=telegram_bot
USER_HOME=$(eval echo ~$USER) 
BOT_PATH="${USER_HOME}/Documents/youtube_telegram_bot/start_bot.sh"
SCRIPT_PATH="${USER_HOME}/Documents/youtube_telegram_bot/youtube_telegram_bot.py"

echo "[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
ExecStartPre=/bin/sleep 10
ExecStart=${BOT_PATH}
WorkingDirectory=$(dirname ${BOT_PATH})
Restart=always
RestartSec=10s 
User=${USER}

[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null

sudo chmod 644 /etc/systemd/system/${SERVICE_NAME}.service

chmod +x "$BOT_PATH"

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

echo "✅ Telegram bot configured to start on boot."