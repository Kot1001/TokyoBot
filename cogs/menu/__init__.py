from __future__ import annotations

import json
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from . import switch
from configs import config

if TYPE_CHECKING:
    from main import TokyoBot


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class MenuCog(commands.GroupCog, name='-mnu-', description="Управление меню"):
    def __init__(self, bot: TokyoBot):
        self.bot = bot
        self.db_connections = self.bot.db_connections

        self.reg_db = self.db_connections['passports']
        self.save_db = self.db_connections['saves']

        self.bot.add_view(switch.EnterButtonView(self.bot, self.db_connections))
        self.bot.add_view(switch.ExitButtonView(self.bot, self.db_connections))

    # @app_commands.command(name='переключение', description="Переключение РП/Нон-РП")
    # @app_commands.default_permissions(administrator=True)
    # @app_commands.choices(
    #     place=[
    #         app_commands.Choice(name='вход', value='enter'),
    #         app_commands.Choice(name='выход', value='exit')
    #     ]
    # )
    # @app_commands.rename(place='расположение')
    # async def switch(self, interaction: discord.Interaction, place: str):
    #     await interaction.response.defer(thinking=True)
    #
    #     if place not in ('enter', 'exit'):
    #         return
    #
    #     if place == 'enter':
    #         embed = config.rp_embed
    #         view = switch.EnterButtonView(self.bot, self.db_connections)
    #     elif place == 'exit':
    #         embed = discord.Embed(
    #             title="Для выхода из РП нажмите кнопку ниже",
    #             description="||*Все роли сохранятся*||",
    #             color=discord.Color.from_str('#f04747')
    #         )
    #         view = switch.ExitButtonView(self.bot, self.db_connections)
    #
    #     await interaction.followup.send(view=view, embed=embed)
    #
    # @app_commands.command(name='управление_рп', description="Закрытие/открытие РП зоны")
    # @app_commands.default_permissions(administrator=True)
    # @app_commands.choices(action=[
    #     app_commands.Choice(name='закрыть', value='close'),
    #     app_commands.Choice(name='открыть', value='open'),
    # ])
    # @app_commands.rename(action='действие')
    # async def rp_control(self, interaction: discord.Interaction, action: str):
    #     await interaction.response.defer(ephemeral=True, thinking=True)
    #
    #     channel = self.bot.get_channel(config.rp_channel)
    #     last_message = await channel.fetch_message(channel.last_message_id)
    #
    #     if action == 'close':
    #         embed = discord.Embed(title="🛑 Проводятся технические работы, ожидайте 🛑",
    #                               color=discord.Color.from_str('#f04747'))
    #
    #         await last_message.edit(embed=embed, view=None)
    #
    #         async with self.save_db.execute(
    #                 'SELECT member_id, non_rp_ids FROM saves WHERE status = ?', ('rp',)
    #         ) as cursor:
    #             for row in await cursor.fetchall():
    #                 member = interaction.guild.get_member(row['member_id'])
    #                 rp_roles = member.roles
    #
    #                 await member.remove_roles(*rp_roles)
    #                 await member.add_roles(
    #                     *[interaction.guild.get_role(role) for role in json.loads(row['non_rp_ids'])])
    #
    #                 await self.save_db.execute(
    #                     'UPDATE saves SET (status, rp_ids) = (?, ?, ?) WHERE member_id = ?',
    #                     ('non_rp', json.dumps([role.id for role in rp_roles]), member.id)
    #                 )
    #                 await self.save_db.commit()
    #
    #         await interaction.followup.send(content="РП закрыто")
    #     elif action == 'open':
    #         view = switch.EnterButtonView(self.bot, self.db_connections)
    #         await last_message.edit(embed=config.rp_embed, view=view)
    #
    #         await interaction.followup.send(content="РП открыто")


async def setup(bot: TokyoBot):
    await bot.add_cog(MenuCog(bot), guild=config.GUILD)
