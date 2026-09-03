import psycopg2 as db
import os 
from dotenv import load_dotenv

load_dotenv()
import logging
from SteamPractice import *
import datetime as dt
from datetime import timezone
from igdbPractice import *

logger = logging.getLogger(__name__)
#conn = db.connect(host= os.getenv("DB_HOST"), dbname=os.getenv("DB_NAME"), user=os.getenv("USER"), password=os.getenv("PASSWORD"),port=os.getenv("PORT"))
#cur = conn.cursor()
# cur.execute("""CREATE TABLE IF NOT EXISTS person (
#         id INT PRIMARY KEY,
#         name VARCHAR (255),
#         age INT,
#         gender CHAR
#     );
#     """)

#     cur.execute("""INSERT INTO person (id, name, age, gender)
#     VALUES 
#     (1, 'Steve', 43, 'M'),
#     (2, 'Mike', 23, 'M'),
#     (3, 'Patty', 29, 'F'),
#     (4, 'Sue', 63, 'F'),
#     (5, 'Lary', 52, 'M');
#     """)

#     cur.execute("""SELECT * FROM person WHERE age < 50;
#     """)

#     entries = cur.fetchall()

#     for row in entries:
#         print(row)


#     sql = cur.mogrify("""SELECT * FROM  person WHERE starts_with(name,%s) AND age < %s;""", ("J", 50))

#     cur.execute(sql)
#     for entry in cur.fetchall():
#         print(entry)

#     cur.execute("""UPDATE person
#     SET
#         name = 'Piablo',
#         age = 635,
#         gender = 'O'
#     WHERE id = 2;
#     """)

#     cur.execute("""SELECT * FROM person
#     WHERE id = 2;
#     """)
#     for entry in cur.fetchall():
#         print(entry)


#     cur.execute("""ALTER TABLE person
#     ADD COLUMN credit_score INT;
#     """)

#     cur.execute("""ALTER TABLE person
#     DROP COLUMN credit_score
#     """)

#     cur.execute("""UPDATE person
#     SET
#         credit_score = 800
#     WHERE age > 40 
#     AND (
#         starts_with(name, 'J')
#         OR starts_with(name, 'S')
#     );
#     """)

#     cur.execute("SELECT * FROM person")

#     for entry in cur.fetchall():
#         print(entry)



#conn.commit()
#cur.close()
#conn.close()

def initialize_db():
    conn,cur = create_connection()

    cur.execute("""CREATE TABLE IF NOT EXISTS guilds (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        guild_id BIGINT UNIQUE NOT NULL,
        guild_name VARCHAR(255)
    );
    """)
    logger.info(f"Verified table: guilds")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        discord_id BIGINT UNIQUE NOT NULL,
        user_name VARCHAR(255),

        total_gaming_hours INT DEFAULT 0,
        total_streamed_hours INT DEFAULT 0

    );
    """)
    logger.info(f"Verified table: users")
    # steam_id VARCHAR(255),
    # steam_hours INT DEFAULT 0,
    # steam_games_count INT DEFAULT 0,
    # total_gaming_hours INT DEFAULT 0,
    # auto_sync_steam BOOLEAN DEFAULT FALSE

    cur.execute("""CREATE TABLE IF NOT EXISTS guilds_users (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        guild_id INT REFERENCES guilds(id),
        user_id INT REFERENCES users(id),

        guild_level INT DEFAULT 1,
        xp INT DEFAULT 0
    );
    """)
    logger.info(f"Verified table: guilds_users")

    cur.execute("""CREATE TABLE IF NOT EXISTS games (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        game_name VARCHAR(255),

        on_steam BOOLEAN,
        img TEXT,
        steam_app_id INT UNIQUE,
        steam_price INT
    );
    """)
    logger.info(f"Verified table: games")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_games (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id INT REFERENCES users(id),
        game_id INT REFERENCES games(id),

        seen_playing_in_server BOOLEAN DEFAULT FALSE,
        server_hours INT DEFAULT 0,
        unsyced_hours INT DEFAULT 0,
        last_time_played INT,
        steam_playtime INT
    );
    """)
    logger.info(f"Verified table: user_games")

    cur.execute("""CREATE TABLE IF NOT EXISTS general_steam_data (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id INT REFERENCES users(id),

        steam_id VARCHAR(255),
        account_name VARCHAR(255),
        account_age INT,
        steam_games_count INT,
        account_cost INT,
        total_steam_time INT,
        auto_sync_steam BOOLEAN,
        last_sync INT
    );
    """)
    logger.info(f"Verified table: general_steam_data")


    # cur.execute("""CREATE TABLE IF NOT EXISTS daily_game_stats (
    #     id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    #     user_id INT,
    #     game_id INT,
    #     hours_played INT
    # );
    # """)

    # cur.execute("""CREATE TABLE IF NOT EXISTS daily_stats_general (
    #     id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    #     total_hours_gaming INT,
    #     total_hours_streaming INT,
    #     messages_sent INT
    # );
    # """)

    cur.execute("""CREATE TABLE IF NOT EXISTS activity_tracker (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id INT REFERENCES users(id) UNIQUE,
        game_id INT REFERENCES games(id),

        start_time TIMESTAMPTZ
    );
    """)
    logger.info(f"Verified table: activity_tracker")

    close_connection(conn,cur)
    print("Database has been successfully initialized")


