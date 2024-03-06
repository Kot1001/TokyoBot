import time

from . import tools

import asyncio
import contextlib
from typing import Optional, Union

import aiosqlite

import discord
from discord.ext import commands


__all__ = (
    'DatabaseCleanup',
    'is_value_in_db',
    'generate_id'
)


class DatabaseCleanup:
    def __init__(
            self,
            bot: commands.Bot,
            guild: discord.Guild,
            db_connections: dict[str, aiosqlite.Connection],
            passports_channel: discord.TextChannel,
            requests_channel: discord.TextChannel
    ):
        self.bot = bot
        self.guild = guild

        self.reg_db = db_connections['reg_db']
        self.save_db = db_connections['save_db']

        self.passports_channel = passports_channel
        self.requests_channel = requests_channel

    @staticmethod
    async def _delete_message(channel: discord.TextChannel, message_id: int):
        with contextlib.suppress(discord.NotFound):
            message = await channel.fetch_message(message_id)
            await message.delete()

    async def _cleanup_member(self, member_id: int):
        await asyncio.gather(
            self.delete_accepted(member_id),
            self.delete_temporary(member_id),
            self.delete_saves(member_id),
            tools.dm_cleanup(self.bot, self.guild.get_member(member_id))
        )

    async def delete_accepted(self, member_id: int):
        async with self.reg_db.execute(
                'SELECT guild_message FROM accepted WHERE member_id = ?',
                (member_id,)
        ) as cursor:
            if row := await cursor.fetchone():
                await self._delete_message(self.passports_channel, row[0])
                await self.reg_db.execute('DELETE FROM accepted WHERE member_id = ?', (member_id,))

    async def delete_temporary(self, member_id: int):
        async with self.reg_db.execute(
                'SELECT message_id FROM temporary WHERE member_id = ?',
                (member_id,)
        ) as cursor:
            if row := await cursor.fetchone():
                await self._delete_message(self.requests_channel, row[0])
                await self.reg_db.execute('DELETE FROM temporary WHERE member_id = ?', (member_id,))

    async def delete_saves(self, member_id: int):
        await self.save_db.execute('DELETE FROM saves WHERE member_id = ?', (member_id,))

    async def full_cleanup(self, member: Optional[Union[discord.User, discord.Member]] = None):
        if member:
            member_ids = {member.id}
        else:
            async with self.reg_db.execute('SELECT member_id FROM accepted') as cursor:
                member_ids = {row[0] for row in await cursor.fetchall()}
                member_ids -= {member.id for member in self.guild.members}

        for member_id in member_ids:
            await self._cleanup_member(member_id)

        await self.reg_db.commit()
        await self.save_db.commit()


async def is_value_in_db(db: aiosqlite.Connection, key: str, value):
    async with db.execute('SELECT name FROM sqlite_master WHERE type = "table"') as cursor:
        tables = await cursor.fetchall()

        for table in tables:
            try:
                query = f'SELECT COUNT(*) AS count FROM {table["name"]} WHERE {key} = ?'
                async with db.execute(query, (value,)) as cursor2:
                    row = await cursor2.fetchone()
                    if row['count'] > 0:
                        return True
            except aiosqlite.OperationalError:
                continue

    return False


async def generate_id(db: aiosqlite.Connection, table: str, column: str, epoch: int):
    autoincrement_cursor = await db.execute(f'INSERT INTO {table} DEFAULT VALUES')
    await db.commit()

    async with db.execute(f'SELECT {column} FROM {table} WHERE rowid = ?', (autoincrement_cursor.lastrowid,)) as cursor:
        row = await cursor.fetchone()

        timestamp = int(time.time() * 1000) - epoch

        generated_id = timestamp << (64 - 42)
        generated_id |= row['auto_increment'] % (2 ** 22)

    await db.execute(f'DELETE FROM {table} WHERE rowid = ?', (autoincrement_cursor.lastrowid,))
    await db.commit()

    return generated_id
