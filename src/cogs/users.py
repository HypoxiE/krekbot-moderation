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
	bot.add_cog(UIModule(bot))

class UIModule(commands.Cog):
	def __init__(self, client):
		self.client = client
		self.DataBaseManager = self.client.DataBaseManager

	@commands.Cog.listener()
	async def on_ready(self):
		print(f'KrekModBot UI module activated')

	@commands.slash_command(description="Показывает действительные наказания пользователя", name="наказания")
	async def penalties(self, ctx: disnake.AppCmdInter, member: disnake.Member = None):
		models = self.client.DataBaseManager.model_classes
		if not member:
			member = ctx.author
		embed =  disnake.Embed(title="Наказания", description = f"{member.mention}", colour = 0x008000)
		embed.set_thumbnail(url=member.avatar)

		async with self.DataBaseManager.session() as session:
			async with session.begin():
				stmt = self.DataBaseManager.select(models['punishment_mutes_text']).where(models['punishment_mutes_text'].user_id == member.id)
				result = (await session.execute(stmt)).scalars().all()
				stmt = self.DataBaseManager.select(models['punishment_mutes_voice']).where(models['punishment_mutes_voice'].user_id == member.id)
				result += (await session.execute(stmt)).scalars().all()
				stmt = self.DataBaseManager.select(models['punishment_bans']).where(models['punishment_bans'].user_id == member.id)
				result += (await session.execute(stmt)).scalars().all()
				stmt = self.DataBaseManager.select(models['punishment_warns']).where(models['punishment_warns'].user_id == member.id)
				result += (await session.execute(stmt)).scalars().all()
				stmt = self.DataBaseManager.select(models['punishment_reprimands']).where(models['punishment_reprimands'].user_id == member.id)
				result += (await session.execute(stmt)).scalars().all()
				stmt = self.DataBaseManager.select(models['punishment_perms']).where(models['punishment_perms'].user_id == member.id)
				result += (await session.execute(stmt)).scalars().all()

				result = sorted(result, key=lambda a: a.time_begin, reverse=True)

		for penalt in result:
			match penalt.get_table_name():
				case 'punishment_mutes_text':
					embed.add_field(name = f"Текстовый мут", value = f"Заканчивается {'<t:{time_end}:f>'.format(time_end = int(penalt.time_end)) if penalt.time_warn is None else '<t:{time_warn}:f> (предупреждение)'.format(time_warn = int(penalt.time_warn))}\n```{penalt.reason}```", inline = False)
				case 'punishment_mutes_voice':
					embed.add_field(name = f"Голосовой мут", value = f"Заканчивается {'<t:{time_end}:f>'.format(time_end = int(penalt.time_end)) if penalt.time_warn is None else '<t:{time_warn}:f> (предупреждение)'.format(time_warn = int(penalt.time_warn))}\n```{penalt.reason}```", inline = False)
				case 'punishment_bans':
					embed.add_field(name = f"Бан", value = f"Заканчивается {'<t:{time_end}:f>'.format(time_end = int(penalt.time_end)) if not penalt.time_end is None else 'никогда (предупреждение)'}\n```{penalt.reason}```", inline = False)
				case 'punishment_warns':
					embed.add_field(name = f"Предупреждение", value = f"Заканчивается <t:{int(penalt.time_warn)}:f>\n```{penalt.reason}```", inline = False)
				case 'punishment_reprimands':
					embed.add_field(name = f"Выговор", value = f"Заканчивается <t:{int(penalt.time_warn)}:f>\n```{penalt.reason}```", inline = False)
				case 'punishment_perms':
					embed.add_field(name = f"Вечный бан", value = f"```{penalt.reason}```", inline = False)

		if len(embed.fields)==0:
			embed.add_field(name = f"Наказаний нет", value = f"", inline = False)

		await ctx.response.send_message(embed = embed)
		

	@commands.slash_command(description="Подайте жалобу на нарушение правил сервера или действия модератора", name="жалоба")
	async def report(self, ctx: disnake.AppCmdInter, member: disnake.Member = commands.Param(description="На кого хотите подать жалобу?", name="пользователь"), reason: str = commands.Param(description="Кратко опишите причину жалобы", name="причина")):
		
		async def ReportCallback(ctx, member, report_message, reason, embed, mentions, mod):

			async def AcceptCallback(report_message, member, embed, mod, call, channel):
				if call.author == mod.author:
					await channel.delete()
					embed.set_footer(text = f"Рассмотрено в пользу исца\n{mod.author.name} ({mod.author.id})")
					embed.colour=0x008000
					await report_message.edit(content = "", embed=embed, view=None)
					await member.send(embed = disnake.Embed(title=f"", description = f"После разбора нарушения модератор {mod.author.mention} признал вас виновным", colour = 0xff9900))

					await self.client.bt_send({"type": "complaint", "options": {"accepted": True, "attack_member": ctx.author.id, "defence_member": member.id, "moderator": mod.author.id}})
				else:
					await call.send(embed = disnake.Embed(title=f"", description = f"Только судья может использовать эти команды", colour = 0xff9900), ephemeral=True)

			async def DenyCallback(report_message, member, embed, mod, call, channel):
				if call.author == mod.author:
					await channel.delete()
					embed.set_footer(text = f"Рассмотрено в пользу ответчика\n{mod.author.name} ({mod.author.id})")
					embed.colour=0x008000
					await report_message.edit(content = "", embed=embed, view=None)
					#await member.send(embed = disnake.Embed(title=f"", description = f"После разбора нарушения модератор {mod.author.mention} признал вас невиновным", colour = 0xff9900))

					await self.client.bt_send({"type": "complaint", "options": {"accepted": False, "attack_member": ctx.author.id, "defence_member": member.id, "moderator": mod.author.id}})
				else:
					await call.send(embed = disnake.Embed(title=f"", description = f"Только судья может использовать эти команды", colour = 0xff9900), ephemeral=True)

			class AttackClass:
				def __init__(self, member, channel, mod):
					self.member=member
					self.channel=channel
					self.mod=mod
					self.permatt=True
				async def callback(self, mod):
					if mod.author == self.mod.author:
						await self.channel.set_permissions(self.member, read_messages = True, read_message_history=True, send_messages=self.permatt) #read_messages=self.permatt
						await mod.send(embed = disnake.Embed(title=f"", description = f"{self.member.mention}-{'право ответа включено' if self.permatt else 'право ответа выключено'}", colour = 0x008000), ephemeral=True)
						self.permatt=not self.permatt
					else:
						await mod.send(embed = disnake.Embed(title=f"", description = f"Только судья может использовать эти команды", colour = 0xff9900), ephemeral=True)
			class DefenceClass:
				def __init__(self, member, channel, mod):
					self.member=member
					self.channel=channel
					self.mod=mod
					self.permdef=True
				async def callback(self, mod):
					if mod.author == self.mod.author:
						await self.channel.set_permissions(self.member, read_messages = True, read_message_history=True, send_messages=self.permdef) #read_messages=self.permdef
						await mod.send(embed = disnake.Embed(title=f"", description = f"{self.member.mention}-{'право ответа включено' if self.permdef else 'право ответа выключено'}", colour = 0x008000), ephemeral=True)
						self.permdef=not self.permdef
					else:
						await mod.send(embed = disnake.Embed(title=f"", description = f"Только судья может использовать эти команды", colour = 0xff9900), ephemeral=True)

			if not any(i.mention in mentions for i in mod.author.roles):
				await mod.send(embed = disnake.Embed(description = f"Вы не можете принять этот репорт", colour = 0xff9900), ephemeral=True)
				return

			if mod.author == ctx.author:
				await mod.send(embed = disnake.Embed(description = f"Вы не можете принять свой же репорт", colour = 0xff9900), ephemeral=True)
				return

			embed.set_footer(text = f"Принято\n{mod.author.name} ({mod.author.id})")
			embed.colour=0x008000
			await report_message.edit(content = "", embed=embed, view=None)

			parsing_channel = await ctx.guild.create_text_channel(
				name=f"⚠️Жалоба от {ctx.author.name} на {member}",
				overwrites = {ctx.author: disnake.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True, attach_files=True),
							  mod.author: disnake.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True, attach_files=True),
							  member: disnake.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True, attach_files=True),
							  self.client.everyone: disnake.PermissionOverwrite(read_messages=False, send_messages=False, read_message_history=False)},
				category=ctx.guild.get_channel(1220744958961778850)
			)

			view = disnake.ui.View(timeout=86400)

			btnatt = disnake.ui.Button(label="⚔️", style=disnake.ButtonStyle.primary)
			view.add_item(btnatt)
			btndef = disnake.ui.Button(label="⚰️", style=disnake.ButtonStyle.primary)
			view.add_item(btndef)
			btnacc = disnake.ui.Button(label="✅", style=disnake.ButtonStyle.primary)
			view.add_item(btnacc)
			btnden = disnake.ui.Button(label="❌", style=disnake.ButtonStyle.primary)
			view.add_item(btnden)

			attack = AttackClass(ctx.author, parsing_channel, mod)
			defence = DefenceClass(member, parsing_channel, mod)

			pin = await parsing_channel.send( f"{mod.author.mention}" ,embed = disnake.Embed(title=f"Жалоба", description = f"Вы вызвались судить {member.mention} по жалобе от {ctx.author.mention}\n\
																															  ⚔️ - Дать {ctx.author.mention} право ответа\n\
																															  ⚰️ - Дать {member.mention} право ответа\n\
																															  ✅ - Виновен\n\
																															  ❌ - Невиновен\n\
																															  Перед закрытием дела убедитесь, что сохранили все доказательства", colour = 0x008000), view=view)
			btnatt.callback = lambda mod: attack.callback(mod)
			btndef.callback = lambda mod: defence.callback(mod)
			btnacc.callback = lambda call: AcceptCallback(report_message, member, embed, mod, call, parsing_channel)
			btnden.callback = lambda call: DenyCallback(report_message, member, embed, mod, call, parsing_channel)
			await pin.pin()

		if member==ctx.author:
			await ctx.send(embed = disnake.Embed(description = f'Нельзя подать жалобу на самого себя!', colour = 0xFF4500), ephemeral=True)
			return
		mentions = []

		report_channel = disnake.utils.get(ctx.guild.channels, id = 1219644036378394746)

		highest = [i for i in self.client.hierarchy if i in member.roles][0]
		for i in range(0, self.client.hierarchy.index(highest)):
			mentions.append(f"{self.client.hierarchy[i].mention}")


		if len(mentions)==0:
			mentions.append(f"{self.client.me.mention}")

		report_embed = disnake.Embed(title=f"**Жалоба**", colour = 0xDC143C)

		report_embed.add_field(name=f"Обвинитель: ", value = f"{ctx.author.mention}\n({ctx.author.id})", inline=True)
		report_embed.add_field(name=f"Обвиняемый: ", value = f"{member.mention}\n({member.id})", inline=True)
		report_embed.add_field(name=f"Причина: ", value = f"```{reason}```", inline=False)
		view = disnake.ui.View(timeout=86400)
		btn = disnake.ui.Button(label="✅", style=disnake.ButtonStyle.primary)
		view.add_item(btn)
		report_embed.set_thumbnail(url=member.avatar)
		report_message = await report_channel.send(", ".join(mentions), embed = report_embed, view=view)
		btn.callback = lambda mod: ReportCallback(ctx,member,report_message,reason,report_embed,mentions,mod)

		await ctx.send(embed = disnake.Embed(description = f'Жалоба на {member.mention} успешно подана', colour = 0x008000), ephemeral=True)

	'''

		Иерархия

	'''

	@commands.slash_command(description="Показывает весь персонал, по ролям и веткам", name="иерархия", administrator=True)
	async def hierarchy(self, ctx: disnake.AppCmdInter, branchid: int = commands.Param(description="Укажите id ветки, в которой вам нужна иерархия", name="ветвь", default=None),
														devmod: bool = commands.Param(description="Показывать подробную информацию?", name="devmode", default=False)):
		
		async with self.DataBaseManager.session() as session:
			async with session.begin():

				if branchid is None:
					stmt = (
						self.DataBaseManager.select(self.DataBaseManager.model_classes['staff_branches'])
						.options(
							self.DataBaseManager.selectinload(self.DataBaseManager.model_classes['staff_branches'].roles)
						)
						.order_by(
							self.DataBaseManager.model_classes['staff_branches'].layer.asc()
						)
					)
					branches = (await session.execute(stmt)).scalars().all()
					for branch in branches:
						branch.roles.sort(key=lambda role: role.layer)

					embed = disnake.Embed(title = f"", description = f"# Общая иерархия\n", colour = 0xff9900)
					for branchcounter, branch in enumerate(branches, start=1):
						embed.description += f"## {branchcounter}) {branch.purpose}"
						if devmod:
							embed.description += f" id:({branch.id}) layer:({branch.layer})"
						embed.description += "\n"

						for rolecounter, role in enumerate(branch.roles, start=1):
							embed.description += f"### {rolecounter}. <@&{role.id}>"
							if devmod:
								embed.description += f" layer:({role.layer})"
							embed.description += "\n"
					await ctx.send(embed = embed)
				else:
					branch = await session.get(self.DataBaseManager.model_classes['staff_branches'], branchid)

					stmt = (
						self.DataBaseManager.select(self.DataBaseManager.model_classes['staff_branches'])
						.options(
							self.DataBaseManager.selectinload(self.DataBaseManager.model_classes['staff_branches'].roles)
							.selectinload(self.DataBaseManager.model_classes['staff_roles'].users)
						)
						.where(
							self.DataBaseManager.model_classes['staff_branches'].id == branchid
						)
					)
					branch = (await session.execute(stmt)).scalars().first()
					if branch is None:
						await ctx.send(embed = disnake.Embed(description = f'Ветви с идентификатором {branchid} не существует', colour = 0xff9900))
						return 1

					branch.roles.sort(key=lambda role: role.layer)

					embed = disnake.Embed(title = f"", description = f"# Иерархия по ветви {branch.purpose}\n", colour = 0xff9900)

					for rolecounter, role in enumerate(branch.roles, start=1):
						embed.description += f"## {rolecounter}) <@&{role.id}>"
						if devmod:
							embed.description += f" layer:({role.layer})"
						embed.description += "\n"

						for membercounter, user in enumerate(role.users, start=1):
							embed.description += f"### - <@{user.user_id}>"
							if devmod:
								embed.description += f" update_time:(<t:{int(user.update_time)}:R>)"
							embed.description += "\n"
					await ctx.send(embed = embed)