def create_connection():
    conn = db.connect(host= os.getenv("DB_HOST"), dbname=os.getenv("DB_NAME"), user=os.getenv("USER"), password=os.getenv("PASSWORD"),port=os.getenv("PORT"))
    cur = conn.cursor()
    return conn,cur

def close_connection(conn,cur):
    conn.commit()
    cur.close()
    conn.close()

# cur.execute("""ALTER TABLE person
# ADD COLUMN price VARCHAR(255)
# """)

def game_name_in_database(game_name, cur : db.extensions.cursor):
    gid = get_game_id_from_name(game_name, cur)
    if gid is None:
        return False
    return True


#This function will find the most recent played game from the game tracker and then return the date before removing the game from the tracker
def end_game_tracker(member_id, game_name, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)
    gid = get_game_id_from_name(game_name, cur)

    cur.execute(
        """SELECT start_time FROM activity_tracker
            WHERE user_id = %s
            AND game_id = %s
        """,(uid, gid))
    
    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find data for {game_name} because it does not exist")
        return None

    cur.execute(
        """DELETE FROM activity_tracker
            WHERE user_id = %s
            AND game_id = %s 
        """,(uid, gid))
    
    return result[0]

def check_for_active_game(uid, gid, cur: db.extensions.cursor):
    cur.execute(
        """SELECT game_id, game_id FROM activity_tracker
            WHERE user_id = %s
        """,(uid,))

    result = cur.fetchone()

    # There are no conflicts tracking a new game
    if result is None:
        return 0
    # That game is already being tracked
    elif result[1] == gid:
        return 1
    # There is a differnt game session that ended but wasn't recorded
    else:
        return 2
    

def start_game_tracker(member_id, game_name, time : dt.datetime, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)
    gid = get_game_id_from_name(game_name, cur)

    error_code = check_for_active_game(uid, gid, cur)

    if error_code == 2:
        
    cur.execute(
        """INSERT INTO activity_tracker (user_id, game_id, start_time)
            VALUES (%s, %s, %s);
        """,(uid, gid, time))


def verify_member_in_database(total_guilds, bot_profile_id, cur : db.extensions.cursor):
    for guild in total_guilds:
        try:
            cur.execute(
            """SELECT guilds.id 
                FROM guilds
                WHERE guilds.guild_id = %s;
            """,(guild.id,))

            result = cur.fetchone()
            if result == None:
                logger.info(f"Attempting to add guild with id {guild.id} ({guild.name})")
                cur.execute(
                    """INSERT INTO guilds (guild_id, guild_name)
                        VALUES (%s,%s);
                    """,(guild.id, guild.name))
                logger.info(f"Guild with id {guild.id} ({guild.name}) was added to the database")
            else:
                guild_name = get_guild_name(guild.id, cur)
                logger.info(f"Verified guild : {guild_name}")

        except Exception as e:
            print(f"something went wrong with: {e}")
            logger.info(f"Could not add guild with id {guild.id} ({guild.name})")

        for member in guild.members:
                if member.id != bot_profile_id:
                    cur.execute(
                        """SELECT users.discord_id
                            FROM users
                            WHERE users.discord_id = %s;
                        """,(member.id,))
                    result = cur.fetchone()
                    if result == None:
                        logger.info(f"Attempting to add member with id {member.id} ({member.name})")
                        cur.execute(
                            """INSERT INTO users (discord_id, user_name)
                                VALUES (%s,%s);
                            """,(member.id, member.name))
                        logger.info(f"Member with id {member.id} ({member.name}) was added to the database")
                    else:
                        user_name = get_discord_username(result[0], cur)
                        logger.info(f"Verified memeber with username : {user_name}")


