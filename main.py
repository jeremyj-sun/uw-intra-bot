import asyncio
from discord import DiscordEvents
from dotenv import load_dotenv
import os

DEBUG = False

async def main():
    load_dotenv()
    discord_token = os.environ.get('DISCORD_TOKEN')
    guild_id = os.environ.get('GUILD_ID')
    channel_id = os.environ.get('CHANNEL_ID')
    bot_id = os.environ.get('BOT_ID')

    if DEBUG:
        print(discord_token)
        print(guild_id)
        print(channel_id)
        print(bot_id)

    bot = DiscordEvents(discord_token, bot_id)
    # event_data = SCRAPE_WEBPAGE FUNCTION
    # Convert datetime from local timezone to ISO standard time

    await bot.delete_guild_events(guild_id)

    event_link = await bot.create_guild_event(
        guild_id=guild_id,
        event_name='GAME DAY N',
        event_description='test description',
        event_start_time='2024-01-20T15:30:00',
        event_end_time='2024-01-20T16:30:00',
        event_metadata={'location': 'test location'},
    )
    print(event_link)

asyncio.run(main())
