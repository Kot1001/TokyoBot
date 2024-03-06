from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from . import add_item
from configs import config

if TYPE_CHECKING:
    from main import TokyoBot


@app_commands.guild_only()
class InventoryCog(commands.GroupCog, name='-inv-', description="Управление инвентарём"):
    def __init__(self, bot: TokyoBot):
        self.bot = bot
        self.db_connections = self.bot.db_connections

        self.inv_db = self.db_connections['inventory']
        # bot.add_view(View(bot))

    @app_commands.command(name='добавить', description="Добавить предмет в пул")
    @app_commands.default_permissions(administrator=True)
    @app_commands.rename(item_type='тип')
    async def add_item(
            self,
            interaction: discord.Interaction,
            item_type: str,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if item_type not in config.types:
            await interaction.followup.send("Тип не найден")
            return

        type_params = config.types[item_type]
        category = config.categories[type_params['category']]

        embed = discord.Embed(
            color=discord.Color.from_str('#FFB26F'),
            title="Создание предмета"
        )
        embed.add_field(name="Тип", value=type_params['name'])
        embed.add_field(name="Категория", value=category['name'])

        forms_indexes = {}
        for form_tag in type_params['forms']:
            form = config.forms[form_tag]

            embed.add_field(name=form['name'], value="`...`", inline=False)

            forms_indexes[form_tag] = len(embed.fields) - 1

        view = add_item.FormView(
            embed,
            forms_indexes,
            item_type,
            self.db_connections,
            await interaction.original_response()
        )
        await interaction.followup.send(embed=embed, view=view)

    @add_item.autocomplete('item_type')
    async def type_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []

        for key, value in config.types.items():
            var = f'{config.categories[value["category"]]["name"]}: {value["name"]}'

            if current.lower() in var.lower():
                choices.append(app_commands.Choice(name=var, value=key))

        return choices

    # TODO: Переделать под aiosqlite
    # @app_commands.command(name='убрать', description="Тестовая команда")
    # async def remove_item(self, inter: discord.Interaction, название: str, пользователь: Optional[discord.Member]):
    #     author = inter.user if пользователь is None else пользователь
    #     db = inventory_db.get(str(author.id))
    #
    #     if not inventory_db.exists(str(author.id)) or db['inventory'] in ({}, False) or название not in db['inventory']:
    #         return await inter.response.send_message('Предмет не существует', ephemeral=True)
    #
    #     db['inventory'].pop(название)
    #     inventory_db.set(str(author.id), db)
    #
    #     await inter.response.send_message(f'{название} убран из инвентаря', ephemeral=True)
    #
    # @remove_item.autocomplete('название')
    # async def items_autocomplete(self, inter: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    #     author_id = str(inter.user.id)
    #     db = inventory_db.get(author_id)
    #     items = list(db['inventory'].keys())
    #
    #     return [
    #         app_commands.Choice(name=item, value=item)
    #         for item in items if current.lower() in item.lower()
    #     ]
    #
    # @app_commands.command(name='инвентарь', description="Тестовая команда")
    # async def inventory(self, inter: discord.Interaction, пользователь: Optional[discord.Member]):
    #     member = inter.user if пользователь is None else пользователь
    #     db = inventory_db.get(str(member.id))
    #
    #     embed = discord.Embed(color=member.accent_color or discord.Color.from_str('#73757a'),
    #                           description=f"__Свободных слотов: **{config.default_slots}**__")
    #     embed.set_author(name=f"Инвентарь {member.display_name}({member.name}#{member.discriminator})")
    #     if not inventory_db.exists(str(member.id)) or db['inventory'] in ({}, False):
    #         embed.add_field(name="​", value="​", inline=True)
    #         embed.add_field(name="​", value="<:tumbleweed:1074870519670771873> Инвентарь пуст\n​", inline=True)
    #         embed.add_field(name="​", value="​", inline=True)
    #
    #         return await inter.response.send_message(embed=embed, ephemeral=True)
    #
    #     remaining_space = config.default_slots - sum(inv_utils.stack(ob['characteristics'].get('size'),
    #                                                 ob['characteristics'].get('count'))
    #                                           for ob in db['inventory'].values())
    #     items = {key: db['inventory'][key]['characteristics'] for key in list(db['inventory'].keys())}
    #     for item in items.values():
    #         count = f" `x{item['count']}`" if item['count'] > 1 else ''
    #         description = textwrap.shorten(item['description'], width=48, placeholder='...')
    #         embed.add_field(
    #             name=f"<:slot:1069436202756882545>{inv_utils.stack(item['size'], item['count'])}: "
    #                  f"{item['name']}{count}",
    #             value=description,
    #             inline=True
    #         )
    #
    #     embed.description = f"__Свободных слотов: **{remaining_space}**__"
    #     embed.set_footer(
    #         text="Чтобы использовать предмет, увидеть полное описание и прочее, выберите только его",
    #         icon_url='https://cdn.discordapp.com/attachments/1059489105530060821/1072669072816349264/i.png'
    #     )
    #
    #     await inter.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: TokyoBot):
    await bot.add_cog(InventoryCog(bot), guild=config.GUILD)
