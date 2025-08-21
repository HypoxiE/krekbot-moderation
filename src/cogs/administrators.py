import re
import disnake
from disnake.ext import commands
from disnake.ext import tasks
import requests
import numpy as np

import asyncio
import sys
import os
import copy
import datetime
import math
import random
import json
import shutil


def setup(bot):
	bot.add_cog(AdminModule(bot))

class AdminModule(commands.Cog):
	def __init__(self, client):
		self.client = client
		self.DataBaseManager = client.DataBaseManager

	@commands.Cog.listener()
	async def on_ready(self):
		print(f'KrekModBot admin module activated')

	@commands.slash_command(name="bot_mod_off")
	async def BotModOff(self, ctx: disnake.ApplicationCommandInteraction):
		if isinstance(ctx.author, disnake.User):
			await ctx.send(embed=self.client.ErrEmbed(description=f'Невозможно в личных сообщениях'), ephemeral=True)
			return
		
		if self.client.me in ctx.author.roles:
			await ctx.send(embed=self.client.SuccessEmbed(description=f'Бот отключён'), ephemeral=True)
			await self.client.BotOff()
		else:
			await ctx.send(embed=self.client.ErrEmbed(description=f'Не допустимо'), ephemeral=True)

	@commands.slash_command(name="очистка", administrator=True)
	async def clear(self, ctx: disnake.AppCmdInter, count: int):
		if isinstance(ctx.author, disnake.User):
			await ctx.send(embed=self.client.ErrEmbed(description=f'Невозможно в личных сообщениях'), ephemeral=True)
			return
		if isinstance(ctx.channel, (disnake.DMChannel, disnake.GroupChannel, disnake.PartialMessageable)):
			await ctx.send(embed=self.client.ErrEmbed(description=f'Неверный тип канала!'), ephemeral=True)
			return
		
		if self.client.me in ctx.author.roles:
			await ctx.channel.purge(limit=count)
			await ctx.send(embed = self.client.SuccessEmbed(description = f'очищено {count} сообщений!', colour = 0xff9900), ephemeral=True)
		else:
			await ctx.send(embed = self.client.ErrEmbed(description = f'Ты чего удумал?', colour = 0xff9900), ephemeral=True)

	@commands.slash_command(description="Позволяет менять/создавать/удалять ветви", name="правка_ветви", administrator=True)
	async def edit_branch(self, ctx: disnake.AppCmdInter, purpose: str = commands.Param(description="Укажите цель этой ветки (например, \"модерация\" или \"администрация\")", name="цель", default=None),
													  layer: int = commands.Param(description="Укажите слой этой ветки (у ролей нижних слоёв есть власть над верхними)", name="слой", default=None),
													  branchid: int = commands.Param(description="Необходимо для изменения уже существующей ветви", name="id", default=None),
													  is_admin: bool = commands.Param(description="Имеют ли пользователи в этой роли права администратора? *(только при создании)", name="администратор", default=False),
													  is_moder: bool = commands.Param(description="Имеют ли пользователи в этой роли права модератора? *(только при создании)", name="модератор", default=False),
													  delete_branch: str = commands.Param(description="Вы уверены, что хотите удалить ветвь? Для подтверждения впишите \"уверен\"", name="удаление", default=None)):
		if isinstance(ctx.author, disnake.User):
			await ctx.send(embed=self.client.ErrEmbed(description=f'Невозможно в личных сообщениях'), ephemeral=True)
			return
		
		if not self.client.me in ctx.author.roles:
			await ctx.send(embed = self.client.ErrEmbed(description = f'Недостаточно прав', colour = 0xff9900), ephemeral=True)
			return 1

		async with self.DataBaseManager.session() as session:

			if delete_branch == "уверен":
				if branchid is None:
					await ctx.send(embed = self.client.ErrEmbed(description = f'Для удаления ветки необходимо указать её id', colour = 0xff9900))
					return 1
				
				async with session.begin():
					stmt = self.DataBaseManager.delete(self.DataBaseManager.models['staff_branches'].m).where(self.DataBaseManager.models['staff_branches'].m.id == branchid)
					await session.execute(stmt)
					await ctx.send(embed = self.client.SuccessEmbed(description = f'Ветка {branchid} успешно удалена', colour = 0xff9900))
					return 0

			if branchid is None:
				if layer is None or purpose is None:
					await ctx.send(embed = self.client.ErrEmbed(description = f'Для создания роли необходимо ввести все данные', colour = 0xff9900))
					return 1
				async with session.begin():
					new_branch = self.DataBaseManager.models['staff_branches'].m(layer = layer, purpose = purpose, is_admin = is_admin, is_moder = is_moder)
					session.add(new_branch)
				await ctx.send(embed = self.client.SuccessEmbed(description = f'Ветвь \"{purpose}\" успешно создана. Её новый id: {new_branch.id}', colour = 0xff9900))
				return 0
			else:
				async with session.begin():
					branch = await session.get(self.DataBaseManager.models['staff_branches'].m, branchid, with_for_update = True)
					if branch is None:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Ветви с таким идентификатором пока не существует', colour = 0xff9900))
						return 1

					else:
						if purpose is None and layer is None:
							await ctx.send(embed = self.client.ErrEmbed(description = f'Для изменения ветви необходимы новые значения', colour = 0xff9900))
							return 1

						if not purpose is None:
							branch.purpose = purpose

						if not layer is None:
							branch.layer = layer

						await ctx.send(embed = self.client.SuccessEmbed(description = f'Ветвь \"{branch.purpose}\"({branch.id}) успешно изменена', colour = 0xff9900))
						return 0
						

	@commands.slash_command(description="Позволяет менять/создавать/удалять роли в системе персонала", name="правка_роли", administrator=True)
	async def edit_role(self, ctx: disnake.AppCmdInter, roleid_str: str = commands.Param(description="Укажите id роли (используются идентификаторы дискорда)", name="id"),
													   staffsalary: int = commands.Param(description="Укажите зарплату этой роли", name="зарплата", default=0),
													   branchid: int = commands.Param(description="Укажите id ветви для этой роли *(только при создании)", name="ветвь", default=None),
													   layer: int = commands.Param(description="Укажите слой этой роли в ветке (у ролей нижних слоёв есть власть над верхними)", name="слой", default=None),
													   delete_role: str = commands.Param(description="Вы уверены, что хотите удалить роль из системы? Для подтверждения впишите \"уверен\"", name="удаление", default=None),):
		if isinstance(ctx.author, disnake.User):
			await ctx.send(embed=self.client.ErrEmbed(description=f'Невозможно в личных сообщениях'), ephemeral=True)
			return
		
		if not self.client.me in ctx.author.roles:
			await ctx.send(embed = self.client.ErrEmbed(description = f'Недостаточно прав', colour = 0xff9900), ephemeral=True)
			return 1

		roleid = int(roleid_str)

		staff_roles_model = self.DataBaseManager.models['staff_roles'].m
		async with self.DataBaseManager.session() as session:

			if delete_role == "уверен":
				async with session.begin():
					stmt = self.DataBaseManager.delete(staff_roles_model).where(staff_roles_model.id == roleid)
					await session.execute(stmt)
					await ctx.send(embed = self.client.SuccessEmbed(description = f'Роль <@&{roleid}> успешно удалена из системы', colour = 0xff9900))
					return 0

			async with session.begin():
				role = await session.get(staff_roles_model, roleid, with_for_update = True)
				if not role is None:
					if staffsalary != 0:
						role.staff_salary = staffsalary
						await ctx.send(embed = self.client.SuccessEmbed(description = f'Зарплата роли <@&{roleid}> успешно изменена на {staffsalary}', colour = 0xff9900))
						return 0
					elif not layer is None:
						role.layer = layer
						await ctx.send(embed = self.client.SuccessEmbed(description = f'Слой роли <@&{roleid}> успешно изменён на {layer}', colour = 0xff9900))
						return 0
					else:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Для изменения существующей роли необходимо ввести новые параметры: layer или staffsalary', colour = 0xff9900))
						return 1
				else:
					if branchid is None:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Для внесения этой роли в систему необходимо указать id ветви', colour = 0xff9900))
						return 1
					if layer is None:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Для внесения этой роли в систему необходимо указать слой роли', colour = 0xff9900))
						return 1
					branch = await session.get(self.DataBaseManager.models['staff_branches'].m, branchid)
					if branch is None:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Ветви с таким id пока не существует', colour = 0xff9900))
						return 1
					role = staff_roles_model(id = roleid, staff_salary = staffsalary, branch_id = branchid, layer = layer)
					session.add(role)
					await ctx.send(embed = self.client.SuccessEmbed(description = f'Роль <@&{roleid}> успешно добавлена в ветвь {branchid}', colour = 0xff9900))
					return 0

	@commands.slash_command(description="Позволяет создавать/удалять пользователей в системе персонала", name="правка_пользователя", administrator=True)
	async def edit_member(self, ctx: disnake.AppCmdInter, userid_str: str = commands.Param(description="Укажите id пользователя (используются идентификаторы дискорда)", name="id"),
														  delete_user: str = commands.Param(description="Вы уверены, что хотите удалить пользователя из системы? Для подтверждения впишите \"уверен\"", name="удаление", default=None)):
		if isinstance(ctx.author, disnake.User):
			await ctx.send(embed=self.client.ErrEmbed(description=f'Невозможно в личных сообщениях'), ephemeral=True)
			return
		
		if not self.client.me in ctx.author.roles:
			await ctx.send(embed = self.client.ErrEmbed(description = f'Недостаточно прав', colour = 0xff9900), ephemeral=True)
			return 1

		userid = int(userid_str)

		staff_users_model = self.DataBaseManager.models['staff_users'].m
		async with self.DataBaseManager.session() as session:

			if delete_user == "уверен":
				async with session.begin():
					stmt = self.DataBaseManager.delete(staff_users_model).where(staff_users_model.id == userid)
					await session.execute(stmt)
					await ctx.send(embed = self.client.SuccessEmbed(description = f'Пользователь <@{userid}> успешно удален из системы', colour = 0xff9900))
				member = await self.client.krekchat.fetch_member(userid)
				await member.remove_roles(self.client.staff)
				return 0

			async with session.begin():
				user = await session.get(staff_users_model, userid, with_for_update = True)
				if user is None:
					member = await self.client.krekchat.fetch_member(userid)
					await member.add_roles(self.client.staff)
					user = staff_users_model(id = userid)
					session.add(user)
					await ctx.send(embed = self.client.SuccessEmbed(description = f'Пользователь <@{userid}> успешно добавлен в систему', colour = 0xff9900))
					return 0
				else:
					await ctx.send(embed = self.client.ErrEmbed(description = f'Пользователь <@{userid}> уже есть в системе', colour = 0xff9900))
					return 1
		
	@commands.slash_command(description="!!ВАЖНО!! ИСПОЛЬЗОВАНИЕ ТОЛЬКО В ЭКСТРЕННЫХ СЛУЧАЯХ! Назначает пользователей на роль", name="назначить_пользователя", administrator=True)
	async def appoint_member(self, ctx: disnake.AppCmdInter, userid_str: str = commands.Param(description="Укажите id пользователя (используются идентификаторы дискорда)", name="пользователь"),
															roleid_str: str = commands.Param(description="Укажите id роли (используются идентификаторы дискорда)", name="роль"),
															description: str = commands.Param(description="Описание", name="описание", default=None)):
		if isinstance(ctx.author, disnake.User):
			await ctx.send(embed=self.client.ErrEmbed(description=f'Невозможно в личных сообщениях'), ephemeral=True)
			return

		if not self.client.me in ctx.author.roles:
			await ctx.send(embed = self.client.ErrEmbed(description = f'Недостаточно прав', colour = 0xff9900), ephemeral=True)
			return 1

		userid = int(userid_str)
		roleid = int(roleid_str)

		async with self.DataBaseManager.session() as session:
			async with session.begin():

				user = await session.get(self.DataBaseManager.model_classes['staff_users'], userid)
				if user is None:
					user = self.DataBaseManager.model_classes['staff_users'](id = userid)
					session.add(user)
					await session.flush()
				user_role = await self.DataBaseManager.model_classes['staff_users_roles'].create_with_auto_branch(session, user_id = userid, role_id = roleid, description = description)
				session.add(user_role)
				await ctx.send(embed = self.client.SuccessEmbed(description = f'Пользователю <@{userid}> успешно назначена роль <@&{roleid}>. \n```diff\n- Эта функция не выдаёт роли автоматически, поэтому требуется выдача вручную.```', colour = 0xff9900))
				return 0
			
	@commands.slash_command(name="запланировать_сообщение", description="Позволяет запланировать отправку анонсов и других сообщений")
	async def schedule_message(self, ctx: disnake.AppCmdInter,
							message_id: str = commands.Param(description="Укажите id сообщения, которое будет отложено", name="сообщение"),
							webhook_link: str = commands.Param(description="Укажите ссылку на вебхук, от которого будет отправлено сообщение", name="вебхук"),
							timestamp: int = commands.Param(description="Временная метка для отправки сообщения", name="таймстамп", default=None)):
		
		await ctx.response.defer()
		
		def extract_webhook_id(webhook_url: str) -> int | None:
			pattern = r"^https:\/\/(?:canary\.|ptb\.)?discord(?:app)?\.com\/api\/webhooks\/(\d+)\/[\w\-]+$"
			match = re.match(pattern, webhook_url)
			if match:
				return int(match.group(1))
			return None
		
		if webhook_link is None:
			webhook_id = None
		else:
			webhook_id = extract_webhook_id(webhook_link)
			if webhook_id is None:
				await ctx.edit_original_response(embed = self.client.ErrEmbed(description = f'Некорректная ссылка'))
				return 1
		
		async with self.DataBaseManager.session() as session:
			async with session.begin():
				if not (await self.DataBaseManager.model_classes['staff_users'].is_admin_or_moder_by_id(ctx.author.id, self.DataBaseManager, session, is_admin=True, is_moder=False)):
					await ctx.edit_original_response(embed = self.client.ErrEmbed(description = f'У вас недостаточно полномочий, чтобы оставлять отложенные сообщения.'))
					return 1
				else:
					scheduled_message_model = self.DataBaseManager.model_classes['scheduled_messages']
					message = scheduled_message_model(source_channel_id=ctx.channel.id, source_message_id=int(message_id), webhook_id=webhook_id, timestamp=timestamp)
					session.add(message)

					await ctx.edit_original_response(embed = self.client.SuccessEmbed(description = f'Сообщение будет отправлено <t:{timestamp}:F>! Текст сообщения:', colour = 0xff9900))
					mgs_parsed = await message.parse_message(self.client, preview=True)
					await ctx.send(**mgs_parsed)
					return 0
