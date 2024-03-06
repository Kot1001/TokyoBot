from configs import config

from datetime import datetime, timezone
from typing import Optional
import os

import aiosqlite
import pyowm

import discord
from discord.ext import commands, tasks


class TokyoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=config.PREFIX, intents=discord.Intents.all(), help_command=None)

        owm_config_dict = pyowm.owm.cfg.get_default_config()
        owm_config_dict['language'] = 'ru'
        self.owm = pyowm.OWM(config.OWM_API_KEY, owm_config_dict)

        self.db_connections: Optional[dict[str, aiosqlite.Connection]] = None

    @property
    async def _db_connections(self) -> dict[str, aiosqlite.Connection]:
        db_connections = {}
        for filename in config.DATABASES:
            connection = await aiosqlite.connect(f'databases/{filename}.db')
            connection.row_factory = aiosqlite.Row

            db_connections[filename] = connection

        return db_connections

    async def _load_cogs(self):
        for name in config.EXTENSIONS:
            await self.load_extension(f'cogs.{name}')
            print(f'Расширение "{name}" загружено')

    async def on_ready(self):
        self.db_connections = await self._db_connections

        await self._load_cogs()
        await self.tree.sync()

        print(f'Бот {self.user} запущен')

    # @tasks.loop(minutes=1)
    # async def presence(self):
    #     # TODO: Перевести в конфиг и сделать нормальный обработчик
    #     # TODO: Переделать цикл под ресоздание
    #     if self.presence.current_loop % 6 == 0:
    #         weather = self.owm.weather_manager()
    #         weather = weather.weather_at_place('Tokyo,JP').weather
    #
    #         feels_like = int(weather.temperature('celsius')['feels_like'])
    #
    #         name = f"погоду: {feels_like}°C ({str(weather.detailed_status).capitalize()})"
    #     else:
    #         current_time = datetime.now(timezone.utc).strftime('%H:%M')
    #
    #         name = f"на время: {current_time}"
    #
    #     await self.change_presence(
    #         activity=discord.Activity(
    #             type=discord.ActivityType.watching,
    #             name=name
    #         )
    #     )


bot = TokyoBot()
bot.run(config.TOKEN)

# TODO: Переделать передачу подключений к датабазам обратно на парметральный метод
