import asyncio
from datetime import datetime, timedelta

from discord import DiscordEvents
from dotenv import load_dotenv
from game_fetcher import fetch_game_data

import os

DEBUG = False

def game_endtime(input_datetime: str) -> str:
    '''Returns the ISO formatted datetime string of when the game finishes'''
    original_datetime = datetime.fromisoformat(input_datetime)
    game_duration = int(os.environ.get('GAME_DURATION_HOURS'))
    new_datetime = original_datetime + timedelta(hours=game_duration)
    return new_datetime.isoformat()

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
    event_data = await fetch_game_data()
    if DEBUG:
        print(f'GAME DATA: {event_data}')

    await bot.delete_guild_events(guild_id)

    for i in range(len(event_data)):
        event = event_data[i]
        event_link = await bot.create_guild_event(
            guild_id=guild_id,
            event_name=f'GAME DAY {i+1}',
            event_description=f'{event.team1} vs. {event.team2}',
            event_start_time=event.time,
            event_end_time=game_endtime(event.time),
            event_metadata={'location': event.location},
        )
        print(event_link)
        if int(os.environ.get('SEND_ANNOUNCEMENTS')) == 1:
            await bot.send_guild_message(channel_id, event_link)

asyncio.run(main())
