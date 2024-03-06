import json

import aiosqlite
import discord
from discord import ui
from discord.ext import commands

from configs import config
import utils


class EnterButtonView(ui.View):
    def __init__(self, bot: commands.Bot, db_connections: dict[str, aiosqlite.Connection]):
        super().__init__(timeout=None)
        self.bot = bot

        self.reg_db = db_connections['passports']
        self.save_db = db_connections['saves']
        self.inv_db = db_connections['inventory']

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

        self.save_db = db_connections['saves']

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
