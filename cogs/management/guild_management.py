from configs import config, GUILD_CONFIG

import utils

import asyncio
import datetime
import string
from typing import TYPE_CHECKING, Optional, Collection
import json

import aiosqlite

import discord
from discord import app_commands, ui, utils
from discord.ext import commands, tasks
from discord.abc import Snowflake

if TYPE_CHECKING:
    from main import TokyoBot


# class TravelView(ui.View):
#     def __init__(self, db_connections: dict[str, aiosqlite.Connection], destination: str):
#         super().__init__(timeout=None)
#
#         self.add_item(TravelSelect(db_connections['save_db'], destination))


# class TravelSelect(ui.Select):
#     def __init__(self, save_db: aiosqlite.Connection, destination: str):
#         super().__init__(placeholder="Место назначения...", custom_id=destination)
#
#         self.save_db = save_db
#
#         self.location_params = GUILD_CONFIG.destinations[destination]
#
#         for destination_key in self.location_params['duration']:
#             destination_info = GUILD_CONFIG.destinations[destination_key]
#             district_info = GUILD_CONFIG.districts_info[destination_info['district']]
#
#             self.append_option(
#                 discord.SelectOption(
#                     label=destination_info['name'],
#                     value=destination_key,
#                     description=district_info['description'],
#                     emoji=district_info['emoji']
#                 )
#             )
#
#     async def interaction_check(self, interaction: discord.Interaction) -> bool:
#         transport = GUILD_CONFIG.transports[self.location_params['transport']]
#         ticket_role = GUILD_CONFIG.travels_waiting_role[transport['ticket']]
#
#         check = ticket_role in interaction.user.roles
#
#         if not check:
#             await interaction.response.send("Билет отсутствует", ephemeral=True)
#
#         return check
#
#     async def _departure(
#             self,
#             member: discord.Member,
#             add_roles: Collection[Snowflake],
#             remove_roles: Collection[Snowflake]
#     ):
#         await self.save_db.execute(
#             'UPDATE saves SET rp_ids = ? WHERE member_id = ?',
#             (json.dumps(utils.roles_to_ids(member.roles[1:])), member.id)
#         )
#         await self.save_db.commit()
#
#         await utils.toggle_roles(
#             member=member,
#             add_roles=add_roles,
#             remove_roles=remove_roles,
#             reason="Отправка"
#         )
#
#     @staticmethod
#     async def _travel(
#             member: discord.Member,
#             duration: int,
#             transport_emoji: str,
#             start_destination_name: str,
#             final_destination_name: str,
#     ):
#         timestamp = datetime.datetime.now() + datetime.timedelta(minutes=duration)
#
#         await member.send(
#             content=f"{transport_emoji} `{start_destination_name} > {final_destination_name}`: "
#                     f"прибытие {utils.format_dt(timestamp, 'R')}",
#             delete_after=duration * 60 - 1
#         )
#
#     async def _arrival(
#             self,
#             member: discord.Member,
#             add_roles: Collection[Snowflake],
#             remove_roles: Collection[Snowflake]
#     ):
#         await utils.toggle_roles(
#             member=member,
#             add_roles=add_roles,
#             remove_roles=remove_roles,
#             reason="Прибытие"
#         )
#
#         await self.save_db.execute(
#             'UPDATE saves SET rp_ids = ? WHERE member_id = ?',
#             (json.dumps([role.id for role in member.roles[1:]]), member.id)
#         )
#         await self.save_db.commit()
#
#         await member.send(content="Вы прибыли!", delete_after=10)
#
#     async def callback(self, interaction: discord.Interaction):
#         await interaction.response.defer(ephemeral=True)
#
#         start_destination = GUILD_CONFIG.destinations[self.custom_id]
#
#         waiting_role = GUILD_CONFIG.travels_waiting_role
#
#         await self._departure(
#             member=interaction.user,
#             add_roles=[waiting_role],
#             remove_roles=[*GUILD_CONFIG.districts_roles[start_destination['district']], GUILD_CONFIG.citizen_role]
#         )
#
#         duration = start_destination['duration'][self.values[0]]
#         final_destination = GUILD_CONFIG.destinations[self.values[0]]
#
#         await self._travel(
#             member=interaction.user,
#             duration=duration,
#             transport_emoji=GUILD_CONFIG.transports[start_destination['transport']]['emoji'],
#             start_destination_name=start_destination['name'],
#             final_destination_name=final_destination['name']
#         )
#
#         await self._arrival(
#             member=interaction.guild.get_member(interaction.user.id),
#             add_roles=[*GUILD_CONFIG.districts_roles[final_destination['district']], GUILD_CONFIG.citizen_role],
#             remove_roles=[GUILD_CONFIG.ticket_roles[start_destination['transport']], waiting_role]
#         )


