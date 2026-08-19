import os
from dotenv import load_dotenv
load_dotenv()
from steam_web_api import Steam

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

def print_price():
    title = 2246340
    game = steam.apps.get_app_details(title,None,"price_overview")
    pricef = game['{}'.format(title)]['data']['price_overview']['final_formatted']
    return pricef
    