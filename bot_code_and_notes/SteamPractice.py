import os
from dotenv import load_dotenv

load_dotenv()
from steam_web_api import Steam
from DBpractice import *

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

user = steam.users.get_owned_games("76561198965639452")
# for game in user['games']:
#     print(game)
user = steam.users.get_user_details("76561198965639452")
#game = user['games'][0]['name']
#print(user)

# game_id = user['games'][0]['appid']
# game_info = steam.apps.get_app_details(game_id)
# for key in game_info[f'{game_id}']['data']:
#     print(key)

def print_price():
    title = 2246340
    game = steam.apps.get_app_details(title,None,"price_overview")
    pricef = game['{}'.format(title)]['data']['price_overview']['final_formatted']
    return pricef

def verify_steam_access(steam_id : str):
    user = steam.users.get_user_details(steam_id)
    # The user was not found
    if user['player'] == None:
        return 1, None
    
    # The user's profile is not private
    if user['player']['communityvisibilitystate'] != 3:
        return 2, user['player']['personaname']

    return 0, user['player']['personaname']

def add_steam_game_library(steam_id : str, conn, cur):
    steam_library = steam.users.get_owned_games(steam_id)
    return steam_library

def get_steam_image(appid : int):
    details = steam.apps.get_app_details(appid)
    if details[f'{appid}']['success']:
        image = details[f'{appid}']['data']['header_image']
        return image

    return None
    
if __name__ == "__main__":
    link_steam_library(add_steam_game_library("76561198965639452",None,None))
    #print(add_steam_game_library("76561198965639452",None,None))