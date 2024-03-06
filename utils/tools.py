import asyncio
import datetime
from typing import Optional, Union, Collection

import discord
from discord.ext import commands
from discord.abc import Snowflake


__all__ = (
    'format_dt',
    'ids_to_roles',
    'roles_to_ids',
    'noun_declension',
    'can_dm_member',
    'dm_cleanup',
    'toggle_roles'
)


def format_dt(dt: datetime.datetime, style: Optional[discord.utils.TimestampStyle] = None) -> str:
    epoch = datetime.datetime(1970, 1, 1)

    if dt >= epoch:
        return discord.utils.format_dt(dt, style)

    seconds = dt - epoch
    seconds = int(seconds.total_seconds())
    return f"<t:{seconds}:{style}>" if style else f"<t:{seconds}>"


def ids_to_roles(guild: discord.Guild, ids_list: list[int]) -> list[discord.Role]:
    return [guild.get_role(role_id) for role_id in ids_list]


def roles_to_ids(role_list: list[discord.Role]) -> list[int]:
    return [role.id for role in role_list]


def noun_declension(number: int, nom_pl, nom_sg, gen_sg):
    if number in range(5, 20):
        return nom_pl
    elif 1 in (number, number % 10):
        return nom_sg
    elif {number, number % 10} & {2, 3, 4}:
        return gen_sg
    return nom_pl


async def can_dm_member(member: discord.Member):
    channel = member.dm_channel or await member.create_dm()
    return channel.permissions_for().send_messages


async def dm_cleanup(bot: commands.Bot, user: Union[discord.User, discord.Member], limit: Optional[int] = None):
    channel = user.dm_channel or await user.create_dm()
    async for message in channel.history(limit=limit):
        if message.author is bot.user:
            await message.delete()
            await asyncio.sleep(1)


async def toggle_roles(
        member: discord.Member,
        add_roles: Collection[Snowflake],
        remove_roles: Collection[Snowflake],
        reason: Optional[str] = None
) -> None:
    new_roles = set(member.roles[1:])
    new_roles.difference_update(remove_roles)
    new_roles.update(add_roles)

    await member.edit(roles=list(new_roles), reason=reason)
