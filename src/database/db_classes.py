from sqlalchemy import Column, Integer, BigInteger, Text, Float, ForeignKey, UniqueConstraint, MetaData, Boolean
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from sqlalchemy.schema import CreateTable
from sqlalchemy.sql import text
import datetime
from typing import Annotated

class Base(DeclarativeBase):

	def get_table_name(self):
		return self.__tablename__

	def to_dict(self, exclude: list[str] = None):
		"""Конвертирует модель в словарь, исключая указанные поля."""
		if exclude is None:
			exclude = []

		return {
			c.name: getattr(self, c.name)
			for c in self.__table__.columns
			if c.name not in exclude
		}

discord_identificator_pk = Annotated[int, mapped_column(BigInteger, primary_key=True, nullable=False, index = True)]
identificator_pk = Annotated[int, mapped_column(Integer, primary_key=True, nullable=False, autoincrement=True, index = True)]
discord_identificator = Annotated[int, mapped_column(BigInteger, nullable=False, index=True)]

# Модели для системы наказаний
class PunishmentTextMute(Base):
	__tablename__ = 'punishment_mutes_text'
	id: Mapped[identificator_pk]
	user_id: Mapped[discord_identificator]
	reason: Mapped[str | None] = mapped_column(Text)
	time_end: Mapped[float | None] = mapped_column(Float)
	time_warn: Mapped[float | None] = mapped_column(Float)

	time_begin: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW())"))
	moderator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, default = None)


class PunishmentVoiceMute(Base):
	__tablename__ = 'punishment_mutes_voice'
	id: Mapped[identificator_pk]
	user_id: Mapped[discord_identificator]
	reason: Mapped[str | None] = mapped_column(Text)
	time_end: Mapped[float | None] = mapped_column(Float)
	time_warn: Mapped[float | None] = mapped_column(Float)

	time_begin: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW())"))
	moderator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, default = None)


class PunishmentWarn(Base):
	__tablename__ = 'punishment_warns'
	id: Mapped[identificator_pk]
	user_id: Mapped[discord_identificator]
	reason: Mapped[str | None] = mapped_column(Text)
	time_warn: Mapped[float] = mapped_column(Float)

	time_begin: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW())"))
	moderator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, default = None)


class PunishmentBan(Base):
	__tablename__ = 'punishment_bans'
	id: Mapped[identificator_pk]
	user_id: Mapped[discord_identificator]
	reason: Mapped[str | None] = mapped_column(Text)
	time_end: Mapped[float | None] = mapped_column(Float)

	time_begin: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW())"))
	moderator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, default = None)


class PunishmentPerm(Base):
	__tablename__ = 'punishment_perms'
	id: Mapped[identificator_pk]
	user_id: Mapped[discord_identificator]
	reason: Mapped[str | None] = mapped_column(Text)

	time_begin: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW())"))
	moderator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, default = None)


class PunishmentReprimand(Base):
	__tablename__ = 'punishment_reprimands'
	id: Mapped[identificator_pk]
	user_id: Mapped[discord_identificator]
	reason: Mapped[str | None] = mapped_column(Text)
	time_warn: Mapped[float] = mapped_column(Float)
	branch_id: Mapped[int] = mapped_column(ForeignKey('staff_branches.id', ondelete='CASCADE'))

	time_begin: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW())"))
	designated_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, default = None)


# Модели для системы персонала
class StaffBranch(Base):
	__tablename__ = 'staff_branches'
	id: Mapped[identificator_pk]
	layer: Mapped[int] = mapped_column(Integer, nullable=False)
	purpose: Mapped[str] = mapped_column(Text)
	is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	is_moder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

	roles: Mapped[list["StaffRole"]] = relationship(
		back_populates="branch",
		primaryjoin="StaffBranch.id==StaffRole.branch_id"
	)
	users: Mapped[list["StaffUserRole"]] = relationship(
		back_populates="branch",
		primaryjoin="StaffBranch.id==StaffUserRole.branch_id"
	)
	curations: Mapped[list["StaffCuration"]] = relationship(
		back_populates="branch",
		primaryjoin="StaffBranch.id==StaffCuration.branch_id"
	)

