from app.config import settings
from app.data.sqlite import BotDB


db = BotDB(db_path=settings.BOT_DB_PATH)
