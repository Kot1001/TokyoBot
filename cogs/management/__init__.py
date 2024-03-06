from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from configs import config
import utils
from . import reg

if TYPE_CHECKING:
    from main import TokyoBot


@app_commands.guild_only()
class ManagementCog(commands.GroupCog, name='-mng-', description="Управление элементами сервера"):
    def __init__(self, bot: TokyoBot):
        self.bot = bot
        self.db_connections = bot.db_connections

        self.reg_db = self.db_connections['passports']
        self.save_db = self.db_connections['saves']

        bot.add_view(reg.ButtonView(self.bot, self.db_connections))

    @commands.Cog.listener(name='on_member_join')
    async def roles_reversion(self, member: discord.Member):
        async with self.save_db.execute('SELECT non_rp_ids FROM saves WHERE member_id = ?', (member.id,)) as cursor:
            if row := await cursor.fetchone():
                await member.edit(
                    roles=utils.ids_to_roles(member.guild, json.loads(row['non_rp_ids'])),
                    bypass_verification=True
                )
            else:
                await member.edit(roles=[member.guild.get_role(config.registration_role_id)])

    @app_commands.command(name='рег', description="Команда регистрации")
    @app_commands.choices(gender=[
        app_commands.Choice(name="мужской", value='man'),
        app_commands.Choice(name="женский", value='woman')
    ])
    @app_commands.rename(age='возраст', gender='пол', link='ссылка', rate='оценка', comment='комментарий')
    async def reg(
            self,
            interaction: discord.Interaction,
            age: int,
            gender: str,
            link: str,
            rate: Optional[app_commands.Range[int, 1, 10]],
            comment: Optional[str]
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not await utils.can_dm_member(interaction.user):
            await interaction.edit_original_response(content="Ваше ЛС закрыто")
            return

        async with self.reg_db.execute(
                'SELECT rowid FROM temporary WHERE member_id = ?',
                (interaction.user.id,)
        ) as cursor:
            if await cursor.fetchone():
                await interaction.edit_original_response(content="Вы уже отправили заявку")
                return

        async with self.reg_db.execute(
                'SELECT rowid FROM accepted WHERE member_id = ?',
                (interaction.user.id,)
        ) as cursor:
            if await cursor.fetchone():
                await interaction.edit_original_response(
                    content="Вы уже зарегистрированы. Если произошла ошибка - обратитесь к администрации"
                )
                return

        await utils.dm_cleanup(self.bot, interaction.user)

        embed = discord.Embed(color=discord.Color.red())
        embed.set_author(name="Запрос на регистрацию")
        embed.add_field(name="Пользователь", value=interaction.user.mention, inline=False)
        embed.add_field(name="Возраст", value=f"{age}", inline=False)
        embed.add_field(name="Пол", value="Мужской" if gender == 'man' else "Женский", inline=False)
        embed.add_field(name="Cсылка", value=link, inline=False)
        if rate:
            embed.add_field(name="Оценка", value=f"{rate}", inline=False)
        if comment:
            embed.add_field(name="Комментарий", value=comment, inline=False)

        view = reg.ButtonView(self.bot, self.db_connections)
        message = await self.bot.get_channel(config.requests_channel).send(embed=embed, view=view)

        await self.reg_db.execute('INSERT INTO temporary VALUES (?, ?, ?)', (message.id, interaction.user.id, gender))
        await self.reg_db.commit()

        await interaction.followup.send(content="Заявка отправлена, ожидайте")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context):
        fmt = await ctx.bot.tree.sync(guild=ctx.guild)
        fmt_len = len(fmt)
        noun = utils.noun_declension(fmt_len, 'команд', 'команда', 'команды')

        await ctx.send(f"Синхронизировано {fmt_len} {noun}")
        return


async def setup(bot: TokyoBot):
    await bot.add_cog(ManagementCog(bot), guild=config.GUILD)