class StaffRole(Base):
	__tablename__ = 'staff_roles'
	id: Mapped[discord_identificator_pk]
	layer: Mapped[int] = mapped_column(Integer, nullable=False)
	staff_salary: Mapped[int] = mapped_column(Integer, nullable=False)
	branch_id: Mapped[int] = mapped_column(ForeignKey('staff_branches.id', ondelete='CASCADE'))

	branch: Mapped["StaffBranch"] = relationship(
		back_populates="roles",
		primaryjoin="StaffRole.branch_id==StaffBranch.id"
	)
	users: Mapped[list["StaffUserRole"]] = relationship(
		back_populates="role",
		primaryjoin="StaffRole.id==StaffUserRole.role_id"
	)

class StaffUser(Base):
	__tablename__ = 'staff_users'
	id: Mapped[discord_identificator_pk]

	roles: Mapped[list["StaffUserRole"]] = relationship(back_populates="user")
	curators: Mapped[list["StaffCuration"]] = relationship(
		back_populates="apprentice",
		primaryjoin="StaffUser.id==StaffCuration.apprentice_id"
	)
	apprentices: Mapped[list["StaffCuration"]] = relationship(
		back_populates="curator",
		primaryjoin="StaffUser.id==StaffCuration.curator_id"
	)


class StaffUserRole(Base):
	__tablename__ = 'staff_users_roles'
	id: Mapped[identificator_pk]
	user_id: Mapped[int] = mapped_column(ForeignKey('staff_users.id', ondelete='CASCADE'))
	role_id: Mapped[int] = mapped_column(ForeignKey('staff_roles.id', ondelete='CASCADE'))
	branch_id: Mapped[int] = mapped_column(ForeignKey('staff_branches.id', ondelete='CASCADE'))
	description: Mapped[str | None] = mapped_column(Text)
	update_time: Mapped[float] = mapped_column(Float,
		server_default=text("EXTRACT(EPOCH FROM NOW())"), 
		server_onupdate=text("EXTRACT(EPOCH FROM NOW())")
	)

	user: Mapped["StaffUser"] = relationship(back_populates="roles")
	branch: Mapped["StaffBranch"] = relationship(back_populates="users")
	role: Mapped["StaffRole"] = relationship(back_populates="users")
	
	__table_args__ = (
		UniqueConstraint('user_id', 'branch_id', name='uq_user_branch'),
	)

	@classmethod
	async def create_with_auto_branch(cls, session, user_id: int, role_id: int, **kwargs):
		# Получаем роль
		role = await session.get(StaffRole, role_id)
		if not role:
			raise ValueError("Роль не найдена")

		return cls(user_id=user_id, role_id=role_id, branch_id=role.branch_id, **kwargs)


class StaffCuration(Base):
	__tablename__ = 'staff_curation'
	id: Mapped[identificator_pk]
	apprentice_id: Mapped[int] = mapped_column(ForeignKey('staff_users.id', ondelete='CASCADE'))
	curator_id: Mapped[int] = mapped_column(ForeignKey('staff_users.id', ondelete='CASCADE'))
	branch_id: Mapped[int] = mapped_column(ForeignKey('staff_branches.id', ondelete='CASCADE'))

	apprentice: Mapped["StaffUser"] = relationship(
		back_populates="curators",
		foreign_keys=[apprentice_id]
	)
	curator: Mapped["StaffUser"] = relationship(
		back_populates="apprentices",
		foreign_keys=[curator_id]
	)
	branch: Mapped["StaffBranch"] = relationship(back_populates="curations")
	
	__table_args__ = (
		UniqueConstraint('apprentice_id', 'curator_id', 'branch_id', name='uq_apprentice_curator_branch'),
	)


all_data = {
	'base': Base
}