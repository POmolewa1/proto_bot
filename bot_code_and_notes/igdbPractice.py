import requests 
from dotenv import load_dotenv
import os
load_dotenv()
import logging
import datetime as dt
from datetime import timezone
import re
import unicodedata
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

def normalize_game_name(name):
    name = unicodedata.normalize("NFKD", name)
    name = name.lower()

    # Remove trademark/copyright/registered symbols
    name = name.replace("™", "")
    name = name.replace("®", "")
    name = name.replace("©", "")

    # Normalize whitespace
    name = re.sub(r"\s+", " ", name).strip()

    return name


class IGDBClient():

    def __init__(self):
        access_token = None
        access_token_expiration_date = None
        self.create_access_token()


    def create_access_token(self):
        data = {
            "client_id" : os.getenv("CLIENTID"),
            "client_secret" : os.getenv("CLIENTSECRET"),
            "grant_type" : "client_credentials"
        }

        result = requests.post("https://id.twitch.tv/oauth2/token", data = data)

        self.access_token = result.json()['access_token']

        expiration_time = result.json()['expires_in']
        self.access_token_expiration_date = dt.datetime.now(tz= timezone.utc) + (dt.timedelta(seconds=expiration_time) - dt.timedelta(minutes=5))


    def get_alt_url(self, game_name):
        if dt.datetime.now(tz= timezone.utc) >= self.access_token_expiration_date:
            self.create_access_token()
        
        header = {
            "Client-ID" : os.getenv("CLIENTID"),
            "Authorization" : f"Bearer {self.access_token}"
        }
        url = "https://api.igdb.com/v4/games"
        data = f'''search "{game_name}"; fields name, cover.url;'''

        request = requests.post(url = url, headers = header, data = data)

        # Refresh the token in the case it expires before the expiration time
        if request.status_code == 401:
            self.create_access_token()
            header = {
                "Client-ID" : os.getenv("CLIENTID"),
                "Authorization" : f"Bearer {self.access_token}"
            }
            request = requests.post(url = url, headers = header, data = data)

        result = request.json()
        if len(result) == 0:
            logger.info("Could not find any results")
            return None
        best_match = None
        best_similarity = 0

        normalized_name = normalize_game_name(game_name)

        for game in result:
            if 'cover' not in game or game['cover']['url'] is None:
                continue

            igdb_name = normalize_game_name(game['name'])

            similarity = SequenceMatcher(
                None,
                normalized_name,
                igdb_name
            ).ratio()

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = game

        
        if best_match is None:
            return None
        
        print(
                f"From IGDB Client:\n"
                f"Best match: {game_name} -> {best_match['name']} "
                f"({best_similarity:.2%})\n"
                f"url : http:{best_match['cover']['url']}"
            )
        logger.info(
                f"From IGDB Client:\n"
                f"Best match: {game_name} -> {best_match['name']} "
                f"({best_similarity:.2%})\n"
                f"url : http:{best_match['cover']['url']}"
            )

        
        img = best_match['cover']['url']

        return f"http:{img}"

# client = IGDBClient()

# url = client.get_alt_url("valorant")

# Maybe I could add the ratings to the game library

# data = {
#     "client_id" : os.getenv("CLIENTID"),
#     "client_secret" : os.getenv("CLIENTSECRET"),
#     "grant_type" : "client_credentials"
# }
# result = requests.post("https://id.twitch.tv/oauth2/token", data = data)
# print(result.json()['access_token'])


# header = {
#     "Client-ID" : os.getenv("CLIENTID"),
#     "Authorization" : f"Bearer {"rvk8gn9gi3h88inhqrbqrg1wwkvsoi"}"
# }
# url = "https://api.igdb.com/v4/games"
# #url = "https://api.igdb.com/v4/characters"

# game_name = "VALORANT"
# data = f'''search "{game_name}"; fields name, cover.url;'''

# request = requests.post(url = url, headers = header, data=data)
# #print(request.json())

# best_match = None
# best_similarity = 0

# normalized_name = normalize_game_name(game_name)

# for game in request.json():
#     steam_name = normalize_game_name(game['name'])

#     similarity = SequenceMatcher(
#         None,
#         normalized_name,
#         steam_name
#     ).ratio()

#     if similarity > best_similarity:
#         best_similarity = similarity
#         best_match = game
# print(best_match)
# print(
#         f"Best match: {game_name} -> {best_match['name']} "
#         f"({best_similarity:.2%})\n"
#         f"url : http:{best_match['cover']['url']}"
#     )


# if len(request.json()) == 0:
#     print("could not find the game")
#     if len(request.json()) != 0:
#         print(f"only found {request.json()[0]['name']}")
# else:
#     url = request.json()[0]['cover']['url']
#     print(f"http:{url}")



# def get_alterantive_url(game_name):
#     header = {
#         "Client_ID" : os.getenv("CLIENTID"),
#         "Authorization" : f"Bearer {os.getenv("IGDBTOKEN")}"
#     }
#     url = "https://api.igdb.com/v4/games"
#     data = f'''search "{game_name}"; fields cover.url; limit 1'''

#     request = requests.post(url = url, headers = header, data = data)

#     if len(request.json()) == 0:
#         logger.info("Could not find any result")
#         return None
    
#     img = request.json()[0]['cover']['url']
#     return img
