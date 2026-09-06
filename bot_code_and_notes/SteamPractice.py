import os
from dotenv import load_dotenv

load_dotenv()
from steam_web_api import Steam
#from DBpractice import *
import datetime as dt
from datetime import timezone
from dateutil.relativedelta import relativedelta
import requests
import logging
import time

logger = logging.getLogger(__name__)
KEY = os.getenv("STEAM_API_KEY")

steam = Steam(KEY)

# user = steam.users.get_user_friends_list("76561198138082742")

# for friend in user["friends"]:
#     print(friend['personaname'])

#title = 2246340
title = 2369900
title = 930210

# game = steam.apps.get_app_details(title)
# for key in game['930210']['data']:
#     print(key)

#game = steam.apps.get_app_details(title,None,"price_overview")
# game = steam.apps.get_app_details(title)
# for key in game[f"{title}"]["data"]:
#     print(key)
# for x in game['{}'.format(title)]['data']:
#     print(x)

# game = steam.apps.search_games("Castlevania Dominus Collection")
# print(game)
# id = 2369900
# game = steam.apps.search_games("Helldivers 2")
# print(game)

# user_games = steam.users.get_user_details("76561198868092917")
#user_games = steam.users.search_user("GethUprising")
# user_games = steam.users.get_owned_games("76561198868092917")
# print(user_games)

# try:
#     user_games = steam.apps.get_user_achievements("76561198658552885","3224770")
#     print(user_games)
# except Exception as e:
#     print(e)
# for game in user_games['games']:
#     print(game)
    # if("has_community_visible_stats" in game):
    #     print(f"{game['name']} status = {game['has_community_visible_stats']}")
    # else:
    #     print(f"{game['name']}")

# user = steam.users.get_owned_games("76561198138082742")
# for game in user['games']:
#     print(f"{game['name']} time played {game['playtime_forever']}")
# user = steam.users.get_user_details("76561198965639452")
#game = user['games'][0]['name']
# print(user)

# game_id = user['games'][0]['appid']
# game_id = 930210
#game_info = steam.apps.get_app_details(game_id)
# game_info = steam.apps.search_games("Warhammer: Vermintide 2")
# print(game_info['apps'][0])
# for key in game_info[f'{game_id}']['data']:
#     print(key)


# game_data = steam.apps.search_games("balls in space")
# print(game_data['apps'])
# if len(game_data['apps']) == 0:
#     print("no result")


# date_created = 1558540534
# date = dt.datetime.fromtimestamp(date_created,tz = timezone.utc)
# curr_date = dt.datetime.now(timezone.utc)
# age = relativedelta(curr_date, date)
# print(f"{age.years} years {age.months} months {age.days} days")

# user = steam.users.search_user("bob")
# if user == "No match":
#     print("user not found")
# else:
#     print(user)


# game = steam.apps.get_app_details(4866180,None,"price_overview")
# if len(game['4866180']['data']) == 0:
#     print(game)

# time = dt.timedelta(seconds=5543400)
# print(time)

# user = steam.users.get_user_recently_played_games("76561198965639452")
# print(user)

# user = steam.users.get_owned_games("76561198965639452")
# for game in user['games']:
#     if game['name'] == "hololive Dreams":
#         print(game)

# tday = dt.datetime.now(tz = timezone.utc)
# subtract = dt.timedelta(days=1)
# print(tday - subtract)

# game_info = steam.apps.search_games("Warhammer: Vermintide 2")
# print(game_info['apps'][0])

# date = dt.datetime.now(timezone.utc)
# recency_scaling = dt.timedelta(days = 3)

# d = date - recency_scaling
# print((date - d).days)

# Steam only exposes recently played games for a limited period.
# Since exact last-played dates aren't reliably available, we use
# the ordering of the first few games as an initial approximation.
# Activity tracking and autosync will replace these estimates later.


def get_game_news_from_steam(appid_user_dictionary):
    # need to return a dictionary of games to news like| Helldivers 2(id= 33333) : news(dictionary) |
    logger.info("Started looking for relevent news from Steam client")
    today = dt.datetime.now(timezone.utc)
    date_cutoff = today - dt.timedelta(days=10)
    for appid in appid_user_dictionary:
        url = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={appid}&maxlength=150&count=5"
        request = requests.get(url)
        news = request.json()
        if news is None:
            logger.info(f"No news found for appid : {appid}")
            continue

        for artice in news['appnews']['newsitems']:
            article_timestamp = artice['date']
            article_date = dt.datetime.fromtimestamp(article_timestamp, timezone.utc)
            feed_type = artice['feed_type']
            if article_date <= date_cutoff:
                break
            # also have to check if it has not already been mentioned within the last 24 hours
            if feed_type == 1:
                appid_user_dictionary[appid]['news_articles'].append(artice['url'])

    logger.info(f"All relevant news has been recorded : {appid_user_dictionary}")
    return appid_user_dictionary


#get_game_news(1)

def get_recently_played_games(steam_id):
    games = steam.users.get_user_recently_played_games(steam_id)

    if len(games) == 0:
        logger.error("User recently played list was not able to be found")
        return None
    if games['total_count'] == 0:
        return None

    return games

def check_steam_game_availability(name):
    result = steam.apps.search_games(name)

    if len(result['apps']) == 0:
        return False,None
    if result['apps'][0]['name'] != name:
        return False,None

    return True, result['apps'][0]
    

def print_price():
    title = 2246340
    game = steam.apps.get_app_details(title,None,"price_overview")
    pricef = game['{}'.format(title)]['data']['price_overview']['final_formatted']
    return pricef

def search_for_user(name):
    user = steam.users.search_user(name)
    if user == "No match":
        return 1, None

    if user['player']['communityvisibilitystate'] != 3:
        return 2, user

    return 0, user


def verify_steam_access(steam_id : str):
    user = steam.users.get_user_details(steam_id)
    # The user was not found
    if user['player'] == None:
        return 1, None
    
    # The user's profile is not private
    if user['player']['communityvisibilitystate'] != 3:
        return 2, user
    # might as well just return the whole user so we can get the profile pic

    return 0, user


def get_steam_game_library(steam_id : str):
    steam_library = steam.users.get_owned_games(steam_id)
    return steam_library


def look_up_steam_image_and_price(appid : int):
    details = steam.apps.get_app_details(appid)
    if details is None:
        for attempt in range(5):
            logger.warning(f"Could not get app info for appid : {appid} on try : {attempt}")
            time.sleep(60)
            print(f"sleep on attempt {attempt}")
            details = steam.apps.get_app_details(appid)
            if details is not None:
                break
    if details is None:
        return None, None
    
    for attempt in range(5):
        try:
            if details[f'{appid}']['success']:
                image = details[f'{appid}']['data']['header_image']
            else:
                image = None

            details = steam.apps.get_app_details(appid,None, "price_overview")
            if details is None:
                return image, None
            if details[f'{appid}']['success'] and len(details[f'{appid}']['data']) != 0:
                price = details[f'{appid}']['data']['price_overview']['initial']
            else:
                price = None

            return image, price

        except requests.exceptions.ReadTimeout as e:
            logger.warning(f"Could not get Steam data for {appid}: {e} on attempt: {attempt}")
            if attempt < 4:
                time.sleep(3)

    logger.error(f"Could not get Steam data for {appid}")
    return None,None
    
# if __name__ == "__main__":
#     pass
    #link_steam_library(add_steam_game_library("76561198965639452",None))
    #print(add_steam_game_library("76561198965639452",None,None))