try:
	import aiosqlite
	import disnake
	from disnake.ext import commands
	from disnake.ext import tasks
except:
	import pip

	pip.main(['install', 'disnake'])
	pip.main(['install', 'aiosqlite'])
	import disnake
	from disnake.ext import commands
	from disnake.ext import tasks
	import aiosqlite
from typing import Optional, Union, List, Dict, Any, AsyncIterator, Tuple
from asyncio import Lock
import datetime

class DatabaseManager:
	"""Расширенное соединение с БД с поддержкой транзакций и удобных методов"""

	def __init__(self, connection: aiosqlite.Connection):
		self._connection = connection
		self._transaction_depth = 0
		self._closed = False
		self._transaction_lock = Lock()
		self.last_error = None

	@classmethod
	async def connect(cls, database: str, **kwargs) -> 'DatabaseManager':
		"""Альтернатива конструктору для подключения"""
		connection = await aiosqlite.connect(database, **kwargs)
		return cls(connection)

	async def UpdateBD(self, table: str, *, change: dict, where: dict, whereandor = "AND"):
		request = ()

		change_request = []
		for i in change.keys():
			change_request.append(f"{i} = ?")
			request = request + (change[i],)

		where_request = []
		for i in where.keys():
			where_request.append(f"{i} = ?")
			request = request + (where[i],)

		await self.execute('UPDATE {table} SET {change} WHERE {where}'
			.format(table = table, change = ", ".join(change_request), where = f" {whereandor} ".join(where_request)), request)
		return 0

	async def SelectBD(self, table: str, *, select: list = ["*"], where: dict = None, where_ops: dict = None, whereandor = "AND", order_by: str = None, limit: int = None):

		where_combined = {}
		if where:
			where_combined.update({f"{k} =": v for k, v in where.items()})
		if where_ops:
			where_combined.update(where_ops)

		request = ()
		where_clauses = ""

		for condition, value in where_combined.items():
			field_op = condition.split()
			field = field_op[0]
			op = "=" if len(field_op) == 1 else field_op[1]
			if where_clauses == "":
				where_clauses= where_clauses + f"{field} {op} ? "
			else:
				where_clauses= where_clauses + f"{whereandor} {field} {op} ? "
			request += (value,)

		query = "SELECT {select} FROM {table}".format(
			select=", ".join(select),
			table=table
		)

		if where_clauses:
			query += f" WHERE {where_clauses}"

		if order_by:
			query += f" ORDER BY {order_by}"
			
		if limit:
			query += f" LIMIT {limit}"

		async with await self.execute(query, request) as cursor:
			return [i for i in await cursor.fetchall()]

	async def GetStaffJoins():
		query = \
		"""
		SELECT sur.userid, sur.roleid, sur.description, sur.starttime, sr.staffsalary, sbr.layer as rolelayer, sbr.branchid, sb.layer as branchlayer, sb.purpose
		FROM staff_users_roles AS sur
		JOIN staff_roles as sr ON sr.roleid = sur.roleid
		JOIN staff_branches_roles as sbr ON sbr.roleid = sur.roleid
		JOIN staff_branches as sb ON sb.branchid = sbr.branchid
		ORDER BY branchlayer ASC, rolelayer ASC;
		"""
		async with await self.execute(query, request) as cursor:
			answer = [i for i in await cursor.fetchall()]
		result = [{'userid': userid, 'roleid': roleid, 'description': description, 'starttime': starttime, 'staffsalary': staffsalary, 'rolelayer': rolelayer, 'branchid': branchid, 'branchlayer': branchlayer, 'purpose': purpose} for userid, roleid, description, starttime, staffsalary, rolelayer, branchid, branchlayer, purpose in answer]
		return result

	async def DeleteBD(self, table: str, *, where: dict, whereandor = "AND"):
		request = ()
		where_request = []
		for i in where.keys():
			where_request.append(f"{i} = ?")
			request = request + (where[i],)
		await self.execute("DELETE FROM {table} where {where}"
			.format(table = table, where = f" {whereandor} ".join(where_request)), request)
		return 0

	async def InsertBD(self, table: str, *, data: dict):
		request = ()
		keys = list(data.keys())
		qstring = []
		for i in keys:
			request = request + (data[i],)
			qstring.append("?")
		await self.execute("INSERT INTO {table}({keys}) VALUES({values})"
			.format(table = table, keys = ", ".join(keys), values = ", ".join(qstring)), request)
		return 0
	
	async def execute(self, sql: str, parameters: Optional[Union[Tuple, Dict]] = None, **kwargs) -> aiosqlite.Cursor:
		"""
		Универсальный execute, который автоматически определяет:
		- Нужно ли начинать транзакцию (для INSERT/UPDATE/DELETE вне транзакции)
		- Работает ли уже внутри транзакции (не создаёт вложенные транзакции)
		"""
		is_modifying = sql.strip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
		
		# Если это модифицирующий запрос И мы НЕ внутри транзакции
		if is_modifying and self._transaction_depth == 0:
			async with self:  # Автоматические begin/commit
				cursor = await self._connection.execute(sql, parameters or (), **kwargs)
				await cursor.close()  # Важно: закрываем курсор для COMMIT
				return cursor
		else:
			# Для SELECT или работы внутри существующей транзакции
			return await self._connection.execute(sql, parameters or (), **kwargs)

	async def fetch_all(self, sql: str, parameters: Optional[Union[Tuple, Dict]] = None) -> List[Tuple]:
		"""Выполняет запрос и возвращает все строки"""
		async with await self.execute(sql, parameters) as cursor:
				return await cursor.fetchall()

	async def fetch_one(self, sql: str, parameters: Optional[Union[Tuple, Dict]] = None) -> Optional[Tuple]:
		"""Выполняет запрос и возвращает первую строку"""
		async with await self.execute(sql, parameters) as cursor:
				return await cursor.fetchone()

	async def fetch_val(self, sql: str, parameters: Optional[Union[Tuple, Dict]] = None, column: int = 0) -> Any:
		"""Возвращает значение из первого столбца"""
		row = await self.fetch_one(sql, parameters)
		return row[column] if row else None

	async def insert(self, table: str, data: Dict[str, Any], on_conflict: str = None) -> int:
		"""Упрощенный INSERT с поддержкой ON CONFLICT"""
		keys = data.keys()
		values = list(data.values())
		
		sql = f"""
		INSERT INTO {table} ({', '.join(keys)})
		VALUES ({', '.join(['?']*len(keys))})
		"""
		
		if on_conflict:
				sql += f" ON CONFLICT {on_conflict}"
				
		await self.execute(sql, values)
		return self.lastrowid

	async def update(self, table: str, where: Dict[str, Any], changes: Dict[str, Any], where_operator: str = "AND") -> int:
		"""Упрощенный UPDATE с автоматическим построением WHERE"""
		set_clause = ", ".join([f"{k} = ?" for k in changes.keys()])
		where_clause = f" {where_operator} ".join([f"{k} = ?" for k in where.keys()])
		
		sql = f"""
		UPDATE {table}
		SET {set_clause}
		WHERE {where_clause}
		"""
		
		result = await self.execute(sql, [*changes.values(), *where.values()])
		return result.rowcount

	async def begin(self):
		"""Начать транзакцию (с поддержкой вложенности)"""
		async with self._transaction_lock:
			if self._transaction_depth == 0:
				await self._connection.execute("BEGIN IMMEDIATE")
			self._transaction_depth += 1

	async def commit(self):
		"""Зафиксировать транзакцию"""
		async with self._transaction_lock:
			if self._transaction_depth == 1:
				await self._connection.commit()
			self._transaction_depth = max(0, self._transaction_depth - 1)

	async def rollback(self):
		"""Откатить транзакцию"""
		async with self._transaction_lock:
			if self._transaction_depth > 0:
				await self._connection.rollback()
			self._transaction_depth = 0

	async def close(self) -> None:
		"""Безопасное закрытие соединения с учётом транзакций"""
		async with self._transaction_lock:
			try:
				# Откатываем активную транзакцию, если есть
				if self._transaction_depth > 0:
					await self._connection.rollback()
					self._transaction_depth = 0

				# Закрываем соединение
				if hasattr(self._connection, '_connection'):  # Проверка внутреннего состояния
					await self._connection.close()
			except Exception as e:
				self.last_error = f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Ошибка при закрытии соединения: {e}"
				print(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Ошибка при закрытии соединения: {e}")
			finally:
				# Помечаем соединение как закрытое
				self._closed = True

	async def __aenter__(self):
		await self.begin()  # Используем собственный метод begin
		return self  # Возвращаем сам менеджер, а не соединение

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		if exc_type is None:
			await self.commit()
		else:
			self.last_error = f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Во время записи в бд произошла ошибка: {exc_type}({exc_val}): {exc_tb.tb_frame.f_code.co_filename}(строка {exc_tb.tb_lineno})!"
			print(f"{datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}:: Во время записи в бд произошла ошибка: {exc_type}({exc_val}): {exc_tb.tb_frame.f_code.co_filename}(строка {exc_tb.tb_lineno})!")
			await self.rollback()