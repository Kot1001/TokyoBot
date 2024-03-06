import datetime
import random

import aiosqlite
import discord
from discord import ui, utils

from configs import config
import utils


class DeclineModal(ui.Modal):
    def __init__(self, db_connections: dict[str, aiosqlite.Connection]):
        super().__init__(title="Отклонить")
        self.reg_db = db_connections['passports']

        self.reason = ui.TextInput(
            label="Причина",
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        async with self.reg_db.execute(
                'SELECT member_id FROM temporary WHERE message_id = ?',
                (interaction.message.id,)
        ) as cursor:
            row = await cursor.fetchone()
            member = interaction.guild.get_member(row['member_id'])

        if not await utils.can_dm_member(member):
            await member.kick(reason=f"{self.reason}")
            return

        await member.send(content=f"**Заявка отклонена**\nПричина: `{self.reason}`")

        await self.reg_db.execute('DELETE FROM temporary WHERE message_id = ?', (interaction.message.id,))
        await self.reg_db.commit()

        await interaction.delete_original_response()


class BanModal(ui.Modal):
    def __init__(self, db_connections: dict[str, aiosqlite.Connection]):
        super().__init__(title="Забанить")
        self.reg_db = db_connections['passports']

        self.reason = ui.TextInput(
            label="Причина",
            placeholder="(используется для аудита)",
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        async with self.reg_db.execute(
                'SELECT member_id FROM temporary WHERE message_id = ?',
                (interaction.message.id,)
        ) as cursor:
            row = await cursor.fetchone()
            member = interaction.guild.get_member(row['member_id'])

        await member.ban(reason=f'{self.reason}')

        await self.reg_db.execute('DELETE FROM temporary WHERE message_id = ?', (interaction.message.id,))
        await self.reg_db.commit()

        await interaction.delete_original_response()


class ButtonView(ui.View):
    def __init__(self, bot, db_connections: dict[str, aiosqlite.Connection]):
        super().__init__(timeout=None)
        self.bot = bot
        self.db_connections = db_connections

        self.reg_db = self.db_connections['passports']

    @ui.button(custom_id='accept', label='Принять', style=discord.ButtonStyle.green)
    async def accept_callback(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)

        async with self.reg_db.execute(
                'SELECT * FROM temporary WHERE message_id = ?',
                (interaction.message.id,)
        ) as cursor:
            row = await cursor.fetchone()

            member = interaction.guild.get_member(row['member_id'])

            if not await utils.can_dm_member(member):
                await interaction.edit_original_response(
                    content="Пользователь закрыл ЛС\nВы можете нажать кнопку \"Отклонить\" для кика пользователя")
                return

            gender = row['gender']

        pass_id = str(random.randint(1, 9999999)).zfill(7)

        owned = {
            'man': {'gender_name': "Мужской", 'owner_name': "Владелец"},
            'woman': {'gender_name': "Женский", 'owner_name': "Владелица"}
        }

        name = random.choice(config.names[gender])
        surname = random.choice(config.surnames)

        age = random.choices(
            [random.randint(18, 24), random.randint(25, 49), random.randint(50, 65)],
            weights=[5, 3, 2]
        )[0]
        birth = interaction.created_at - datetime.timedelta(
            days=age * 365 + random.randint(0, 364),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        embed = discord.Embed(
            color=discord.Color.from_str('#c30034'),
            title="Паспорт",
            description=f"{owned[gender]['owner_name']}: {member.mention}"
        )
        embed.add_field(name="Имя", value=name)
        embed.add_field(name="Фамилия", value=surname)
        embed.add_field(name="Дата рождения", value=utils.format_dt(birth), inline=False)
        embed.add_field(name="Пол", value=owned[gender]['gender_name'])
        embed.add_field(name="Город проживания", value="Токио, регион Канто, Япония")
        embed.add_field(name="Зарегистрирован", value=utils.format_dt(interaction.message.created_at, style='f'))
        embed.set_footer(text=f"ID паспорта: JP-13TYO{pass_id}")
        embed.set_image(
            url=f'''
            https://media.discordapp.net/attachments/808381913663275021/{random.choice(
                [
                    '925436267980787753/Frame_1_17.png',
                    '925481912431161394/Frame_1_20.png',
                    '925575879646662687/Frame_1_21.png',
                    '925591238663630898/Frame_1_22-min.png',
                    '925591866802581504/Frame_1_23-min.png',
                    '925591867129729034/Frame_1_24-min.png'
                ]
            )}''')
        embed.set_thumbnail(
            url='https://media.discordapp.net/attachments/1059489105530060821/1110635464089686086/Imperial_Seal.png'
        )

        dm_message = await member.send(embed=embed)
        await dm_message.pin()
        async for ob in member.dm_channel.history(after=dm_message):
            if ob.type is discord.MessageType.pins_add:
                await ob.delete()
        guild_message = await self.bot.get_channel(config.passports_channel).send(embed=embed)

        await self.reg_db.execute(
            """
            INSERT INTO accepted (member_id, name, surname, dob, gender, registered, pass_id, guild_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member.id,
                name,
                surname,
                birth.isoformat(),
                gender,
                interaction.message.created_at.isoformat(),
                pass_id,
                guild_message.id
            )
        )
        await self.reg_db.execute('DELETE FROM temporary WHERE member_id = ?', (member.id,))
        await self.reg_db.commit()

        await member.edit(roles=[interaction.guild.get_role(role_id) for role_id in config.entry_role_ids])

        await interaction.delete_original_response()

    @ui.button(custom_id='decline', label='Отклонить', style=discord.ButtonStyle.blurple)
    async def decline_callback(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(DeclineModal(self.db_connections))

    @ui.button(custom_id='ban', label='Забанить', style=discord.ButtonStyle.red)
    async def ban_callback(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BanModal(self.db_connections))