def game_in_db(game_id,cur : db.extensions.cursor):
    cur.execute(
        """SELECT FROM games 
            WHERE games.steam_app_id = %s
        """,(game_id,))

    result = cur.fetchone()
    if result is None:
        return 0
    else:
        return 1

def check_for_existing_steam_link(member_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)

    cur.execute(
        """SELECT account_name FROM general_steam_data
            WHERE user_id = %s;
        """,(uid,))

    result = cur.fetchone()

    if result is not None:
        return 3, result[0]

    return 0, None


def get_game_id_from_name(game_name, cur : db.extensions.cursor):
    cur.execute(
        """SELECT id FROM games
            WHERE game_name = %s
        """,(game_name,))

    result = cur.fetchone()

    if result is None:
        logger.warning(f"Could not find the game : {game_name} in the database")
        return result

    return result[0]
        

def get_guild_name(guild_id, cur : db.extensions.cursor):
    cur.execute(
        """SELECT guild_name FROM guilds
            WHERE guild_id = %s
        """,(guild_id,))

    result = cur.fetchone()
    if result is not None :
        return result[0]
    else:
        return "Guild not found"
    
    
def get_discord_username(discord_id, cur : db.extensions.cursor):
    cur.execute(
        """SELECT user_name FROM users
            WHERE discord_id = %s 
        """,(discord_id,))

    result = cur.fetchone()
    if result is not None:
        return result[0]
    else:
        return "User not found"
    
def get_user_id(member_id, cur: db.extensions.cursor):
    cur.execute(
        """SELECT id FROM users
            WHERE users.discord_id = %s
        """,(member_id,))
    result = cur.fetchone()
    return result[0]


def get_steam_name(member_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id,cur)

    cur.execute(
        """SELECT account_name FROM general_steam_data
            WHERE user_id = %s;
        """,(uid,))

    result = cur.fetchone()
    return result[0]

def get_game_id(app_id, cur : db.extensions.cursor):
    cur.execute(
        """SELECT id FROM games
            WHERE steam_app_id = %s
        """,(app_id,))
    result = cur.fetchone()
    return result[0]


def get_game_img(app_id, cur : db.extensions.cursor):
    cur.execute(
            """SELECT img FROM games
                WHERE steam_app_id = %s
            """,(app_id,))
    result = cur.fetchone()
    return result[0]


def get_total_steam_time(member_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)

    cur.execute(
        """SELECT steam_playtime FROM user_games
            WHERE user_id = %s;
        """,(uid,))

    result = cur.fetchall()

    total = 0 
    for time_list in result:
        time = time_list[0]
        total += time

    return total


def get_total_library_cost(member_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)
    cur.execute(
        """SELECT games.steam_price
            FROM user_games
            JOIN games
                ON user_games.game_id = games.id 
            WHERE user_id = %s;
        """,(uid,))
    
    result = cur.fetchall()
    total = 0
    for price_list in result:
        price = price_list[0]
        if price != None:
            total += price
    return total


def add_game_to_database(name, IGDBClient : IGDBClient , cur : db.extensions.cursor):
    logger.info(f"Attempting to add {name} to the database...")
    on_steam, steam_game_data = check_steam_game_availability(name)

    if on_steam == False:
        logger.info(f"{name} was not found on steam. Getting image from igdb")
        img = IGDBClient.get_alt_url(name)
        cur.execute(
            """INSERT INTO games (game_name, on_steam, img)
                VALUES(%s,%s,%s)
            """,(name, on_steam, img))
    else:
        logger.info(f"{name} is on Steam. Updating from Steam client")
        steam_app_id = steam_game_data['id']
        img, price = look_up_steam_image_and_price(steam_app_id)
        cur.execute(
            """INSERT INTO games (game_name, on_steam, img, steam_app_id, steam_price)
                VALUES(%s,%s,%s,%s,%s)
            """,(name, on_steam, img, steam_app_id, price))


def add_game_to_database_from_steam(game_data, cur : db.extensions.cursor):
    name = game_data['name']
    on_steam = True
    gid = game_data['appid']

    img, price = look_up_steam_image_and_price(gid)
    cur.execute(
        """INSERT INTO games (game_name, on_steam, img, steam_app_id, steam_price)
            VALUES(%s,%s,%s,%s,%s)
        """,(name, on_steam, img, gid, price))

    
