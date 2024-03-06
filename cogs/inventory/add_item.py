import json
import re

import aiosqlite
import discord
from discord import ui

from configs import config


class FormView(ui.View):
    def __init__(
            self,
            embed: discord.Embed,
            forms_indexes: dict[str, int],
            item_type: str,
            db_connections: dict[str, aiosqlite.Connection],
            original_message: discord.Message
    ):
        super().__init__(timeout=120.0)

        self.forms_indexes = forms_indexes
        self.item_type = item_type
        self.inv_db = db_connections['inv_db']
        self.original_message = original_message

        self.embed = embed
        self.db_info = {}

        select = ParamsSelect(config.types[item_type]['forms'])
        select.row = 0
        self.add_item(select)

    @ui.button(style=discord.ButtonStyle.green, label="Создать", custom_id='accept_button', disabled=True, row=1)
    async def accept_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        modal = TagModal(self.inv_db, self.item_type, self.db_info)
        await interaction.response.send_modal(modal)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.original_message.edit(view=self)


class ParamsSelect(ui.Select['AddItemView']):
    def __init__(self, forms: list[str]):
        super().__init__(
            placeholder="Выберите параметр...",
            options=[
                discord.SelectOption(label=config.forms[tag]['name'], value=tag) for tag in forms
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        component = config.forms[self.values[0]]['component']

        if component in config.components_types['modal']:
            modal = FormsModal(
                config.modals_types[component],
                self.view,
                self.values[0]
            )

            await interaction.response.send_modal(modal)
        elif component in config.components_types['view']:
            ...


class Modals(ui.Modal):
    def __init__(self, params: dict[str]):
        super().__init__(title="Создание предмета")

        self.regex = params['regex']

        self.response = ui.TextInput(
            label="Введите значение",
            style=params['style'],
            placeholder=params['placeholder'],
            max_length=params['max_length']
        )
        self.add_item(self.response)

    async def interaction_check(self, interaction: discord.Interaction):
        if self.regex is None:
            return True

        check = bool(re.match(self.regex, self.response.value))

        if not check:
            await interaction.response.edit_message()
            await interaction.followup.send("Некорректное значение", ephemeral=True)

        return check


class FormsModal(Modals):
    def __init__(self, params: dict[str], parent_view: FormView, form_tag: str):
        super().__init__(params=params)

        self.parent_view = parent_view
        self.form_tag = form_tag

    async def on_submit(self, interaction: discord.Interaction):
        view = self.parent_view
        view.embed.set_field_at(
            index=view.forms_indexes[self.form_tag],
            name=config.forms[self.form_tag]['name'],
            value=self.response.value,
            inline=False
        )
        view.db_info[self.form_tag] = self.response.value

        if all(key in view.db_info for key in config.types[view.item_type]['forms']):
            view.accept_button_callback.disabled = False

        await interaction.response.edit_message(view=view, embed=view.embed)


class TagModal(Modals):
    def __init__(self, inv_db: aiosqlite.Connection, item_type: str, db_info: dict[str]):
        super().__init__(params=config.modals_types['tag_modal'])

        self.inv_db = inv_db
        self.item_type = item_type
        self.db_info = db_info

    async def interaction_check(self, interaction: discord.Interaction):
        if not await super().interaction_check(interaction):
            return False

        async with self.inv_db.execute(
                'SELECT rowid FROM items_objects WHERE tag = ?',
                (self.response.value,)
        ) as cursor:
            row = await cursor.fetchone()

            if row:
                await interaction.response.edit_message()
                await interaction.followup.send("Тэг уже используется", ephemeral=True)
                return False

            return True

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None)

        characteristics = config.types[self.item_type]['forms']
        characteristics = {key: self.db_info[key] for key in characteristics}

        await self.inv_db.execute(
            'INSERT INTO items_objects (tag, type, characteristics) VALUES (?, ?, ?)',
            (self.response.value, self.item_type, json.dumps(characteristics))
        )
        await self.inv_db.commit()

        await interaction.followup.send("Предмет добавлен в пул", ephemeral=True)


class FormsView(ui.View):
    ...
