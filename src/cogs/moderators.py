import disnake
from disnake.ext import commands
from disnake.ext import tasks
import asyncio
import sys
import os
import copy
import datetime
import math
import random
import json
import shutil
import tldextract

translate = {"textmute":"Текстовый мут", "voicemute":"Голосовой мут", "ban":"Бан", "warning":"Предупреждение",\
			 "time":"Время", "reason":"Причина", "changenick":"Сменить ник", "reprimand":"Выговор", "newnick":"Новый ник"}

form_to_send = {'punishment_mutes_voice': 'voice_mutes', 'punishment_mutes_text': 'text_mutes', 'punishment_bans': 'bans', 'punishment_warns': 'warns', 'punishment_reprimands': 'reprimand', 'punishment_perms': 'perm'}

count_translate = {"textmute":3, "voicemute":3, "ban":9, "warning":1, "changenick":0, "punishment_mutes_text":3, "punishment_mutes_voice":3, "punishment_bans":9, "punishment_warns":1}

def setup(bot):
	bot.add_cog(ModerModule(bot))

class ModerModule(commands.Cog):
	def __init__(self, client):
		self.client = client
		self.DataBaseManager = self.client.DataBaseManager

	@commands.Cog.listener()
	async def on_ready(self):
		self.client.logger.info(f'KrekModBot moderation module activated')

	@commands.slash_command(name="действие")
	async def action_slash(self, ctx: disnake.AppCmdInter, member: disnake.Member):
		models = self.client.DataBaseManager.model_classes
		DataBaseManager = self.client.DataBaseManager

		staff_users_roles_model = self.DataBaseManager.model_classes['staff_users_roles']
		staff_users_model = self.DataBaseManager.model_classes['staff_users']
		staff_roles_model = self.DataBaseManager.model_classes['staff_roles']
		staff_branches_model = self.DataBaseManager.model_classes['staff_branches']

		class ActionSelect(disnake.ui.Select):
			client = self.client
			max_strength_role = self.max_strength_role
			def __init__(self, member, reprimand_branches: list, other_on: bool):
				self.member=member
				placeholder = "Выберите действие"
				options = []
				for branch in reprimand_branches:
					options += [disnake.SelectOption(label=f"Выговор в ветке {branch.purpose}", value=f"reprimand:{branch.id}")]
				if other_on:
					options += [
						disnake.SelectOption(label="Предупреждение", value="warning"),
						disnake.SelectOption(label="Войс мут", value="voicemute"),
						disnake.SelectOption(label="Текстовый мут", value="textmute"),
						disnake.SelectOption(label="Бан", value="ban"),
						disnake.SelectOption(label="Сменить ник", value="changenick"),
					]
				options += [disnake.SelectOption(label="Удалить наказание", value="deletepenalties")]
				super().__init__(placeholder = placeholder, min_values = 1, max_values = 1, options = options)

			async def callback(self, interaction:disnake.MessageInteraction):

				class ActionModal(disnake.ui.Modal):
					client = self.client
					def __init__(self, title, member):
						self.member = member
						self.title = title
						components = []
						if title.split(":")[0] == "textmute" or title.split(":")[0] == "voicemute" or title.split(":")[0] == "ban":
							components = [
							disnake.ui.TextInput(label="Время", placeholder="Например: 1д15ч9мин", custom_id="time", style=disnake.TextInputStyle.short, max_length=100),
							disnake.ui.TextInput(label = "Причина", placeholder="Например: правило 1.3" , custom_id="reason", style=disnake.TextInputStyle.paragraph, max_length=100)
							]
						if title.split(":")[0] == "warning":
							components = [
							disnake.ui.TextInput(label = "Причина", placeholder="Например: правило 1.3" , custom_id="reason", style=disnake.TextInputStyle.paragraph, max_length=100)
							]
						if title.split(":")[0] == "reprimand":
							components = [
							disnake.ui.TextInput(label = "Причина", placeholder="Например: неправомерный бан" , custom_id="reason", style=disnake.TextInputStyle.paragraph, max_length=100)
							]
						if title.split(":")[0] == "changenick":
							components = [
							disnake.ui.TextInput(label="Новый ник", placeholder="Например: Humanoid", custom_id="newnick", style=disnake.TextInputStyle.short, max_length=32)
							]
						super().__init__(title = title, components = components, timeout=300)

					async def callback(self, interaction: disnake.Interaction):

						if interaction.guild is None:
							raise TypeError("interaction.guild is None")

						async def voicemute(interaction: disnake.MessageInteraction, member: disnake.Member, time, reason):
							role = self.client.voice_mute
							await member.add_roles(role)
							await member.move_to(None) # type: ignore
							async with DataBaseManager.session() as session:
								async with session.begin():
									new_punishment = models['punishment_mutes_voice'](user_id = member.id, reason = reason, time_end = time, time_warn = None, moderator_id = interaction.author.id)
									session.add(new_punishment)
						async def textmute(interaction: disnake.MessageInteraction, member: disnake.Member, time, reason):
							role = self.client.text_mute
							await member.add_roles(role)
							async with DataBaseManager.session() as session:
								async with session.begin():
									new_punishment = models['punishment_mutes_text'](user_id = member.id, reason = reason, time_end = time, time_warn = None, moderator_id = interaction.author.id)
									session.add(new_punishment)
						async def ban(interaction: disnake.MessageInteraction, member: disnake.Member, time, reason):
								role = self.client.ban_role
								await member.move_to(None) # type: ignore
								if time-datetime.datetime.timestamp(datetime.datetime.now())>0:
									await member.add_roles(role)
									async with DataBaseManager.session() as session:
										async with session.begin():
											new_punishment = models['punishment_bans'](user_id = member.id, reason = reason, time_end = time, moderator_id = interaction.author.id)
											session.add(new_punishment)
									return
								await member.add_roles(role)
								async with DataBaseManager.session() as session:
									async with session.begin():
										new_punishment = models['punishment_perms'](user_id = member.id, reason = reason, moderator_id = interaction.author.id)
										session.add(new_punishment)

								if interaction.guild is None:
									raise TypeError("interaction.guild is None")
								for channel in interaction.guild.channels:
									if isinstance(channel, disnake.TextChannel):
										await channel.purge(limit=10, check=lambda m: m.author==member)
						async def warning(interaction: disnake.MessageInteraction, member: disnake.Member, reason):
							async with DataBaseManager.session() as session:
								async with session.begin():
									new_punishment = models['punishment_warns'](user_id = member.id, reason = reason, time_warn = float(self.client.TimeFormater(days = 30)), moderator_id = interaction.author.id)
									session.add(new_punishment)
						async def reprimand(interaction: disnake.MessageInteraction, member: disnake.Member, branchid, reason):
							async with DataBaseManager.session() as session:
								async with session.begin():
									new_punishment = models['punishment_reprimands'](user_id = member.id, branch_id = branchid, reason = reason, time_warn = float(self.client.TimeFormater(days = 80)), designated_user_id = interaction.author.id)
									session.add(new_punishment)
						async def changenick(interaction: disnake.MessageInteraction, member: disnake.Member, newnick):
							await member.edit(nick=newnick)

						await interaction.response.defer(ephemeral=True)
						embed = self.client.AnswEmbed(title=f"{translate[self.title.split(':')[0]]}", description = f"{self.member.mention} ({self.member.id})")
						bans_channel = disnake.utils.get(interaction.guild.channels, id = 1219644103973671035)
						warns_channel = disnake.utils.get(interaction.guild.channels, id = 1219644151184887838)
						muts_channel = disnake.utils.get(interaction.guild.channels, id = 1219644125469474889)
						reprimands_channel = disnake.utils.get(interaction.guild.channels, id = self.client.constants['reprimandlog_channel'])
						logs_channel = disnake.utils.get(interaction.guild.channels, id = 490730651629387776)
						formated_time = None
						reason = ""
						newnick = ""
						if self.title.split(':')[0] == "reprimand":
							embed.add_field(name = 'Ветка', value = self.title.split(':')[1], inline = False)

						if isinstance(interaction, disnake.Interaction):
							raise TypeError("modal interaction is interaction")
						
						for key, value in interaction.text_values.items():
							if key == "time":
								formated_time = self.client.TimeFormater(value)
								embed.add_field(name = translate[key], value = str(formated_time), inline = True)
							elif key == "reason":
								reason = value
								embed.add_field(name = translate[key], value = f"```{value}```", inline = False)
							elif key == "newnick":
								newnick = value
								embed.add_field(name = "", value=f"`{self.member.nick!r} ==> {newnick!r}`", inline = False)
							else:
								embed.add_field(name = translate[key], value = value, inline = False)
						embed.set_footer(text = f"{interaction.author.name}\n{interaction.author.id}")
						embed.set_thumbnail(url=self.member.avatar)

						await self.client.bt_send({"type": "punishment", "options": {"severity": self.title.split(':')[0], "member": self.member.id, "moderator": interaction.author.id}})

						if self.title.split(":")[0] == "reprimand":

							async with DataBaseManager.session() as session:
								async with session.begin():
									stmt = (
										DataBaseManager.select(models['punishment_reprimands'])
										.where(
											models['punishment_reprimands'].user_id == self.member.id,
											models['punishment_reprimands'].branch_id == int(self.title.split(':')[1])
										)
									)
									result = (await session.execute(stmt)).scalars().all()

							await reprimand(interaction, self.member, int(self.title.split(':')[1]), reason)
							embed.add_field(name = "Всего выговоров в этой ветке", value = str(len(result)+1), inline = False)
							await reprimands_channel.send(embed=embed)

						else:
							if self.title == "textmute":
								await textmute(interaction, self.member, float(formated_time), reason)
								await muts_channel.send(embed=embed)

								await interaction.author.send("Скопируй и вставь следующее сообщение с прикреплением доказательств в канал \"[mutlog](https://discord.com/channels/1219110919536115802/1219114151566114847)\"!!!")
								await interaction.author.send(f"```{self.member.id}/{str(formated_time)}/{reason}```")

							elif self.title == "voicemute":
								await voicemute(interaction, self.member, float(formated_time), reason)
								await muts_channel.send(embed=embed)

								await interaction.author.send("Скопируй и вставь следующее сообщение с прикреплением доказательств в канал \"[mutlog](https://discord.com/channels/1219110919536115802/1219114151566114847)\"!!!")
								await interaction.author.send(f"```{self.member.id}/{str(formated_time)}/{reason}```")

							elif self.title == "ban":
								await ban(interaction, self.member, float(formated_time), reason)
								await bans_channel.send(embed=embed)

								await interaction.author.send("Скопируй и вставь следующее сообщение с прикреплением доказательств в канал \"[banlog](https://discord.com/channels/1219110919536115802/1219110920060407850)\"!!!")
								await interaction.author.send(f"```{self.member.id}/{str(formated_time)}/{reason}```")

							elif self.title == "warning":
								await warning(interaction, self.member, reason)
								await warns_channel.send(embed=embed)

								await interaction.author.send("Скопируй и вставь следующее сообщение с прикреплением доказательств в канал \"[warnlog](https://discord.com/channels/1219110919536115802/1219129098257956947)\"!!!")
								await interaction.author.send(f"```{self.member.id}/{reason}```")

							elif self.title == "changenick":
								await changenick(interaction, self.member, newnick)
								await logs_channel.send(embed=embed)
							else:
								await logs_channel.send(embed=embed)

							counter = 0
							async with DataBaseManager.session() as session:
								async with session.begin():
									for i in ["punishment_mutes_text", "punishment_mutes_voice", "punishment_bans", "punishment_warns"]:
										stmt = DataBaseManager.select(models[i]).where(models[i].user_id == self.member.id)
										result = (await session.execute(stmt)).scalars().all()
										counter += count_translate[i] * len(result)
							if counter>=18:
								await ban(interaction, self.member, 0, "Набрал больше 18 'очков наказаний'")
								await bans_channel.send(embed=self.client.AnswEmbed(title=f"Достойное достижение!", description = f"Поздравляем! {self.member.mention}({self.member.id}) наконец набрал целых {counter} очков наказания и получил свою награду: вечный бан!"))

						await interaction.edit_original_response(embed=embed)

				class DeletePenaltiesSelect(disnake.ui.Select):
					client = self.client
					max_strength_role = self.max_strength_role
					def __init__(self, member):
						self.member=member
						
					async def initialization(self, embed):
						member = self.member
						placeholder = "Выберите наказание для снятия"
						options=[]
						async with DataBaseManager.session() as session:
							async with session.begin():

								result = []
								stmt = self.max_strength_role(user_id = ctx.author.id, is_moder = True, is_admin = True)
								author_is_moderator = (await session.execute(stmt)).first() is not None

								stmt = self.max_strength_role(user_id = ctx.author.id, is_admin = True)
								author_is_admin = (await session.execute(stmt)).first()
								
								if author_is_admin:
									stmt = DataBaseManager.select(models['punishment_reprimands']).where(models['punishment_reprimands'].user_id == member.id)
									result += (await session.execute(stmt)).scalars().all()

								if author_is_moderator:
									stmt = DataBaseManager.select(models['punishment_mutes_text']).where(models['punishment_mutes_text'].user_id == member.id)
									result += (await session.execute(stmt)).scalars().all()
									stmt = DataBaseManager.select(models['punishment_mutes_voice']).where(models['punishment_mutes_voice'].user_id == member.id)
									result += (await session.execute(stmt)).scalars().all()
									stmt = DataBaseManager.select(models['punishment_bans']).where(models['punishment_bans'].user_id == member.id)
									result += (await session.execute(stmt)).scalars().all()
									stmt = DataBaseManager.select(models['punishment_warns']).where(models['punishment_warns'].user_id == member.id)
									result += (await session.execute(stmt)).scalars().all()
									stmt = DataBaseManager.select(models['punishment_perms']).where(models['punishment_perms'].user_id == member.id)
									result += (await session.execute(stmt)).scalars().all()

								result = sorted(result, key=lambda a: a.time_begin, reverse=True)

						for penalt in result:
							match penalt.get_table_name():
								case 'punishment_mutes_text':
									embed.add_field(name = f"{penalt.id} : Текстовый мут", value = f"Заканчивается {'<t:{time_end}:f>'.format(time_end = int(penalt.time_end)) if penalt.time_warn is None else '<t:{time_warn}:f> (предупреждение)'.format(time_warn = int(penalt.time_warn))}\n```{penalt.reason}```", inline = False)
									options.append(disnake.SelectOption(label=f"{penalt.id}) Текстовый мут", value=f"{penalt.get_table_name()}:{member.id}:{penalt.id}"))
								case 'punishment_mutes_voice':
									embed.add_field(name = f"{penalt.id} : Голосовой мут", value = f"Заканчивается {'<t:{time_end}:f>'.format(time_end = int(penalt.time_end)) if penalt.time_warn is None else '<t:{time_warn}:f> (предупреждение)'.format(time_warn = int(penalt.time_warn))}\n```{penalt.reason}```", inline = False)
									options.append(disnake.SelectOption(label=f"{penalt.id}) Голосовой мут", value=f"{penalt.get_table_name()}:{member.id}:{penalt.id}"))
								case 'punishment_bans':
									embed.add_field(name = f"{penalt.id} : Бан", value = f"Заканчивается {'<t:{time_end}:f>'.format(time_end = int(penalt.time_end)) if not penalt.time_end is None else 'никогда (предупреждение)'}\n```{penalt.reason}```", inline = False)
									options.append(disnake.SelectOption(label=f"{penalt.id}) Бан", value=f"{penalt.get_table_name()}:{member.id}:{penalt.id}"))
								case 'punishment_warns':
									embed.add_field(name = f"{penalt.id} : Предупреждение", value = f"Заканчивается <t:{int(penalt.time_warn)}:f>\n```{penalt.reason}```", inline = False)
									options.append(disnake.SelectOption(label=f"{penalt.id}) Предупреждение", value=f"{penalt.get_table_name()}:{member.id}:{penalt.id}"))
								case 'punishment_reprimands':
									embed.add_field(name = f"{penalt.id} : Выговор", value = f"Заканчивается <t:{int(penalt.time_warn)}:f>\n```{penalt.reason}```", inline = False)
									options.append(disnake.SelectOption(label=f"{penalt.id}) Выговор", value=f"{penalt.get_table_name()}:{member.id}:{penalt.id}"))
								case 'punishment_perms':
									embed.add_field(name = f"{penalt.id} : Вечный бан", value = f"```{penalt.reason}```", inline = False)
									options.append(disnake.SelectOption(label=f"{penalt.id}) Вечный бан", value=f"{penalt.get_table_name()}:{member.id}:{penalt.id}"))

						if len(options)==0:
							embed.add_field(name = f"Наказаний нет", value = f" ", inline = False)
							options.append(disnake.SelectOption(label="Наказаний нет"))
						super().__init__(placeholder = placeholder, min_values = 1, max_values = 1, options = options)

						return self
					async def callback(self, interaction:disnake.MessageInteraction):
						if interaction.values is None or interaction.guild is None:
							raise TypeError("interaction.values is None or interaction.guild is None")
						values = interaction.values[0]
						try:
							pentype, member, penaltid = values.split(":")
						except ValueError:
							return
						if values:
							logs_channel = disnake.utils.get(interaction.guild.channels, id = 490730651629387776)
							if not isinstance(logs_channel, disnake.TextChannel):
								raise ValueError("logs_channel is None")

							async with DataBaseManager.session() as session:
								async with session.begin():
									stmt = DataBaseManager.select(models[pentype]).where(
										DataBaseManager.and_(
											models[pentype].id == int(penaltid),
											models[pentype].user_id == int(member)
										)
									).with_for_update()
									result = (await session.execute(stmt)).scalars().first()
									await session.delete(result)

							if pentype=="punishment_perms" or pentype=="punishment_bans":
								await self.member.remove_roles(self.client.ban_role)
								await self.client.bt_send({"type": "unpunishment", "options": {"severity": "ban", "member": int(member)}})
							elif pentype=="punishment_mutes_text":
								await self.member.remove_roles(self.client.text_mute)
								await self.client.bt_send({"type": "unpunishment", "options": {"severity": "textmute", "member": int(member)}})
							elif pentype=="punishment_mutes_voice":
								await self.member.remove_roles(self.client.voice_mute)
								await self.client.bt_send({"type": "unpunishment", "options": {"severity": "voicemute", "member": int(member)}})
							elif pentype=="punishment_reprimands":
								await self.client.bt_send({"type": "unpunishment", "options": {"severity": "reprimand", "member": int(member)}})
							elif pentype=="punishment_warns":
								await self.client.bt_send({"type": "unpunishment", "options": {"severity": "warning", "member": int(member)}})

							view = disnake.ui.View(timeout=30)
							embed =  self.client.AnswEmbed(title="Выберите наказание для снятия", description = f"{self.member.mention}\n({self.member.id})")
							view.add_item(await DeletePenaltiesSelect(self.member).initialization(embed))
							await interaction.response.edit_message(embed = embed, view=view)

							await interaction.followup.send(embed = self.client.AnswEmbed(description = f"Наказание {pentype} успешно аннулировано!"), ephemeral=True)
							await logs_channel.send(embed = self.client.AnswEmbed(description = f"{interaction.author.mention}({interaction.author.id}) успешно аннулировал наказание {pentype}({penaltid}) у пользователя {member}"),)


				if "textmute" in self.values[0] or "voicemute" in self.values[0] or "ban" in self.values[0] or\
				   "warning" in self.values[0] or "changenick" in self.values[0] or "reprimand" in self.values[0]:
					modal = ActionModal(self.values[0], self.member)
					await interaction.response.send_modal(modal)
				elif "deletepenalties" in self.values[0]:
					view = disnake.ui.View(timeout=30)
					embed =  self.client.AnswEmbed(title="Выберите наказание для снятия", description = f"{self.member.mention}\n({self.member.id})")
					view.add_item(await DeletePenaltiesSelect(self.member).initialization(embed))
					await interaction.response.send_message(embed = embed, ephemeral=True, view=view)
		await ctx.response.defer(ephemeral=True)

		async with self.DataBaseManager.session() as session:

			stmt = self.max_strength_role(ctx.author.id)
			author_strenght = (await session.execute(stmt)).first()
			if author_strenght is None:
				await ctx.edit_original_message(embed = self.client.ErrEmbed(description = f"Вы должны иметь должность в персонале полей, чтобы действовать"))
				return

			stmt = (
				self.DataBaseManager.select(staff_users_roles_model)
				.options(
					self.DataBaseManager.joinedload(staff_users_roles_model.role),
					self.DataBaseManager.joinedload(staff_users_roles_model.branch)
				)
				.where(staff_users_roles_model.user_id == member.id)
			)
			member_roles = (await session.execute(stmt)).scalars().all()

			stmt = (
				self.DataBaseManager.select(staff_users_roles_model.role_id)
				.where(staff_users_roles_model.user_id == ctx.author.id)
			)
			author_roles = set((await session.execute(stmt)).scalars().all())

			reprimand_branches = []

			for role in member_roles:
				stmt = (
					self.DataBaseManager.select(staff_roles_model.id)
					.join(staff_branches_model, staff_roles_model.branch_id == staff_branches_model.id)
					.where(
						self.DataBaseManager.tuple_(staff_branches_model.layer, staff_roles_model.layer) < (role.branch.layer, role.role.layer)
					)
					.order_by(
						staff_branches_model.layer.asc(),
						staff_roles_model.layer.asc()
					)
				)
				grand_roles = set((await session.execute(stmt)).scalars().all())

				if bool(author_roles & grand_roles):
					reprimand_branches += [role.branch]

			stmt = self.max_strength_role(ctx.author.id, is_moder = True, is_admin = True)
			author_is_moderator = (await session.execute(stmt)).all()
			stmt = self.max_strength_role(member.id, is_moder = True, is_admin = True)
			member_is_moderator = (await session.execute(stmt)).all()

		class View(disnake.ui.View):
			async def on_timeout(self):
				await ctx.edit_original_message(view=None)

		if (not reprimand_branches) and (not ((not member_is_moderator) and author_is_moderator)):
			await ctx.edit_original_message(embed = self.client.ErrEmbed(description = f"Вы ничего не можете сделать этому пользователю"))
			return
				
		embed = self.client.AnswEmbed(title="Выберите действие", description = f"{member.mention}\n({member.id})")
		embed.set_thumbnail(url=member.avatar)
		view = View(timeout=30)
		view.add_item(ActionSelect(member = member, reprimand_branches = reprimand_branches, other_on = (not member_is_moderator) and author_is_moderator))
		await ctx.edit_original_message(embed = embed, view=view)

	'''

		Продвижения и т.п.

	'''

	def max_strength_role(self, user_id: int, branch_ids: list = [], is_admin: bool = False, is_moder: bool = False):
		staff_users_roles_model = self.DataBaseManager.model_classes['staff_users_roles']
		staff_users_model = self.DataBaseManager.model_classes['staff_users']
		staff_roles_model = self.DataBaseManager.model_classes['staff_roles']
		staff_branches_model = self.DataBaseManager.model_classes['staff_branches']

		stmt = (
			self.DataBaseManager.select(staff_branches_model.layer, staff_roles_model.layer)
			.select_from(staff_users_roles_model)
			.join(staff_users_model, staff_users_roles_model.user_id == staff_users_model.id)
			.join(staff_roles_model, staff_users_roles_model.role_id == staff_roles_model.id)
			.join(staff_branches_model, staff_roles_model.branch_id == staff_branches_model.id)
			.order_by(
				staff_branches_model.layer.asc(),
				staff_roles_model.layer.asc()
			)
		)
		if is_admin or is_moder or branch_ids:
			stmt = stmt.where(
				self.DataBaseManager.and_(
					self.DataBaseManager.or_(
						staff_branches_model.id.in_(branch_ids),
						staff_branches_model.is_admin == is_admin if is_admin else self.DataBaseManager.false(),
						staff_branches_model.is_moder == is_moder if is_moder else self.DataBaseManager.false()
					),
					staff_users_model.id == user_id
				)
			)
		else:
			stmt = stmt.where(
				staff_users_model.id == user_id
			)

		return stmt

	async def promotions_add_remove_role(self, ctx, userid, add_roleid = None, remove_roleid = None):
		krekchat = await self.client.fetch_guild(self.client.krekchat.id)
		member = await krekchat.fetch_member(userid)
		if not add_roleid is None:
			add_role = await krekchat.fetch_role(add_roleid)
			try:
				await member.add_roles(add_role)
			except disnake.errors.Forbidden:
				await ctx.channel.send(ctx.author.mention, embed = self.client.ErrEmbed(description = f'Недостаточно прав. Пользователю {member.mention} необходимо ручное добавление роли {add_role.mention}'))

		if not remove_roleid is None:
			remove_role = await krekchat.fetch_role(remove_roleid)
			try:
				await member.remove_roles(remove_role)
			except disnake.errors.Forbidden:
				await ctx.channel.send(ctx.author.mention, embed = self.client.ErrEmbed(description = f'Недостаточно прав. Пользователю {member.mention} необходимо ручное удаление роли {remove_role.mention}'))


	@commands.slash_command(description="Позволяет повысить пользователя в указанной ветке", name="повысить", administrator=True)
	async def promote(self, ctx: disnake.AppCmdInter, branchid: int = commands.Param(description="Укажите id ветви", name="ветвь", default = None),
													  userid_str: str = commands.Param(description="Укажите id пользователя (используются идентификаторы дискорда)", name="пользователь")):

		userid = int(userid_str)

		async with self.DataBaseManager.session() as session:
			async with session.begin():

				staff_users_roles_model = self.DataBaseManager.model_classes['staff_users_roles']
				staff_users_model = self.DataBaseManager.model_classes['staff_users']
				staff_roles_model = self.DataBaseManager.model_classes['staff_roles']
				staff_branches_model = self.DataBaseManager.model_classes['staff_branches']

				if branchid is None:
					stmt = (
						self.DataBaseManager.select(staff_users_roles_model)
						.options(
							self.DataBaseManager.selectinload(staff_users_roles_model.role)
							.selectinload(staff_roles_model.branch)
						)
						.where(
							staff_users_roles_model.user_id == userid
						)
					)
					user_roles = (await session.execute(stmt)).scalars().all()

					if len(user_roles) != 1:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Для данной операции необходимо уточнение id ветки!'))
						return 1

					else:
						branchid = user_roles[0].role.branch.id

				stmt = self.max_strength_role(user_id = ctx.author.id, branch_ids = [branchid], is_admin = True)
				author_upper_role = (await session.execute(stmt)).first()

				stmt = self.max_strength_role(user_id = userid, branch_ids = [branchid])
				member_upper_role = (await session.execute(stmt)).first()

				if author_upper_role is None or ((not member_upper_role is None) and author_upper_role >= member_upper_role):
					await ctx.send(embed = self.client.ErrEmbed(description = f'Вы должны быть выше должности, на которую назначаете пользователя'))
					return 1

				stmt = (
					self.DataBaseManager.select(staff_roles_model)
					.options(
						self.DataBaseManager.selectinload(staff_roles_model.branch)
					)
					.where(staff_roles_model.branch_id == branchid)
					.order_by(staff_roles_model.layer.desc())
				)
				branch_roles = (await session.execute(stmt)).scalars().all()

				stmt = (
					self.DataBaseManager.select(staff_users_roles_model)
					.join(staff_users_model, staff_users_roles_model.user_id == staff_users_model.id)
					.join(staff_roles_model, staff_users_roles_model.role_id == staff_roles_model.id)
					.join(staff_branches_model, staff_roles_model.branch_id == staff_branches_model.id)
					.options(
						self.DataBaseManager.contains_eager(staff_users_roles_model.user),
						self.DataBaseManager.contains_eager(staff_users_roles_model.role)
						.contains_eager(staff_roles_model.branch)
					)
					.where(
						self.DataBaseManager.and_(
							staff_branches_model.id == branchid,
							staff_users_model.id == userid
						)
					)
				).with_for_update()
				member_role = (await session.execute(stmt)).scalars().first()

				if member_role is not None:
					member_role_index = next((i for i, role in enumerate(branch_roles) if role.id == member_role.role.id), None)
					if member_role_index is None:
						raise ValueError("member_role_index is None")

					if member_role_index + 1 >= len(branch_roles):
						await ctx.send(embed = self.client.ErrEmbed(description = f'Этот пользователь уже находится на самой высокой должности в данной ветви'))
						return 1

					target_role = branch_roles[member_role_index + 1]
					if author_upper_role >= (target_role.branch.layer, target_role.layer):
						await ctx.send(embed = self.client.ErrEmbed(description = f'Вы должны быть выше должности, на которую назначаете пользователя'))
						return 1

					previous_role_id = member_role.role_id
					member_role.role_id = target_role.id
					await ctx.send(embed = self.client.AnswEmbed(description = f'Пользователь <@{userid}> успешно назначен на роль <@&{target_role.id}>'))
					await self.promotions_add_remove_role(ctx, userid, add_roleid = target_role.id, remove_roleid = previous_role_id)
					return 0
				else:
					member_check = await session.get(staff_users_model, userid)
					if member_check is None:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Необходимо изначально зарегистрировать пользователя, попросите разработчика использовать \"/правка_пользователя\"'))
						return 1

					member_role_index = 0

					if member_role_index >= len(branch_roles):
						await ctx.send(embed = self.client.ErrEmbed(description = f'В данной ветви пока нет ролей'))
						return 1

					target_role = branch_roles[member_role_index]
					if author_upper_role >= (target_role.branch.layer, target_role.layer):
						await ctx.send(embed = self.client.ErrEmbed(description = f'Вы должны быть выше должности, на которую назначаете пользователя'))
						return 1

					user_role = await staff_users_roles_model.create_with_auto_branch(session, user_id = userid, role_id = target_role.id)
					session.add(user_role)
					await ctx.send(embed = self.client.AnswEmbed(description = f'Пользователь <@{userid}> успешно назначен на роль <@&{target_role.id}>'))
					await self.promotions_add_remove_role(ctx, userid, add_roleid = target_role.id)
					return 0

	@commands.slash_command(description="Позволяет понизить пользователя в указанной ветке", name="понизить", administrator=True)
	async def demote(self, ctx: disnake.AppCmdInter, branchid: int = commands.Param(description="Укажите id ветви", name="ветвь", default = None),
													  userid_str: str = commands.Param(description="Укажите id пользователя (используются идентификаторы дискорда)", name="пользователь")):
		
		userid = int(userid_str)

		async with self.DataBaseManager.session() as session:
			async with session.begin():

				staff_users_roles_model = self.DataBaseManager.model_classes['staff_users_roles']
				staff_users_model = self.DataBaseManager.model_classes['staff_users']
				staff_roles_model = self.DataBaseManager.model_classes['staff_roles']
				staff_branches_model = self.DataBaseManager.model_classes['staff_branches']

				if branchid is None:
					stmt = (
						self.DataBaseManager.select(staff_users_roles_model)
						.options(
							self.DataBaseManager.selectinload(staff_users_roles_model.role)
							.selectinload(staff_roles_model.branch)
						)
						.where(
							staff_users_roles_model.user_id == userid
						)
					)
					user_roles = (await session.execute(stmt)).scalars().all()

					if len(user_roles) != 1:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Для данной операции необходимо уточнение id ветки!'))
						return 1

					else:
						branchid = user_roles[0].role.branch.id

				stmt = self.max_strength_role(user_id = ctx.author.id, branch_ids = [branchid], is_admin = True)
				author_upper_role = (await session.execute(stmt)).first()

				stmt = self.max_strength_role(user_id = userid, branch_ids = [branchid])
				member_upper_role = (await session.execute(stmt)).first()

				if author_upper_role is None or ((not member_upper_role is None) and author_upper_role >= member_upper_role):
					await ctx.send(embed = self.client.ErrEmbed(description = f'Вы должны быть выше пользователя в должности'))
					return 1

				stmt = (
					self.DataBaseManager.select(staff_roles_model)
					.options(
						self.DataBaseManager.selectinload(staff_roles_model.branch)
					)
					.where(staff_roles_model.branch_id == branchid)
					.order_by(staff_roles_model.layer.desc())
				)
				branch_roles = (await session.execute(stmt)).scalars().all()

				stmt = (
					self.DataBaseManager.select(staff_users_roles_model)
					.join(staff_users_model, staff_users_roles_model.user_id == staff_users_model.id)
					.join(staff_roles_model, staff_users_roles_model.role_id == staff_roles_model.id)
					.join(staff_branches_model, staff_roles_model.branch_id == staff_branches_model.id)
					.options(
						self.DataBaseManager.contains_eager(staff_users_roles_model.user),
						self.DataBaseManager.contains_eager(staff_users_roles_model.role)
						.contains_eager(staff_roles_model.branch)
					)
					.where(
						self.DataBaseManager.and_(
							staff_branches_model.id == branchid,
							staff_users_model.id == userid
						)
					)
				).with_for_update()
				member_role = (await session.execute(stmt)).scalars().first()

				if member_role is not None:
					member_role_index = next((i for i, role in enumerate(branch_roles) if role.id == member_role.role.id), None)
					if member_role_index is None:
						raise ValueError("member_role_index is None")

					if member_role_index == 0:
						stmt = (
							self.DataBaseManager.select(staff_users_roles_model)
							.where(staff_users_roles_model.user_id == userid)
						)
						result = (await session.execute(stmt)).scalars().all()
						await self.promotions_add_remove_role(ctx, userid, remove_roleid = member_role.role_id)
						if len(result) <= 1:
							stmt = self.DataBaseManager.delete(staff_users_model).where(staff_users_model.id == userid)
							await session.execute(stmt)
							await ctx.send(embed = self.client.AnswEmbed(description = f'Пользователь <@{userid}> полностью удалён из системы'))
							await self.promotions_add_remove_role(ctx, userid, remove_roleid = self.client.staff.id)
							return 0
						else:
							await session.delete(member_role)
							await ctx.send(embed = self.client.AnswEmbed(description = f'Пользователь <@{userid}> снят со всех должностей в ветви {branchid}'))
							return 0

					target_role = branch_roles[member_role_index - 1]
					previous_role_id = member_role.role_id
					member_role.role_id = target_role.id
					await ctx.send(embed = self.client.AnswEmbed(description = f'Пользователь <@{userid}> успешно понижен до роли <@&{target_role.id}> в ветви {branchid}'))
					await self.promotions_add_remove_role(ctx, userid, add_roleid = target_role.id, remove_roleid = previous_role_id)
					return 0
				else:
					await ctx.send(embed = self.client.ErrEmbed(description = f'Данный пользователь не имеет роли в ветке {branchid}'))
					return 1

	@commands.slash_command(description="Позволяет добавить домен в белый список", name="добавить_ссылку", administrator=True)
	async def add_domain(self, ctx: disnake.AppCmdInter, link: str = commands.Param(description="Укажите ссылку или домен", name="ссылка")):
		async with self.DataBaseManager.session() as session:
			async with session.begin():
				if not (await self.DataBaseManager.model_classes['staff_users'].is_admin_or_moder_by_id(ctx.author.id, self.DataBaseManager, session)):
					await ctx.send(embed = self.client.ErrEmbed(description = f'У вас недостаточно полномочий, чтобы добавлять ссылку в белый лист. Обратитесь к любому модератору или разработчику.'))
					return 1

				else:

					def extract_root_domain(url):
						ext = tldextract.extract(url)
						if not ext.domain or not ext.suffix:
							return None
						return f"{ext.domain}.{ext.suffix}".lower()
					new_link = extract_root_domain(link)
					if not new_link:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Некорректная ссылка!'))
						return 1

					аllowed_domains_model = self.DataBaseManager.model_classes['аllowed_domains']

					stmt = self.DataBaseManager.select(аllowed_domains_model).where(аllowed_domains_model.domain == new_link)
					link_in_wl = (await session.execute(stmt)).scalars().first()

					if link_in_wl is not None:
						await ctx.send(embed = self.client.ErrEmbed(description = f'Этот домен уже есть в белом листе!'))
						return 1

					domain = аllowed_domains_model(domain = new_link, initiator_id = ctx.author.id)
					session.add(domain)

					await ctx.send(embed = self.client.AnswEmbed(description = f'Домен {new_link} успешно добавлен в белый список'))
					return 0