# Third-party imports
import aiohttp
import json
import validators

from dataclasses import dataclass
# Standard library imports
from datetime import datetime, timezone, timedelta

from battlemetrics import Battlemetrics

with open("./json/config.json", "r") as config_file:
    config = json.load(config_file)


@dataclass
class Playerids():
    _id: int = None
    steamid: str = None
    bmid: int = None

@dataclass
class Playerstats():
    _id: int = None
    steamid: str = None
    bmid: int = None
    kills_day: int = 0
    kills_week: int = 0
    kills_two_weeks: int = 0
    deaths_day: int = 0
    deaths_week: int = 0
    deaths_two_weeks: int = 0

@dataclass
class Player():
    _id: int = None
    battlemetrics_id: int = None
    steam_id: int = None
    profile_url: str = None
    avatar_url: str = None
    player_name: str = None
    playtime: int = None
    playtime_training: int = None
    limited: bool = None
    playtime_servers:list = None


battlemetrics_token = config['tokens']['battlemetrics_token']

api = Battlemetrics(battlemetrics_token)


async def get_player_info(player_id):
    
    player = await api.player.info(player_id)
    if not player:
        return
    player = await sort_player(player)
        
    return player

async def sort_player(player: dict) -> Player:
    player_data = {}
    player_data['battlemetrics_id'] = player['data']['id']
    player_data['player_name'] = player['data']['attributes']['name']
    player_data['playtime'] = 0
    player_data['playtime_training'] = 0

    playtime_servers = []
    
    for included in player['included']:
        if included['type'] == "identifier":
            if included['attributes']['type'] == "steamID":
                player_data['steam_id'] = included['attributes']['identifier']
                if included['attributes'].get('metadata'):
                    if included['attributes']['metadata'].get('profile'):
                        player_data['avatar_url'] = included['attributes']['metadata']['profile']['avatarfull']
                        player_data['limited'] = False
                        if included['attributes']['metadata']['profile'].get('isLimitedAccount'):
                            player_data['limited'] = included['attributes']['metadata']['profile']['isLimitedAccount']
                        player_data['profile_url'] = included['attributes']['metadata']['profile']['profileurl']

        if included['type'] == "server":
            training_names = ["rtg", "aim", "ukn", "arena", "combattag", "training", "aimtrain", "train", "arcade", "bedwar", "bekermelk", "escape from rust"]
            for name in training_names:
                if name in included['attributes']['name']:
                    player_data['playtime_training'] += included['meta']['timePlayed']
            player_data['playtime'] += included['meta']['timePlayed']
            the_time = included['meta']['timePlayed'] / 3600
            the_time = round(the_time, 2)
            playtime_server = {
                'name': f"{included['attributes']['name']}",
                'time': the_time,
                'id': included['id']
            }
            playtime_servers.append(playtime_server)
    player_data['playtime'] = player_data['playtime'] / 3600
    player_data['playtime'] = round(player_data['playtime'], 2)
    player_data['playtime_training'] = player_data['playtime_training'] / 3600
    player_data['playtime_training'] = round(
        player_data['playtime_training'], 2)
    player_data['playtime_servers'] = playtime_servers
    myplayer = Player(**player_data)
    return myplayer

async def get_id_from_steam(url: str) -> int:
    """Takes the URL (well part of it) and returns a steam ID"""
    url = (
        f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?format=json&"
        f"key={config['tokens']['steam_token']}&vanityurl={url}&url_type=1"
    )
    async with aiohttp.ClientSession(
        headers={"Authorization": config['tokens']['steam_token']}
    ) as session:
        async with session.get(url=url) as r:
            response = await r.json()
    if response['response'].get('steamid'):
        return response["response"]["steamid"] if response["response"]["steamid"] else 0
    else:
        return 0


async def get_player_ids(submittedtext: str):
    steamid = 0
    if validators.url(submittedtext):
        mysplit = submittedtext.split("/")
        if mysplit[3] == "id":
            steamid = await get_id_from_steam(mysplit[4])
        if mysplit[3] == "profiles":
            steamid = mysplit[4]
    else:
        if len(submittedtext) != 17:
            return None
        steamid = submittedtext

    if not steamid:
        return None
    
    playerids = Playerids()
    if steamid:
        playerids.steamid = steamid
        results = await api.player.match_identifiers(identifier=steamid,identifier_type="steamID")
        if results.get('data'):
            playerids.bmid = results['data'][0]['relationships']['player']['data']['id']
        else:
            playerids.bmid = 0
    return playerids

async def kda_two_weeks(bmid: int) -> dict:
    weekago = datetime.now(
        timezone.utc) - timedelta(hours=168)
    weekago = str(weekago).replace("+00:00", "Z:")
    weekago = weekago.replace(" ", "T")
    url = "https://api.battlemetrics.com/activity"
    params = {
        "version": "^0.1.0",
        "tagTypeMode": "and",
        "filter[timestamp]": str(weekago),
        "filter[types][whitelist]": "rustLog:playerDeath:PVP",
        "filter[players]": f"{bmid}",
        "include": "organization,user",
        "page[size]": "100"
    }
    return await api.helpers._make_request(method="GET", url=url, data=params)


async def player_stats(bmid: int):
    kda_results = await kda_two_weeks(bmid)
    stats = Playerstats()
    if kda_results:
        if kda_results.get('data'):
            for stat in kda_results['data']:
                mytimestamp = stat['attributes']['timestamp'][:10]
                mytimestamp = datetime.strptime(mytimestamp, '%Y-%m-%d')
                days_ago = (datetime.now() - mytimestamp).days
                if stat['attributes']['data'].get('killer_id'):
                    if stat['attributes']['data']['killer_id'] == int(bmid):
                        if days_ago <= 1:
                            stats.kills_day += 1
                        if days_ago <= 7:
                            stats.kills_week += 1
                        if days_ago <= 14:
                            stats.kills_two_weeks += 1
                    else:
                        if days_ago <= 1:
                            stats.deaths_day += 1
                        if days_ago <= 7:
                            stats.deaths_week += 1
                        if days_ago <= 14:
                            stats.deaths_two_weeks += 1
    if kda_results:
        if kda_results.get('links'):
            while kda_results["links"].get("next"):
                myextension = kda_results["links"]["next"]
                kda_results = await api.helpers._make_request(method="GET", url=myextension)
                if kda_results:
                    for stat in kda_results['data']:
                        mytimestamp = stat['attributes']['timestamp'][:10]
                        mytimestamp = datetime.strptime(
                            mytimestamp, '%Y-%m-%d')
                        days_ago = (datetime.now() - mytimestamp).days
                        if stat['attributes']['data'].get('killer_id'):
                            if stat['attributes']['data']['killer_id'] == int(bmid):
                                if days_ago <= 1:
                                    stats.kills_day += 1
                                if days_ago <= 7:
                                    stats.kills_week += 1
                                if days_ago <= 14:
                                    stats.kills_two_weeks += 1
                            else:
                                if days_ago <= 1:
                                    stats.deaths_day += 1
                                if days_ago <= 7:
                                    stats.deaths_week += 1
                                if days_ago <= 14:
                                    stats.deaths_two_weeks += 1
    return stats