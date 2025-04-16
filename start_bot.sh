#!/bin/bash

# Navigate to the bot directory
cd ~/Documents/youtube_telegram_bot || exit 1

# Activate the Python virtual environment
source python_env/bin/activate

# Export environment variables
export $(grep -v '^#' telegramVars.env | xargs)

# Run the bot script
python3 youtube_telegram_bot.py