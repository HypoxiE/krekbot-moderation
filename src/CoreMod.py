import logging
logging.basicConfig(level=logging.INFO, force=True, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%d-%m-%Y %H:%M:%S")

import inspect
import disnake
from disnake.ext import commands
from disnake.ext import tasks
import asyncio
import sys
import os
import shutil
import datetime
from collections import Counter
from fnmatch import fnmatch
import traceback
import json
import re

from constants.global_constants import *
from libs.tokens_formatter import TOKENS
from database.db_classes import all_data as DataBaseClasses
from managers.DataBaseManager import DatabaseManager
from database.settings import config

from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable

import tldextract

logger = logging.getLogger(__name__)

class AnyBots(commands.Bot):
	logger = logging.getLogger(__name__)
	'''
	
	
	Any bot class


	'''
	def __init__(self, DataBaseManager):
		super().__init__(
			command_prefix="=",
			intents=disnake.Intents.all()
		)
		self.DataBaseManager = DataBaseManager
		self.constants = constants

	async def on_ready(self):
		self.krekchat = await self.fetch_guild(constants["krekchat"])
		self.logger.info(self.krekchat.name)
		self.sponsors = [disnake.utils.get(self.krekchat.roles, id=i) for i in constants["sponsors"]]
		self.text_mute = disnake.utils.get(self.krekchat.roles, id=constants["mutes"][0])
		self.voice_mute = disnake.utils.get(self.krekchat.roles, id=constants["mutes"][1])
		self.ban_role = disnake.utils.get(self.krekchat.roles, id=constants["ban_role"])
		self.me = disnake.utils.get(self.krekchat.roles, id=constants["me"])
		self.moder = disnake.utils.get(self.krekchat.roles, id=constants["moder"])
		self.curator = disnake.utils.get(self.krekchat.roles, id=constants["curator"])
		self.everyone = disnake.utils.get(self.krekchat.roles, id=constants["everyone"])
		self.staff = disnake.utils.get(self.krekchat.roles, id=constants["staff"])
		self.level_roles = [disnake.utils.get(self.krekchat.roles, id=i) for i in constants["level_roles"]]
		self.bots_talk_protocol_channel_id = constants["bots_talk_protocol_channel"]
		self.databases_backups_channel_id = constants["databases_backups_channel"]
		# lists
		self.moderators = [disnake.utils.get(self.krekchat.roles, id=i) for i in constants["moderators"]]
		self.hierarchy = [disnake.utils.get(self.krekchat.roles, id=i) for i in constants["hierarchy"]]
		# /lists
		await self.change_presence(status=disnake.Status.online, activity=disnake.Game("Работаю"))
		self.logger.info(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}::  KrekModBot activated")

	def TimeFormater(self, time_str: str = "", *,
					years: float = 0, months: float = 0, weeks: float = 0, days: float = 0, hours: float = 0, minutes: float = 0, seconds: float = 0,
					now_timestamp = None):
		"""
		Форматирует строку времени в timestamp и разложенное время
		Поддерживает форматы: 1d2h30m, 1д2ч30мин, 1.5d, 1 день 2 часа 30 минут и т.п.
		Возвращает объект класса FormatedTime
		"""

		class FormatedTime:
			def __init__(self, time_units):
				self.translator = {'years': 'лет', 'months': 'месяцев', 'weeks': 'недель', 'days': 'дней', 'hours': 'часов', 'minutes': 'минут', 'seconds': 'секунд'}

				delta = datetime.timedelta(
					weeks=time_units['weeks'],
					days=time_units['days'] + time_units['years'] * 365 + time_units['months'] * 30,
					hours=time_units['hours'],
					minutes=time_units['minutes'],
					seconds=time_units['seconds']
				)
				total_seconds = delta.total_seconds()

				minutes = total_seconds // 60
				seconds = total_seconds % 60
				hours, minutes = divmod(minutes, 60)
				days, hours = divmod(hours, 24)

				months = days // 30
				days = days % 30
				years = months // 12
				months = months % 12

				self.time_units = {
					'years': years,
					'months': months,
					'days': days,
					'hours': hours,
					'minutes': minutes,
					'seconds': seconds
				}

				self.future_time = 0
				if now_timestamp is None:
					self.future_time = datetime.datetime.now() + delta
				else:
					self.future_time = datetime.datetime.fromtimestamp(now_timestamp) + delta
				self.timestamp = self.future_time.timestamp()

			def __float__(self):
				return self.timestamp

			def __int__(self):
				return int(self.timestamp)

			def __repr__(self):
				return self.__str__() + f" [{self.timestamp}]"

			def __str__(self):
				if self.time_is_null():
					return "вечность"
				else:
					result = []
					for key, value in self.time_units.items():
						if value > 0:
							result.append(f"{int(value) if key != 'seconds' else round(value, 2)} {self.translator[key]}")

					return ", ".join(result)

			def time_is_null(self):
				return not any([i for i in self.time_units.values()])

			def to_dict(self):
				return self.time_units

		time_units = {'years': 0, 'months': 0, 'weeks': 0, 'days': 0, 'hours': 0, 'minutes': 0, 'seconds': 0}
		if any([years, months, weeks, days, hours, minutes, seconds]):
			time_units = {'years': years, 'months': months, 'weeks': weeks, 'days': days, 'hours': hours, 'minutes': minutes, 'seconds': seconds}

			return FormatedTime(time_units)
		else:
			time_str = time_str.lower().replace(' ', '').replace(',', '.')

			replacements = {
				# Русские
				'лет': 'years',
				'год': 'years',
				'мес': 'months',
				'нед': 'weeks',
				'дн': 'days',
				'д': 'days',
				'день': 'days',
				'дней': 'days',
				'дня': 'days',
				'ч': 'hours',
				'час': 'hours',
				'часов': 'hours',
				'часа': 'hours',
				'м': 'minutes',
				'мин': 'minutes',
				'минут': 'minutes',
				'минуты': 'minutes',
				'с': 'seconds',
				'сек': 'seconds',
				'секунд': 'seconds',
				'секунды': 'seconds',
				# Английские
				'y': 'years',
				'w': 'weeks',
				'd': 'days',
				'h': 'hours',
				'm': 'minutes',
				's': 'seconds',
				'c': 'seconds'
			}

			pattern = re.compile(r'(\d+(?:\.\d+)?)([a-zа-я]+)', re.IGNORECASE)

			def replacer(match):
				number, unit = match.groups()
				replacement = replacements.get(unit, unit)
				return f"{number}{replacement}"

			time_str = pattern.sub(replacer, time_str)

			pattern = r'(\d+(\.\d+)?)(years|months|weeks|days|hours|minutes|seconds)'
			matches = re.findall(pattern, time_str)

			for value, _, unit in matches:
				time_units[unit] += value

			return FormatedTime(time_units)

	async def bt_send(self, info: dict = {}):
		def get_all_keys(dct, keys_list=None):
			if keys_list is None:
				keys_list = []
			for key, value in dct.items():
				keys_list.append(key)
				if isinstance(value, dict):
					get_all_keys(value, keys_list)
			return keys_list

		krekchat = await self.fetch_guild(self.krekchat.id)
		bt_channel = await krekchat.fetch_channel(self.bots_talk_protocol_channel_id)
		if not isinstance(bt_channel, disnake.TextChannel):
			raise ValueError("bt_channel не найден")

		punishment_keys = ['type', 'options', 'severity', 'member', 'moderator']
		complaint_keys = ['type', 'options', 'accepted', 'attack_member', 'defence_member', 'moderator']
		unpunishment_keys = ['type', 'options', 'severity', 'member']
		if not 'type' in info:
			await bt_channel.send(f"<@479210801891115009> Передан запрос без типа :: bt_send\n {traceback.extract_stack()[-2]}")
			return 1
		if info['type'] == "punishment":
			if get_all_keys(info) != punishment_keys:
				if len(get_all_keys(info)) != punishment_keys:
					await bt_channel.send(f"<@479210801891115009> Требуется {len(punishment_keys)}, а принято {len(get_all_keys(info))} ключей для punishment :: bt_send\n {traceback.extract_stack()[-2]}")
				else:
					await bt_channel.send(f"<@479210801891115009> Требуются ключи {punishment_keys}, а приняты {get_all_keys(info)} для punishment :: bt_send\n {traceback.extract_stack()[-2]}")
				return 1
		elif info['type'] == "complaint":
			if get_all_keys(info) != complaint_keys:
				if len(get_all_keys(info)) != complaint_keys:
					await bt_channel.send(f"<@479210801891115009> Требуется {len(complaint_keys)}, а принято {len(get_all_keys(info))} ключей для complaint :: bt_send\n {traceback.extract_stack()[-2]}")
				else:
					await bt_channel.send(f"<@479210801891115009> Требуются ключи {complaint_keys}, а приняты {get_all_keys(info)} для complaint :: bt_send\n {traceback.extract_stack()[-2]}")
				return 1
		elif info['type'] == "unpunishment":
			if get_all_keys(info) != unpunishment_keys:
				if len(get_all_keys(info)) != unpunishment_keys:
					await bt_channel.send(f"<@479210801891115009> Требуется {len(unpunishment_keys)}, а принято {len(get_all_keys(info))} ключей для unpunishment :: bt_send\n {traceback.extract_stack()[-2]}")
				else:
					await bt_channel.send(f"<@479210801891115009> Требуются ключи {unpunishment_keys}, а приняты {get_all_keys(info)} для unpunishment :: bt_send\n {traceback.extract_stack()[-2]}")
				return 1
		else:
			await bt_channel.send(f"<@479210801891115009> Передан неизвестный тип запроса {info['type']} :: bt_send\n {traceback.extract_stack()[-2]}")
			return 1

		
		
		info["sender"] = "ModBot"
		await bt_channel.send(json.dumps(info))
		return 0

	class ErrEmbed(disnake.Embed):
		def __init__(self, **kwargs):
			color = kwargs.pop('color', 0xff0000)
			super().__init__(color = color, **kwargs)

	class AnswEmbed(disnake.Embed):
		def __init__(self, **kwargs):
			color = kwargs.pop('color', 0x008000)
			super().__init__(color = color, **kwargs)

	class WarnEmbed(disnake.Embed):
		def __init__(self, **kwargs):
			color = kwargs.pop('color', 0xFFFF00)
			super().__init__(color = color, **kwargs)

	class SuccessEmbed(disnake.Embed):
		def __init__(self, **kwargs):
			color = kwargs.pop('color', 0x008000)
			super().__init__(color = color, **kwargs)

class MainBot(AnyBots):
	'''
	

	Main bot class


	'''
	def __init__(self, DataBase, stop_event, task_start = True):
		super().__init__(DataBase)
		self.stop_event = stop_event
		self.ready_once = asyncio.Event()
		self.task_start = task_start

	async def on_ready(self):
		await super().on_ready()

		if not self.ready_once.is_set():
			self.loops = [self.CheckDataBases, self.MakeBackups, self.SendingDeferredMessages, self.watchdog]
			
			if self.task_start:
				for loop in self.loops:
					loop.start()

			else:
				pass

			self.ready_once.set()

	async def BotOff(self):
		if self.task_start and self.ready_once.is_set():
			for loop in self.loops:
				loop.cancel()

		self.stop_event.set()

	# async def on_disconnect(self):
	# 	if self.stop_event.is_set():
	# 		pass
	# 	else:
	# 		self.logger.error(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Соединение с дискордом разорвано")
	# 		await self.BotOff()

	@staticmethod
	def catch_exceptions(func):
		import functools, traceback
		@functools.wraps(func)
		async def wrapper(*args, **kwargs):
			try:
				return await func(*args, **kwargs)
			except Exception:
				logger.exception(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: [ERROR] {func.__name__}:\n{traceback.format_exc()}")
		return wrapper

	@tasks.loop(seconds=30)
	@catch_exceptions
	async def watchdog(self):

		for loop in self.loops:
			if loop == self.watchdog:
				continue

			if not loop.is_running():
				self.logger.error(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Обнаружено падение {loop.coro.__name__}, перезапуск цикла...")
				loop.cancel()
		

	
	@tasks.loop(seconds=60)
	@catch_exceptions
	async def SendingDeferredMessages(self):
		async with self.DataBaseManager.session() as session:
			async with session.begin():
				stmt = self.DataBaseManager.select(self.DataBaseManager.model_classes['scheduled_messages']).where(
					self.DataBaseManager.model_classes['scheduled_messages'].timestamp - datetime.datetime.now().timestamp() <= 0
				).with_for_update()
				messages = (await session.execute(stmt)).scalars().all()

				for message in messages:
					webhook = await self.fetch_webhook(message.webhook_id)
					await webhook.send(**(await message.parse_message(self)))

					await session.delete(message)

	@tasks.loop(seconds=3600)
	@catch_exceptions
	async def MakeBackups(self):
		backup_file = await self.DataBaseManager.pg_dump()

		krekchat = await self.fetch_guild(self.krekchat.id)
		backups_channel = await krekchat.fetch_channel(self.databases_backups_channel_id)
		if not isinstance(backups_channel, disnake.TextChannel):
			raise ValueError("backups_channel не найден")
		await backups_channel.send(content=f"Бэкап бд за {datetime.datetime.now()}:", file=disnake.File(backup_file))

	@tasks.loop(seconds=60)
	@catch_exceptions
	async def CheckDataBases(self):
		self.krekchat = await self.fetch_guild(self.krekchat.id)
		members = [i async for i in self.krekchat.fetch_members(limit=None)]
		textmute = {'mute': [], 'unmute': list(filter(lambda m: self.text_mute in m.roles, members))}
		voicemute = {'mute': [], 'unmute': list(filter(lambda m: self.voice_mute in m.roles, members))}
		ban = {'ban': [], 'unban': list(filter(lambda m: self.ban_role in m.roles, members))}
		#муты
		async with self.DataBaseManager.session() as session:
			async with session.begin():
				stmt = self.DataBaseManager.delete(self.DataBaseManager.model_classes['punishment_mutes_text']).where(
					self.DataBaseManager.and_(
						self.DataBaseManager.model_classes['punishment_mutes_text'].time_warn - datetime.datetime.now().timestamp() <= 0,
						self.DataBaseManager.model_classes['punishment_mutes_text'].time_warn != None
					)
				)
				await session.execute(stmt)

				stmt = self.DataBaseManager.select(self.DataBaseManager.model_classes['punishment_mutes_text']).where(
					self.DataBaseManager.or_(
						self.DataBaseManager.and_(
							self.DataBaseManager.model_classes['punishment_mutes_text'].time_end - datetime.datetime.now().timestamp() <= 0,
							self.DataBaseManager.model_classes['punishment_mutes_text'].time_warn == None
						),
						self.DataBaseManager.and_(
							self.DataBaseManager.model_classes['punishment_mutes_text'].time_end != None
						)
					)
				).with_for_update()
				result = (await session.execute(stmt)).scalars().all()

				for penalt in result:
					member = disnake.utils.get(members, id=penalt.user_id)

					if not member:
						continue

					if penalt.time_warn is None and penalt.time_end-datetime.datetime.now().timestamp()<=0:
						penalt.time_end = None
						penalt.time_warn = self.TimeFormater("30d").timestamp


					if (not penalt.time_warn is None) and (not penalt.time_end is None):
						penalt.time_end = None

					if not penalt.time_end is None:
						if member in textmute['unmute']:
							stmt = self.DataBaseManager.select(self.DataBaseManager.model_classes['punishment_mutes_text']).where(
								self.DataBaseManager.and_(
									self.DataBaseManager.model_classes['punishment_mutes_text'].user_id == member.id,
									self.DataBaseManager.model_classes['punishment_mutes_text'].time_end != None
								)
							)
							member_pens = (await session.execute(stmt)).scalars().all()
							if len(member_pens)>0:
								textmute['unmute'].remove(member)
						if not member in textmute['mute']:
							textmute['mute'].append(member)

			for member in textmute['mute']:
				await member.add_roles(self.text_mute)
			for member in textmute['unmute']:
				await member.remove_roles(self.text_mute)

			async with session.begin():
				stmt = self.DataBaseManager.delete(self.DataBaseManager.model_classes['punishment_mutes_voice']).where(
					self.DataBaseManager.and_(
						self.DataBaseManager.model_classes['punishment_mutes_voice'].time_warn - datetime.datetime.now().timestamp() <= 0,
						self.DataBaseManager.model_classes['punishment_mutes_voice'].time_warn != None
					)
				)
				await session.execute(stmt)

				stmt = self.DataBaseManager.select(self.DataBaseManager.model_classes['punishment_mutes_voice']).where(
					self.DataBaseManager.or_(
						self.DataBaseManager.and_(
							self.DataBaseManager.model_classes['punishment_mutes_voice'].time_end - datetime.datetime.now().timestamp() <= 0,
							self.DataBaseManager.model_classes['punishment_mutes_voice'].time_warn == None
						),
						self.DataBaseManager.and_(
							self.DataBaseManager.model_classes['punishment_mutes_voice'].time_end != None
						)
					)
				).with_for_update()
				result = (await session.execute(stmt)).scalars().all()

				for penalt in result:
					member = disnake.utils.get(members, id=penalt.user_id)

					if not member:
						continue

					if penalt.time_warn is None and penalt.time_end - datetime.datetime.now().timestamp() <= 0:
						penalt.time_end = None
						penalt.time_warn = self.TimeFormater("30d").timestamp


					if (not penalt.time_warn is None) and (not penalt.time_end is None):
						penalt.time_end = None

					if not penalt.time_end is None:
						if member in voicemute['unmute']:
							stmt = self.DataBaseManager.select(self.DataBaseManager.model_classes['punishment_mutes_voice']).where(
								self.DataBaseManager.and_(
									self.DataBaseManager.model_classes['punishment_mutes_voice'].user_id == member.id,
									self.DataBaseManager.model_classes['punishment_mutes_voice'].time_end != None
								)
							)
							member_pens = (await session.execute(stmt)).scalars().all()
							if len(member_pens)>0:
								voicemute['unmute'].remove(member)
						if not member in voicemute['mute']:
							voicemute['mute'].append(member)

			for member in voicemute['mute']:
				await member.add_roles(self.voice_mute)
				await member.move_to(None)
			for member in voicemute['unmute']:
				await member.remove_roles(self.voice_mute)
			#/муты

			#баны
			async with session.begin():
				stmt = self.DataBaseManager.select(self.DataBaseManager.model_classes['punishment_bans']).where(self.DataBaseManager.model_classes['punishment_bans'].time_end != None).with_for_update()
				result = (await session.execute(stmt)).scalars().all()

				for penalt in result:
					member = disnake.utils.get(members, id=penalt.user_id)

					if not member:
						continue

					if penalt.time_end - datetime.datetime.now().timestamp() <= 0:
						penalt.time_end = None

					if penalt.time_end != None:
						if member in ban['unban']:
							stmt = self.DataBaseManager.select(self.DataBaseManager.model_classes['punishment_bans']).where(
								self.DataBaseManager.and_(
									self.DataBaseManager.model_classes['punishment_bans'].user_id == member.id,
									self.DataBaseManager.model_classes['punishment_bans'].time_end != None
								)
							)
							member_pens = (await session.execute(stmt)).scalars().all()
							if len(member_pens)>0:
								ban['unban'].remove(member)
						if not member in ban['ban']:
							ban['ban'].append(member)

			async with session.begin():
				stmt = self.DataBaseManager.select(self.DataBaseManager.model_classes['punishment_perms'])
				result = (await session.execute(stmt)).scalars().all()
				for penalt in result:
					member = disnake.utils.get(members, id=penalt.user_id)

					if not member:
						continue

					if member in ban['unban']:
						stmt = self.DataBaseManager.select(self.DataBaseManager.model_classes['punishment_perms']).where(
							self.DataBaseManager.model_classes['punishment_perms'].user_id == member.id
						)
						member_perms = (await session.execute(stmt)).scalars().all()
						if len(member_perms):
							ban['unban'].remove(member)
					if not member in ban['ban']:
						ban['ban'].append(member)

			for member in ban['ban']:
				await member.add_roles(self.ban_role)
				await member.move_to(None)
			for member in ban['unban']:
				await member.remove_roles(self.ban_role)
			#/баны

			#преды
			async with session.begin():
				stmt = self.DataBaseManager.delete(self.DataBaseManager.model_classes['punishment_warns']).where(self.DataBaseManager.model_classes['punishment_warns'].time_warn - datetime.datetime.now().timestamp() <= 0)
				await session.execute(stmt)
				stmt = self.DataBaseManager.delete(self.DataBaseManager.model_classes['punishment_reprimands']).where(self.DataBaseManager.model_classes['punishment_reprimands'].time_warn - datetime.datetime.now().timestamp() <= 0)
				await session.execute(stmt)
			#/преды

	async def on_button_click(self, inter):
		if not inter.response.is_done():...
			#await inter.response.send_message(embed=self.ErrEmbed(description=f'Ответ не был отправлен, возможно, кнопка перестала действовать'), ephemeral=True)

	async def on_message(self, message):
		
		if message.author.bot or not self.task_start or not self.ready_once.is_set():
			return

		if message.author.id == 479210801891115009 and message.content == "botsoff":
			await message.reply(embed=self.AnswEmbed(description=f'Бот отключён', colour=0xff9900))
			await self.BotOff()
			return
		if type(message.channel).__name__!="DMChannel" and re.match(r"^⚠️?жалоба-от-(.+)-на-(.+)$", message.channel.name):
			log_reports = disnake.utils.get(message.guild.channels, id=1242373230384386068)
			if isinstance(log_reports, disnake.TextChannel):
				files=[]
				for att in message.attachments:
					files = files + [await att.to_file()]
				log_mess = await log_reports.send(f"Чат: `{message.channel.name}`({message.channel.id}).\n"
												f"Автор: `{message.author.name} ({message.author.id})`\n" +
												(f"Сообщение: ```{message.content}```\n" if message.content else ""),
												files = files)
				return

		async with self.DataBaseManager.session() as session:
			if (await self.DataBaseManager.model_classes['staff_users'].is_admin_or_moder_by_id(message.author.id, self.DataBaseManager, session)):
				return

		def extract_root_domain(url):
			ext = tldextract.extract(url)
			if not ext.domain or not ext.suffix:
				return None
			return f"{ext.domain}.{ext.suffix}".lower()

		log = disnake.utils.get(message.guild.channels, id=893065482263994378)
		if not isinstance(log, disnake.TextChannel):
			raise TypeError("Проверь канал логов для сомнительных ссылок")

		url_pattern = re.compile(r'https?://[^\s]+')
		links = re.findall(url_pattern, message.content)
		аllowed_domains_model = self.DataBaseManager.model_classes['аllowed_domains']
		async with self.DataBaseManager.session() as session:
			for link in links:
				root_domain = extract_root_domain(link)
				stmt = self.DataBaseManager.select(аllowed_domains_model).where(аllowed_domains_model.domain == root_domain)
				link_in_wl = (await session.execute(stmt)).scalars().first()

				if link_in_wl is None:
					await log.send(f"{message.author.mention}({message.author.id}) отправил в чат {message.channel.mention} сомнительную ссылку, которой нет в вайлисте:```{message.content}```")
					mess = await message.reply(embed=self.ErrEmbed(description=f'Этой ссылки нет в белом списке, но заявка на добавление уже отправлена. Если это срочно, свяжитесь с разработчиком или модераторами.'))
					await message.delete()
					await asyncio.sleep(20)
					await mess.delete()
					return

		message_words = message.content.replace("/", " ").split(" ")
		if "discord.gg" in message_words:
			for i in range(len(message_words)):
				if message_words[i]=="discord.gg" and not message.author.bot:
					try:
						inv = await self.fetch_invite(url = "https://discord.gg/"+message_words[i+1])
						if (isinstance(inv.guild, disnake.PartialInviteGuild) or isinstance(inv.guild, disnake.Guild)) and inv.guild.id != 490445877903622144:
							await log.send(f"{message.author.mention}({message.author.id}) отправил в чат {message.channel.mention} сомнительную ссылку на сервер '{inv.guild.name}':```{message.content}```")
							mess = await message.reply(embed=self.ErrEmbed(description=f'Ссылки-приглашения запрещены!', colour=0xff9900))
							await message.delete()
							await asyncio.sleep(20)
							await mess.delete()
							break
					except disnake.errors.NotFound:
						await log.send(f"{message.author.mention}({message.author.id}) отправил в чат {message.channel.mention} [сомнительную ссылку]({message.jump_url}) на неизвестный сервер:```{message.content}```")


	

async def init_db():
	DataBaseEngine = create_async_engine(
		config.Settings().DB_URL,
		pool_size=20,
		max_overflow=10,
		pool_recycle=300,
		pool_pre_ping=True,
		#echo=True,
	)
	async with DataBaseEngine.begin() as conn:
		await conn.run_sync(DataBaseClasses['base'].metadata.create_all)
	
	return DatabaseManager(DataBaseEngine, DataBaseClasses)

async def run_bot(bot, token, stop_event):
	try:
		await bot.start(token)
	except Exception as e:
		logger.exception(f"Бот {bot.user.name if hasattr(bot, 'user') else 'Unknown'} упал с ошибкой: {e}")
		stop_event.set()  # Сигнализируем об остановке

async def monitor_stop(stop_event, bots):
	await stop_event.wait()
	logger.info(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Получен сигнал остановки, завершаю всех ботов...")

	for bot in bots:
		if not bot.is_closed():
			try:
				await bot.close()
			except Exception as e:
				logger.exception(f"Ошибка при закрытии бота: {e}")

	await asyncio.sleep(0.1)


async def main():
	stop_event = asyncio.Event()
	DataBase = None
	all_bots = []
	bot = None

	try:
		DataBase = await init_db()

		# Инициализация ботов
		bot = MainBot(DataBase, stop_event)
		all_bots = [bot]

		# Загрузка когов
		bot.load_extension("cogs.users")
		bot.load_extension("cogs.moderators")
		bot.load_extension("cogs.administrators")

		# Запуск монитора остановки и ботов
		monitor_task = asyncio.create_task(monitor_stop(stop_event, all_bots))
		bot_tasks = [
			asyncio.create_task(run_bot(bot, TOKENS["KrekModBot"], stop_event))
		]

		await asyncio.gather(*bot_tasks, monitor_task)

	except KeyboardInterrupt:
		logger.info("Боты остановлены по запросу пользователя")
	except Exception as e:
		logger.exception(f"Произошла критическая ошибка: {e}")
	finally:
		if bot is not None:
			await bot.BotOff()

		for bot in all_bots:
			if not bot.is_closed():
				await bot.close()

		if DataBase is not None:
			await DataBase.close()

		current_task = asyncio.current_task()
		pending = [t for t in asyncio.all_tasks() if t is not current_task and not t.done()]
		for task in pending:
			task.cancel()
		await asyncio.gather(*pending, return_exceptions=True)

		await asyncio.sleep(0.1)

if __name__ == "__main__":
	asyncio.run(main())