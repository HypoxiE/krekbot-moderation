import os

DB_HOST=os.getenv("DB_HOST", "localhost")
DB_PORT=os.getenv("DB_PORT", "5432")
DB_USER=os.getenv("DB_USER", "discord_moderation_bot")
DB_PASS=os.getenv("DB_PASSWORD", "moderation_bot")
DB_NAME=os.getenv("DB_NAME", "discord_moderation_bot_db")
