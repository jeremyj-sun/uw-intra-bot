'''
Class adapted from adamsbytes/python-discord-events.md
https://gist.github.com/adamsbytes/8445e2f9a97ae98052297a4415b5356f

Additions:
Rate limiting for all functions
send_guild_message function
'''

import json
import aiohttp
import time
import textwrap

DEBUG = False
ERROR_CODES = {
    'GUILD_SCHEDULED_EVENT_SCHEDULE_PAST': 50035
}

class DiscordEvents:
    '''Class to create and list Discord events utilizing their API'''
    def __init__(self, discord_token: str, bot_id: str) -> None:
        self.base_api_url = 'https://discord.com/api/v8'
        self.auth_headers = {
            'Authorization':f'Bot {discord_token}',
            'User-Agent': f'DiscordBot (https://discord.com/developers/applications/{bot_id}/bot) Python/3.9 aiohttp/3.8.1',
            'Content-Type':'application/json'
        }

    async def list_guild_events(self, guild_id: str) -> list:
        '''Returns a list of upcoming events for the supplied guild ID
        Format of return is a list of one dictionary per event containing information.'''
        event_retrieve_url = f'{self.base_api_url}/guilds/{guild_id}/scheduled-events'
        response_list = []
        async with aiohttp.ClientSession(headers=self.auth_headers) as session:
            status = 429
            while status == 429:
                try:
                    async with session.get(event_retrieve_url) as response:
                        if response.status == 429:
                            if DEBUG:
                                print('DETECTED RATE LIMIT in LIST function')
                            reset_time = float(response.headers['X-RateLimit-Reset-After']) + 0.25
                            time.sleep(reset_time)    
                            continue
                        elif response.status == 200:
                            response_list = json.loads(await response.read())
                            break
                        else:
                            raise Exception('Unknown error occured in list_guild_events')
                except aiohttp.ClientResponseError as e:
                    if (e.status != 429):
                        await session.close()
                        raise e
                except Exception as e:
                    print(e)
            await session.close()
        return response_list
    
    async def delete_guild_events(self, guild_id: str) -> None:
        '''Deletes all guild events labelled with GAME DAY.'''
        try:
            events = await self.list_guild_events(guild_id)
            async with aiohttp.ClientSession(headers=self.auth_headers) as session:
                for e in events:
                    if 'GAME DAY' in e['name']:
                        event_delete_url = f'{self.base_api_url}/guilds/{guild_id}/scheduled-events/{e["id"]}'
                        status = 429
                        while status == 429:
                            async with session.delete(event_delete_url) as response:
                                if response.status == 429:
                                    if DEBUG:
                                        print('DETECTED RATE LIMIT in DELETE function')
                                    reset_time = float(response.headers['X-RateLimit-Reset-After']) + 0.25
                                    time.sleep(reset_time)    
                                    continue
                                elif response.status == 204:
                                    break
                                else:
                                    raise Exception('Unknown error occured in delete_guild_events')
        except aiohttp.ClientResponseError as e:
            if (e.status != 429):
                await session.close()
                raise e
        except Exception as e:
            print(e)
        finally:
            await session.close()

    async def send_guild_message(
        self,
        channel_id: str,
        event_link: str
        ) -> None:
        '''
        Sends the event link to a text channel
        '''

        message_content = textwrap.dedent(f'''
        @everyone
        {event_link}
        ''')
        message_url = f'{self.base_api_url}/channels/{channel_id}/messages'
        message_data = json.dumps({
            'content': message_content,
            'tts': False
        })
        async with aiohttp.ClientSession(headers=self.auth_headers) as session:
            status = 429
            while status == 429:
                try:
                    async with session.post(message_url, data=message_data) as response:
                        if response.status == 429:
                            if DEBUG:
                                print('DETECTED RATE LIMIT in SEND function')
                            reset_time = float(response.headers['X-RateLimit-Reset-After']) + 0.25
                            time.sleep(reset_time)    
                            continue
                        elif response.status == 200:
                            break
                        else:
                            raise Exception('Unknown error occured in send_guild_message')
                except aiohttp.ClientResponseError as e:
                    if (e.status != 429):
                        await session.close()
                        raise e
                except Exception as e:
                    print(e)
        await session.close()

    async def create_guild_event(
        self,
        guild_id: str,
        event_name: str,
        event_description: str,
        event_start_time: str,
        event_end_time: str,
        event_metadata: dict,
        event_privacy_level=2,
        channel_id=None
    ) -> str:
        '''Creates a guild event using the supplied arguments
        The expected event_metadata format is event_metadata={'location': 'YOUR_LOCATION_NAME'}
        The required time format is %Y-%m-%dT%H:%M:%S
        Returns an event link if the event was successfully scheduled, otherwise returns an empty string'''
        event_create_url = f'{self.base_api_url}/guilds/{guild_id}/scheduled-events'
        event_data = json.dumps({
            'name': event_name,
            'privacy_level': event_privacy_level,
            'scheduled_start_time': event_start_time,
            'scheduled_end_time': event_end_time,
            'description': event_description,
            'channel_id': channel_id,
            'entity_metadata': event_metadata,
            'entity_type': 3
        })
        event_link = ''
        async with aiohttp.ClientSession(headers=self.auth_headers) as session:
            status = 429
            while status == 429:
                try:
                    async with session.post(event_create_url, data=event_data) as response:
                        if response.status == 429:
                            if DEBUG:
                                print('DETECTED RATE LIMIT in CREATE function')
                            reset_time = float(response.headers['X-RateLimit-Reset-After']) + 0.25
                            time.sleep(reset_time)    
                            continue
                        elif response.status == 200:
                            print(f'Event \'{event_name}\' successfully created')
                            response_json = json.loads(await response.read())
                            event_link = f"https://discord.com/events/{response_json['guild_id']}/{response_json['id']}"
                            break
                        else:
                            response_json = await response.json()
                            if DEBUG:
                                print(json.dumps(response_json))
                            if 'code' in response_json and response_json['code'] == ERROR_CODES['GUILD_SCHEDULED_EVENT_SCHEDULE_PAST']:
                                return ''
                            else: 
                                raise Exception('Unknown error occured in create_guild_event')
                except aiohttp.ClientResponseError as e:
                    if (e.status != 429):
                        await session.close()
                        raise e
                except Exception as e:
                    print(e)
        await session.close()
        return event_link
