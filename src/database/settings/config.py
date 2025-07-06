from database.settings.db_settings import *

class Settings:

	def __init__(self):
		self.DB_HOST = DB_HOST
		self.DB_PORT = DB_PORT
		self.DB_USER = DB_USER
		self.DB_PASS = DB_PASS
		self.DB_NAME = DB_NAME

	@property
	def DB_URL(self):
		return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
	