class EnterButtonView(ui.View):
    def __init__(self, bot: commands.Bot, db_connections: dict[str, aiosqlite.Connection]):
        super().__init__(timeout=None)
        self.bot = bot

        self.reg_db = db_connections['reg_db']
        self.save_db = db_connections['save_db']
        self.inv_db = db_connections['inv_db']

    @ui.button(custom_id='enter', label='Войти в РП', style=discord.ButtonStyle.green)
    async def callback(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()

        async with self.reg_db.execute(
                'SELECT name, surname FROM accepted WHERE member_id = ?',
                (interaction.user.id,)
        ) as cursor:
            row = await cursor.fetchone()
            await interaction.user.edit(nick=f"{row['name']} {row['surname']}")

        async with self.save_db.execute(
                'SELECT status, rp_ids FROM saves WHERE member_id = ?',
                (interaction.user.id,)
        ) as cursor:
            row = await cursor.fetchone()
            member_roles = interaction.user.roles[1:]

            if row and row['status'] == 'non_rp':
                await interaction.user.edit(roles=utils.ids_to_roles(interaction.guild, json.loads(row['rp_ids'])))

                await self.save_db.execute(
                    'UPDATE saves SET (status, non_rp_ids, non_rp_nick) = (?, ?, ?) WHERE member_id = ?',
                    ('rp', json.dumps(utils.roles_to_ids(member_roles)), interaction.user.nick, interaction.user.id)
                )
            else:
                await interaction.user.edit(roles=[interaction.guild.get_role(ob) for ob in config.rp_default_roles])

                await self.save_db.execute(
                    'INSERT INTO saves VALUES (?, ?, ?, ?, ?)',
                    (
                        interaction.user.id,
                        'rp',
                        json.dumps(config.rp_default_roles),
                        json.dumps(utils.roles_to_ids(member_roles)),
                        interaction.user.nick
                    )
                )

                await self.inv_db.execute('INSERT INTO inventory (member_id) VALUES (?)', (interaction.user.id,))
                await self.inv_db.commit()

            await self.save_db.commit()


class ExitButtonView(ui.View):
    def __init__(self, bot: commands.Bot, db_connections: dict[str, aiosqlite.Connection]):
        super().__init__(timeout=None)
        self.bot = bot

        self.save_db = db_connections['save_db']

    @ui.button(custom_id='exit', label='Выйти из РП', style=discord.ButtonStyle.red)
    async def callback(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()

        async with self.save_db.execute(
                'SELECT status, non_rp_nick, non_rp_ids FROM saves WHERE member_id = ?',
                (interaction.user.id,)
        ) as cursor:
            row = await cursor.fetchone()

            if not row or row['status'] != 'rp':
                return

            await interaction.user.edit(nick=row['non_rp_nick'])

            member_roles = interaction.user.roles[1:]
            await interaction.user.edit(roles=utils.ids_to_roles(interaction.guild, json.loads(row['non_rp_ids'])))

            await self.save_db.execute(
                'UPDATE saves SET (status, rp_ids) = (?, ?) WHERE member_id = ?',
                ('non_rp', json.dumps(utils.roles_to_ids(member_roles)), interaction.user.id)
            )
            await self.save_db.commit()


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class GuildCog(commands.GroupCog, name='-gld-', description="Команды для управления элементами сервера"):
    def __init__(self, bot: TokyoBot):
        self.bot = bot
        self.db_connections = self.bot.db_connections

        self.reg_db = self.db_connections['reg_db']
        self.save_db = self.db_connections['save_db']

        self.last_run = None
        # self.db_autoclean.start()

        # for destination in config.destinations:
        #     self.bot.add_view(TravelView(self.db_connections, destination))
        self.bot.add_view(EnterButtonView(self.bot, self.db_connections))
        self.bot.add_view(ExitButtonView(self.bot, self.db_connections))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with self.save_db.execute('SELECT non_rp_ids FROM saves WHERE member_id = ?', (member.id,)) as cursor:
            if row := await cursor.fetchone():
                await member.edit(
                    roles=utils.ids_to_roles(member.guild, json.loads(row['non_rp_ids'])),
                    bypass_verification=True
                )
            else:
                await member.edit(roles=[member.guild.get_role(config.registration_role_id)])

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        cleanup = utils.DatabaseCleanup(
            self.bot,
            member.guild,
            self.db_connections,
            config.passports_channel,
            config.requests_channel
        )
        await cleanup.delete_temporary(member.id)

    # @tasks.loop(hours=24)
    # async def db_autoclean(self):
    #     last_run_date = self.last_run
    #     today = datetime.date.today()
    #
    #     if last_run_date is None or (last_run_date.month != today.month and today.day == 1):
    #         cleanup = utils.DatabaseCleanup(
    #             self.bot,
    #             self.bot.guild,
    #             self.db_connections,
    #             config.passports_channel,
    #             config.requests_channel
    #         )
    #         await cleanup.full_cleanup()
    #
    #     self.last_run = today
    #
    # @db_autoclean.before_loop
    # async def before_db_autoclean(self):
    #     await self.bot.wait_until_ready()

    # @app_commands.command(name='перемещение', description="Меню для перемещений")
    # @app_commands.default_permissions(administrator=True)
    # @app_commands.describe(destination="Выбор станции/пристани")
    # @app_commands.rename(destination='точка')
    # async def travel(self, interaction: discord.Interaction, destination: str):
    #     await interaction.response.defer(thinking=True, ephemeral=True)
    #
    #     if destination not in set(config.destinations.keys()):
    #         await interaction.followup.send("Точка не найдена", ephemeral=True)
    #         return
    #
    #     selected_destination = config.destinations[destination]
    #
    #     embed = discord.Embed(
    #         color=discord.Color.from_str(config.transports[selected_destination['transport']]['color']),
    #         title="Добро пожаловать!",
    #         description='`...`'
    #     )
    #     embed.set_image(url=selected_destination["url"])
    #
    #     view = TravelView(self.db_connections, destination)
    #
    #     await interaction.delete_original_response()
    #     await interaction.channel.send(view=view, embed=embed)
    #
    # @travel.autocomplete('destination')
    # async def destination_autocomplete(
    #         self,
    #         interaction: discord.Interaction,
    #         current: str
    # ) -> list[app_commands.Choice[str]]:
    #     choices = []
    #
    #     for key, value in config.destinations.items():
    #         name = value['name']
    #
    #         if current.lower() in name.lower():
    #             choices.append(app_commands.Choice(name=name, value=key))
    #
    #     return choices

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
    #         view = EnterButtonView(self.bot, self.db_connections)
    #     elif place == 'exit':
    #         embed = discord.Embed(
    #             title="Для выхода из РП нажмите кнопку ниже",
    #             description="||*Все роли сохранятся*||",
    #             color=discord.Color.from_str('#f04747')
    #         )
    #         view = ExitButtonView(self.bot, self.db_connections)
    #
    #     await interaction.followup.send(view=view, embed=embed)

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
    #         view = EnterButtonView(self.bot, self.db_connections)
    #         await last_message.edit(embed=config.rp_embed, view=view)
    #
    #         await interaction.followup.send(content="РП открыто")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context):
        fmt = await ctx.bot.tree.sync(guild=ctx.guild)
        fmt_len = len(fmt)
        noun = utils.noun_declension(fmt_len, 'команд', 'команда', 'команды')

        await ctx.send(f"Синхронизировано {fmt_len} {noun}")
        return


async def setup(bot: TokyoBot):
    await bot.add_cog(GuildCog(bot), guild=config.GUILD)
