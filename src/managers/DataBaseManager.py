import disnake
from disnake.ext import commands
from disnake.ext import tasks
from typing import Optional, Union, List, Dict, Any, AsyncIterator, Tuple
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload, contains_eager, aliased
from sqlalchemy import select, delete, insert, update
from sqlalchemy import func, asc, desc, false, tuple_
from sqlalchemy import and_, or_, not_
import subprocess
import os
from types import SimpleNamespace

class Model:
	def __init__(self, model):
		self.model = model
		self.m = model

	async def __aenter__(self):
		return self.model

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		return None

class DatabaseManager:

	def __init__(self, engine, tables_data):
		self.engine = engine
		self.session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
		self.metadata = tables_data['base'].metadata

		self.model_classes = {}
		tables = self.metadata.tables
		for table_name, table in tables.items():
			model_class = next((cls for cls in tables_data['base'].__subclasses__() if cls.__tablename__ == table_name), None)
			if model_class:
				#print(f"Table: {table_name}, Model Class: {model_class.__name__}")
				self.model_classes[table_name] = model_class

		self.models = {table_name: Model(model) for table_name, model in self.model_classes.items()}

		self.tables_data = tables_data

		#функции sqlalchemy
		self.joinedload = joinedload
		self.selectinload = selectinload
		self.contains_eager = contains_eager
		self.aliased = aliased
		self.select = select
		self.delete = delete
		self.insert = insert
		self.update = update
		self.func = func
		self.desc = desc
		self.asc = asc
		self.false = false
		self.tuple_ = tuple_
		self.and_ = and_
		self.or_ = or_
		self.not_ = not_

		#ошибки sqlalchemy
		exceptions = SimpleNamespace(
			IntegrityError = IntegrityError
		)
	
	async def close(self):
		await self.engine.dispose()

	async def pg_dump(self, echo=False, backup_file='src/backups/discord_moderation_bot_backup.sql'):
		conn = await self.engine.connect()
		db_name = self.engine.url.database
		user = self.engine.url.username
		host = self.engine.url.host
		port = self.engine.url.port
		password = self.engine.url.password

		os.environ['PGPASSWORD'] = password
		command = [
			'pg_dump',
			'-h', host,
			'-p', str(port),
			'-U', user,
			'-F', 'p',  # <-- plain text SQL
		] + (['-v'] if echo else []) + [
			'-f', backup_file,
			db_name
		]

		try:
			subprocess.run(command, check=True)
			if echo:
				print(f"{datetime.datetime.now():%H:%M:%S %d-%m-%Y} :: SQL backup of '{db_name}' created.")
		except subprocess.CalledProcessError as e:
			print(f"{datetime.datetime.now():%H:%M:%S %d-%m-%Y} :: Backup failed: {e}")
		finally:
			await conn.close()
			return backup_file

	async def pg_restore(self, echo = False, backup_file = 'backups/backup_file.backup'):
		conn = await self.engine.connect()
		db_name = self.engine.url.database
		user = self.engine.url.username
		host = self.engine.url.host
		port = self.engine.url.port
		password = self.engine.url.password

		os.environ['PGPASSWORD'] = password  # Установка пароля для подключения
		command = [
			'pg_restore',
			'-h', host,
			'-p', str(port),
			'-U', user,
			'-d', db_name,  # Имя базы данных, в которую будет восстановлено
		] + ([
			'-v' # Подробный вывод
		] if echo else []) + [
			backup_file # Путь к файлу резервной копии
		]

		try:
			subprocess.run(command, check=True)
			if echo:
				print(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Database '{db_name}' restored successfully from '{backup_file}'.")
		except subprocess.CalledProcessError as e:
			print(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Error during restore: {e}")
		finally:
			await conn.close()

	async def __aenter__(self):
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		pass
	