def link_steam_library(library_data : dict, steam_profile_data : dict, member_id : int, cur : db.extensions.cursor):
    #conn,cur = create_connection()

    uid = get_user_id(member_id, cur)

    # need to make sure to do a db lookup to see if the game already exists
    # might need to use locks to ensure one sync at a time
    logger.info(library_data)

    for game in library_data['games']:
        # We might need to check to see if the game is marked as not on steam so we can update it 

        if game_in_db(game['appid'], cur):
            app_id = game['appid']

            gid = get_game_id(app_id, cur)
            playtime = game['playtime_forever']
            playtime_seconds = playtime * 60
            logger.info(f"Processing {game['name']} from existing game data")

            # we will have to check if the game exists and if it does we have to update the last time played
            cur.execute(
                    """INSERT INTO user_games (user_id, game_id, steam_playtime)
                        VALUES(%s,%s,%s)
                    """,(uid, gid, playtime_seconds))
        else:
            app_id = game['appid']
            # name = game['name']
            # playtime = game['playtime_forever']
            # img = look_up_steam_image(app_id)
            logger.info(f"Processing {game['name']} from new game data")
            add_game_to_database_from_steam(game,cur)
            #print(f"{app_id} {name} {playtime} {img}")

            gid = get_game_id(app_id, cur)
            playtime = game['playtime_forever']
            playtime_seconds = playtime * 60

            cur.execute(
                """INSERT INTO user_games (user_id, game_id, steam_playtime)
                    VALUES(%s,%s,%s)
                """,(uid, gid, playtime_seconds))

    # Update general steam data profile 
    # Still need to add account age from the time created in the steam_profile
    # When adding the price make sure to only get the values where the price isn't null
    steam_name = steam_profile_data['player']['personaname']
    steam_id = steam_profile_data['player']['steamid']
    game_count = library_data['game_count']
    creation_time = steam_profile_data['player']['timecreated']
    total_library_cost = get_total_library_cost(member_id, cur)
    total_steam_time = get_total_steam_time(member_id, cur)
    cur.execute(
        """INSERT INTO general_steam_data (user_id, steam_id, account_name, account_age, steam_games_count, account_cost, total_steam_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,(uid, steam_id, steam_name, creation_time, game_count, total_library_cost, total_steam_time))

    # INSERT INTO games (steam_app_id, game_name, image_url)
    # VALUES (%s, %s, %s)
    # ON CONFLICT (steam_app_id) DO NOTHING;
    logger.info(f"Library fully processed for {steam_name}")


def remove_user_steam_data(dicord_id, cur: db.extensions.cursor):
    uid = get_user_id(dicord_id, cur)
    cur.execute(
        """DELETE FROM user_games
            WHERE user_id = %s 
            AND seen_playing_in_server = false;
        """,(uid,))
    logger.info(f"Deleting data in user_games with id : {uid}")

    cur.execute(
        """DELETE FROM general_steam_data
            WHERE user_id = %s
        """,(uid,))
    logger.info(f"Deleting data in general_steam_data with id : {uid}")



def add_cost(price):
    conn,cur = create_connection()

    cur.execute(
        """UPDATE person
        SET
            person.price = %s
        WHERE person.credit_score > 799;
        """,(price,))

    close_connection(conn,cur)

def print_db():
    conn,cur = create_connection()

    results = ""
    cur.execute("SELECT * FROM person")
    for entry in cur.fetchall():
        results += str(entry) + "\n"
        print(entry)

    close_connection(conn,cur)

    return results

def resetdb():
    conn,cur = create_connection()

    cur.execute("""
    DROP TABLE IF EXISTS activity_tracker;
    DROP TABLE IF EXISTS user_recently_played;
    DROP TABLE IF EXISTS general_steam_data;
    DROP TABLE IF EXISTS user_games;
    DROP TABLE IF EXISTS guilds_users;
    DROP TABLE IF EXISTS guilds;
    DROP TABLE IF EXISTS games;
    DROP TABLE IF EXISTS users;
    """)

    close_connection(conn,cur)
    print("database has been deleted")

def cleardb():
    conn,cur = create_connection()

    cur.execute("""
    DELETE FROM activity_tracker;
    DELETE FROM user_recently_played;
    DELETE FROM general_steam_data;
    DELETE FROM user_games;
    DELETE FROM guilds_users;
    DELETE FROM guilds;
    DELETE FROM games;
    DELETE FROM users;
    """)

    close_connection(conn,cur)
    print("entries in db have been cleared")

if __name__ == "__main__":
    #resetdb()
    # conn,cur = create_connection()
    # print(get_total_library_cost(938183066948612096,cur))
    # close_connection(conn, cur)
    pass