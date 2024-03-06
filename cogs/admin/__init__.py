from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import utils
from configs import config


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class AdminCog(commands.GroupCog, name='-adm-', description="Утилиты для администраторов"):
    def __init__(self, bot):
        self.bot = bot
        self.db_connections = self.bot.db_connections

        self.reg_db = self.db_connections['passports']
        self.save_db = self.db_connections['saves']

    @app_commands.command(name='очистить', description="Очищает датабазы ушедших пользователей или конкретного")
    @app_commands.rename(member='пользователь')
    async def clean(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        await interaction.response.defer(thinking=True, ephemeral=True)

        cleanup = utils.DatabaseCleanup(self.bot, interaction.guild, self.db_connections)
        if member is None:
            await cleanup.full_cleanup()
            message = "Датабазы очищены"
        elif await utils.is_value_in_db(self.reg_db, 'member_id', member.id):
            await cleanup.full_cleanup(member)
            message = f"Датабазы пользователя {member.mention} очищены"
        else:
            message = f"Датабазы пользователя {member.mention} не найдены"

        await interaction.edit_original_response(content=message)

    @app_commands.command(name='выключение', description='"Мягко" завершает все процессы и выключает бота')
    async def shutdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if 'INVITES_DISABLED' not in interaction.guild.features:
            await interaction.guild.edit(invites_disabled=True)

        await interaction.followup.send(content="Завершение работы...")
        await self.bot.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot), guild=config.GUILD)
