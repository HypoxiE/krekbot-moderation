try:
	import disnake
	from disnake.ext import commands
	from disnake.ext import tasks
	import requests
	import numpy as np
	import aiohttp
	#from colorthief import ColorThief
except:
	import pip

	pip.main(['install', 'disnake'])
	#pip.main(['install', 'matplotlib'])
	pip.main(['install', 'requests'])
	#pip.main(['install', 'Pillow'])
	pip.main(['install', 'numpy'])
	pip.main(['install', 'aiohttp'])
	#pip.main(['install', 'colorthief'])
	import disnake
	from disnake.ext import commands
	from disnake.ext import tasks
	import numpy as np
	import requests
	import aiohttp
	#from colorthief import ColorThief
import asyncio
import sys
import os
import copy
import datetime
import math
import random
import json
import shutil
from constants.global_constants import *
from data.secrets.TOKENS import TOKENS

import CoreMod


async def main():
	stop_event = asyncio.Event()
	sup_bot = None
	DataBase = None
	all_bots = []

	try:
		DataBase = await CoreMod.init_db()
		#sup_bot = CoreMod.MainBot(DataBase, stop_event)
		sup_bot = CoreMod.AnyBots(DataBase)
		all_bots = [sup_bot]

		#НЕ СМЕЙ РАСКОММЕНТИРОВАТЬ
		#await CoreMod.db_migration(DataBase)

		'''
		users = [
			DataBase.model_classes['staff_users'](id = 78173123),
			DataBase.model_classes['staff_users'](id = 6345345)
		]

		async with DataBase.session() as session:
			async with session.begin():
				#session.add_all(users)

				stmt = CoreMod.select(DataBase.model_classes['staff_users']).where(DataBase.model_classes['staff_users'].id == 78173123)
				result = (await session.execute(stmt)).scalars().all()
				for i in result:
					await session.delete(i)
		print(result)
		'''
		


		# Загрузка когов
		sup_bot.load_extension("cogs.resetsupcommands")
		sup_bot.load_extension("cogs.moderators")
		sup_bot.load_extension("cogs.users")
		sup_bot.load_extension("cogs.administrators")

		# Запуск монитора остановки и ботов
		monitor_task = asyncio.create_task(CoreMod.monitor_stop(stop_event, all_bots))
		bot_tasks = [
			asyncio.create_task(CoreMod.run_bot(sup_bot, TOKENS["KrekSupBot"], stop_event)),
		]

		await asyncio.gather(*bot_tasks, monitor_task)

	except KeyboardInterrupt:
		print(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Боты остановлены по запросу пользователя")
	except Exception as e:
		print(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Произошла критическая ошибка: {e}")
	finally:
		# Остановка всех ботов
		stop_event.set()
		for bot in all_bots:
			if not bot.is_closed():
				await bot.close()
		if DataBase is not None:
			await DataBase.close()

if __name__ == "__main__":
	asyncio.run(main())
