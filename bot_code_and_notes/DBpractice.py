import psycopg2 as db
import os 
from dotenv import load_dotenv
load_dotenv()
import logging
from SteamPractice import *
import datetime as dt
from datetime import timezone
from igdbPractice import *
from enum import Enum

class activity_errors(Enum):
    NO_CONFLICT = 0
    SESSION_ALREADY_IN_PROGRESS = 1
    DIFFERENT_GAME_IN_PROGRESS = 2

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

def create_connection():
    conn = db.connect(host= os.getenv("DB_HOST"), dbname=os.getenv("DB_NAME"), user=os.getenv("USER"), password=os.getenv("PASSWORD"),port=os.getenv("PORT"))
    cur = conn.cursor()
    return conn,cur


def close_connection(conn,cur):
    conn.commit()
    cur.close()
    conn.close()


def initialize_db():
    conn,cur = create_connection()

    cur.execute("""CREATE TABLE IF NOT EXISTS guilds (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        guild_id BIGINT UNIQUE NOT NULL,
        guild_name VARCHAR(255),
        weekly_stats_channel_id BIGINT,
        news_channel_id BIGINT
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
        game_name VARCHAR(255) UNIQUE,

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
        unsynced_hours INT DEFAULT 0,
        last_time_played TIMESTAMPTZ,
        steam_playtime INT,

        UNIQUE(user_id, game_id)
    );
    """)
    logger.info(f"Verified table: user_games")

    cur.execute("""CREATE TABLE IF NOT EXISTS general_steam_data (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id INT REFERENCES users(id) UNIQUE,

        steam_id VARCHAR(255),
        account_name VARCHAR(255),
        creation_time TIMESTAMPTZ,
        steam_games_count INT,
        account_cost INT,
        total_steam_time INT,
        auto_sync_steam BOOLEAN,
        last_sync INT
    );
    """)
    logger.info(f"Verified table: general_steam_data")

    cur.execute("""CREATE TABLE IF NOT EXISTS activity_tracker (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id INT REFERENCES users(id),
        game_id INT REFERENCES games(id),
        activity_type VARCHAR(255),
        start_time TIMESTAMPTZ,
        UNIQUE(user_id, activity_type)
    );
    """)
    logger.info(f"Verified table: activity_tracker")

    cur.execute("""CREATE TABLE IF NOT EXISTS todays_news (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        article_title TEXT,
        gid INT UNIQUE
    );
    """)    
    logger.info(f"Verified table: todays_news")

    # We also want to manually clear the activity tracking table(s) on start up if needed

    close_connection(conn,cur)
    print("Database has been successfully initialized")


# cur.execute("""ALTER TABLE person
# ADD COLUMN price VARCHAR(255)
# """)
def user_owns_game(member_id, game_name, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)
    gid = get_game_id_from_name(game_name, cur)
    if uid == None or gid == None:
        logger.error(f"Could not find either uid for {member_id} or gid for {game_name}")
        return
    
    cur.execute(
        """SELECT * FROM user_games
            WHERE user_id = %s
            AND game_id = %s
        """,(uid,gid)
        )

    result = cur.fetchone()

    if result is None:
        logger.warning(f"Game : {game_name} was not found in user : {member_id} profile")
        return False

    return True


def get_game_id_from_name(game_name : str, cur : db.extensions.cursor):
    cur.execute(
        """SELECT id FROM games
            WHERE game_name = %s
        """,(game_name,)
    )

    result = cur.fetchone()

    if result is None:
        logger.warning(f"Could not find the game : {game_name} in the database")
        return result

    return result[0]
   

def game_name_in_database(game_name, cur : db.extensions.cursor):
    gid = get_game_id_from_name(game_name, cur)
    if gid is None:
        return False
    return True


def get_user_id(member_id : int, cur: db.extensions.cursor):
    cur.execute(
        """SELECT id FROM users
            WHERE users.discord_id = %s
        """,(member_id,))
    result = cur.fetchone()
    return result[0]


def get_app_id(gid ,cur : db.extensions.cursor):
    cur.execute(
        """SELECT on_steam, steam_app_id FROM games
            WHERE id = %s
        """,(gid,)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find a steam_app_id for gid : {gid}")
        return result
    if result[0] == False:
        logger.warning(f"Could not find a steam_app_id for gid : {gid} because it is not on steam")
        return None

    return result[1]


def add_to_todays_news(news_title, gid, cur : db.extensions.cursor):
    cur.execute(
        """INSERT INTO todays_news (article_title, gid)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """,(news_title, gid)
    )


def process_member_games_into_news(member_id_list, cur : db.extensions.cursor):
    logger.info(f"Started processing game news for members : {member_id_list}")
    # for each person in the list get all the games that they played that month
    # add those games to a list if they are not already added
    # return all those game ids
    uid_list = []
    for member_id in member_id_list:
        user_id = get_user_id(member_id, cur)
        uid_list.append(user_id)

    user_lookup = dict(zip(uid_list, member_id_list))
    news = {}

    cur.execute(
        """SELECT user_id, game_id, last_time_played FROM user_games
            WHERE last_time_played IS NOT NULL
            ORDER BY last_time_played
        """
    )

    results = cur.fetchall()
    if not results:
        logger.info("No recent games found")
        return {}

    date_cutoff = dt.datetime.now(timezone.utc) - dt.timedelta(weeks = 4)
    #print(date_cutoff)
    for result in results:
        uid = result[0]
        if uid not in uid_list:
            continue
        discord_id = user_lookup[uid]
        gid = result[1]
        plytime = result[2]
        if plytime >= date_cutoff:
            app_id = get_app_id(gid, cur)
            if app_id is None:
                continue
            if app_id not in news:
                data = {
                    'relavent_members' : [],
                    'news_articles' : []
                }
                news[app_id] = data
                news[app_id]['relavent_members'].append(discord_id)
            else:
                news[app_id]['relavent_members'].append(discord_id)

    #print(news)
    return get_game_news_from_steam(news)

# conn,cur = create_connection()
# process_member_games_into_news([385277889404207105,938183066948612096],cur)
# close_connection(conn,cur)


def get_server_time(uid, gid, cur : db.extensions.cursor):
    cur.execute(
        """SELECT server_hours FROM user_games
            WHERE user_id = %s
            AND game_id = %s
        """,(uid, gid)
    )

    result = cur.fetchone()

    if result is None:
        logger.error(f"Could not find a match for user_id : {uid} and game_id : {gid}")
        return

    return result[0]

# Without a total time, this funtion updates the game and marks it as beeing seen and records the
# last played time when an activity starts. With a total time it
# records the completed activity after it ends.
def update_user_game_time(total_time, uid, gid, cur : db.extensions.cursor):
    if total_time is None:
        total_time = get_server_time(uid, gid, cur)
        if total_time is None:
            logger.error(f"Aborting updating user game time because could not find total_time for gid : {gid} and user : {uid}")
            return

    current_time = dt.datetime.now(tz = timezone.utc)

    cur.execute(
        """UPDATE user_games
            SET
                seen_playing_in_server = %s,
                server_hours = %s,
                last_time_played = %s
            WHERE user_id = %s
            AND game_id = %s
        """,(True, total_time, current_time, uid, gid)
    )
    

def remove_tracked_game(uid, gid, cur : db.extensions.cursor):
    cur.execute(
        """DELETE FROM activity_tracker
            WHERE user_id = %s
            AND game_id = %s 
        """,(uid, gid)
    )


def manually_end_game_session(uid, cur : db.extensions.cursor):
    logger.info(f"Attempting to end manual tracking on for user : {uid}...")
    a_type = "PLAYING"
    cur.execute(
        """SELECT game_id, start_time FROM activity_tracker
            WHERE user_id = %s
            AND activity_type = %s
        """,(uid, a_type)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not manually end session for user {uid} because it was not found")
        return

    gid = result[0]
    start_time = result[1]
    curr_server_game_time = get_server_time(uid, gid, cur)
    if curr_server_game_time is None:
        logger.error(f"Aborting manually ending game session for user : {uid} and game : {gid} because could not find the current server game time")
        return
    
    session_time = (dt.datetime.now(tz = timezone.utc) - start_time).total_seconds()

    total_server_time = session_time + curr_server_game_time

    update_user_game_time(total_server_time, uid, gid, cur)
    remove_tracked_game(uid, gid, cur)

    logger.info(f"Successfully ended manual tracking on gid : {gid} for user : {uid}...")

def end_game_tracker(member_id, game_name, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)
    gid = get_game_id_from_name(game_name, cur)
    if uid == None or gid == None:
        logger.error(f"Ending tracking failed for game : {game_name} and user {member_id} because either uid or gid were not found")
        return

    cur.execute(
        """SELECT start_time FROM activity_tracker
            WHERE user_id = %s
            AND game_id = %s
        """,(uid, gid)
    )
    
    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find data for {game_name} because it does not exist")
        return None

    curr_server_game_time = get_server_time(uid, gid, cur)
    if curr_server_game_time == None:
        logger.error(f"Could not find a valid time server time for game : {game_name} and user : {member_id}. Aborting operation")
        return

    today = dt.datetime.now(tz = timezone.utc)
    time_played = (today - result[0]).total_seconds()

    total_time = curr_server_game_time + time_played

    update_user_game_time(total_time, uid, gid, cur)
    remove_tracked_game(uid, gid, cur)
    logger.info(f"Successfully ended tracking on {game_name} for user : {member_id} at time : {today}...")
    # also will want to add this data to the server log


def end_tracker(member_id, game_name, activity_type : str, cur : db.extensions.cursor):

    if activity_type == "PLAYING":
        logger.info(f"Attempting to end tracking on {game_name} for user : {member_id}...")
        end_game_tracker(member_id, game_name, cur)
          

def check_for_active_game(uid, gid, cur: db.extensions.cursor):
    a_type = "PLAYING"
    cur.execute(
        """SELECT game_id FROM activity_tracker
            WHERE user_id = %s
            AND activity_type = %s
        """,(uid,a_type)
    )

    result = cur.fetchone()

    # There are no conflicts tracking a new game
    if result is None:
        return activity_errors.NO_CONFLICT
    # That game is already being tracked
    elif result[0] == gid:
        return activity_errors.SESSION_ALREADY_IN_PROGRESS
    # There is a differnt game session that ended but wasn't recorded
    else:
        return activity_errors.DIFFERENT_GAME_IN_PROGRESS
    

def start_activity_tracker(member_id : int, game_name : str, activity_type : str, cur : db.extensions.cursor):
    logger.info(f"Attempting to start tracking {game_name} for user {member_id}...")

    curr_time = dt.datetime.now(timezone.utc)
    uid = get_user_id(member_id, cur)
    gid = get_game_id_from_name(game_name, cur)
    if uid == None or gid == None:
        logger.error(f"Game tracking start up for game : {game_name} and user {member_id} failed because either uid or gid were not found")
        return

    status_code = check_for_active_game(uid, gid, cur)

    if status_code == activity_errors.SESSION_ALREADY_IN_PROGRESS:
        logger.info(f"Tracking was not updated because {game_name} was already being tracked")
        return
    
    if status_code == activity_errors.DIFFERENT_GAME_IN_PROGRESS:
        logger.info(f"Different game was being tracked. Ending previous tracking for {member_id}")
        manually_end_game_session(uid, cur)

    cur.execute(
        """INSERT INTO activity_tracker (user_id, game_id, activity_type, start_time)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """,(uid, gid, activity_type, curr_time))
        
    update_user_game_time(None, uid, gid, cur)
    logger.info(f"Finalized tracking start up for game : {game_name} with user : {member_id}")


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

def game_in_db_from_gid(gid, cur : db.extensions.cursor):
    if gid is None:
        return 0
    
    cur.execute(
        """SELECT FROM games 
            WHERE games.id = %s
        """,(gid,)
    )

    result = cur.fetchone()
    if result is None:
        return 0
    else:
        return 1

def game_in_db(game_id,cur : db.extensions.cursor):
    if game_id is None:
        return 0
    
    cur.execute(
        """SELECT FROM games 
            WHERE games.steam_app_id = %s
        """,(game_id,)
    )

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
        """,(uid,)
    )

    result = cur.fetchone()

    if result is not None:
        return 3, result[0]

    return 0, None

     

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


def get_game_img(gid, cur : db.extensions.cursor):
    cur.execute(
            """SELECT img FROM games
                WHERE id = %s
            """,(gid,))
    result = cur.fetchone()
    return result[0]


def get_total_steam_time(member_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)

    cur.execute(
        """SELECT steam_playtime FROM user_games
            WHERE user_id = %s;
        """,(uid,))

    result = cur.fetchall()

    if not result:
        logger.info("No recent time found")
        return 0
    total = 0 
    for time_list in result:
        time = time_list[0]
        if time != None:
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

def get_on_steam_from_db(gid, cur : db.extensions.cursor):
    cur.execute(
        """SELECT on_steam FROM games
            WHERE id = %s
        """,(gid,)
    )

    result = cur.fetchone()
    return result[0]


def add_game_to_user_profile(game_name, member_id, cur : db.extensions.cursor):
    logger.info(f"Adding {game_name} to user : {member_id} profile")
    uid = get_user_id(member_id, cur)
    gid = get_game_id_from_name(game_name, cur)
    if gid == None or uid == None:
        logger.error(f"Aborting adding {game_name} to user : {member_id} profile because either uid or gid were not found")
        return
    
    cur.execute(
        """INSERT INTO user_games (user_id, game_id, seen_playing_in_server)
            VALUES(%s,%s,%s)
            ON CONFLICT (user_id, game_id)
            DO UPDATE
                SET seen_playing_in_server = EXCLUDED.seen_playing_in_server
        """,(uid, gid, True)
    )

    
def add_game_to_database(name, IGDBClient : IGDBClient , cur : db.extensions.cursor):
    logger.info(f"Attempting to add {name} to the database...")
    on_steam, steam_game_data = check_steam_game_availability(name)

    if on_steam == False:
        logger.info(f"{name} was not found on steam. Getting image from igdb")
        img = IGDBClient.get_alt_url(name)
        gid = get_game_id_from_name(name,cur)
        if game_in_db_from_gid(gid,cur):
            if get_on_steam_from_db(gid,cur):
                logger.warning(f"Tried to update game: {name} with non-steam data. Keeping existing data")
                return
            prev_img = get_game_img(gid,cur)
            if prev_img is not None and img is None:
                logger.warning(f"Tried to update game: {name} with an image that doesn't exist. Keeping existing image")
                return
        cur.execute(
            """INSERT INTO games (game_name, on_steam, img)
                VALUES(%s,%s,%s)
                ON CONFLICT (game_name)
                DO UPDATE 
                    SET
                        on_steam = EXCLUDED.on_steam,
                        img = EXCLUDED.img
            """,(name, on_steam, img))
    else:
        logger.info(f"{name} is on Steam. Updating from Steam client")
        steam_app_id = steam_game_data['id'][0]
        img, price = look_up_steam_image_and_price(steam_app_id)
        gid = get_game_id_from_name(name, cur)
        if game_in_db_from_gid(gid,cur):
            prev_img = get_game_img(gid,cur)
            if prev_img is not None and img is None:
                logger.warning(f"Tried to update game: {name} with an image that doesn't exist. Keeping existing image")
                return
        cur.execute(
            """INSERT INTO games (game_name, on_steam, img, steam_app_id, steam_price)
                VALUES(%s,%s,%s,%s,%s)
                ON CONFLICT (game_name)
                DO UPDATE
                    SET 
                        on_steam = EXCLUDED.on_steam,
                        img = EXCLUDED.img,
                        steam_app_id = EXCLUDED.steam_app_id,
                        steam_price = EXCLUDED.steam_price    
            """,(name, on_steam, img, steam_app_id, price))


def add_game_to_database_from_steam(game_data, cur : db.extensions.cursor):
    name = game_data['name']
    on_steam = True
    appid = game_data['appid']

    img, price = look_up_steam_image_and_price(appid)
    # If we know the game is on steam but the look up fuction failed to get an image then most likely there was a network issue
    if game_in_db(appid,cur):
        gid = get_game_id(appid, cur)
        prev_img = get_game_img(gid, cur)
        if prev_img is not None and img is None:
            logger.warning(f"Tried to update game: {name} with an image that doesn't exist. Keeping existing image")
            return
    cur.execute(
        """INSERT INTO games (game_name, on_steam, img, steam_app_id, steam_price)
            VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT (steam_app_id)
                DO UPDATE 
                    SET
                        game_name = EXCLUDED.game_name,
                        on_steam = EXCLUDED.on_steam,
                        img = EXCLUDED.img,
                        steam_price = EXCLUDED.steam_price
        """,(name, on_steam, img, appid, price)
    )


# Game can be updated if it is in the database and part of the user's profile
def check_if_game_is_updatable(game, uid, cur : db.extensions.cursor):
    if not game_in_db(game['appid'], cur):
        logger.error(f"Game : {game} could not be found in the data base. Could not add to user: {uid} profile")
        return False

    gid = get_game_id_from_name(game['name'],cur)

    cur.execute(
        """SELECT id, last_time_played FROM user_games
            WHERE user_id = %s
            AND game_id = %s
        """,(uid, gid)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find {game['name']} data in user : {uid} profile")
        return False

    time_limit = dt.datetime.now(timezone.utc) - dt.timedelta(days=1)
    if result[1] != None and result[1] >= time_limit:
        return False

    return True

# A majority of profiles do not have the exact time recent games were played
# To mitigate this issue we assume that each game in the user's recenlty played list was played on a different day
# Over time these values will become more accurate through regular activity monitoring 
def update_user_recently_played(uid, steam_id, cur : db.extensions.cursor):
    # only update if value is older than the last two weeks or none
    games = get_recently_played_games(steam_id)
    if games is None:
        return

    today = dt.datetime.now(timezone.utc)
    date = today
    recency_scaling = dt.timedelta(days = 1)
    for game in games['games']:
        if check_if_game_is_updatable(game, uid, cur):
    
            gid = get_game_id_from_name(game['name'], cur)

            cur.execute(
                """UPDATE user_games
                    SET
                        last_time_played = %s
                    WHERE user_id = %s
                    AND game_id = %s
                """,(date, uid, gid)
            )
            new_date = date - recency_scaling
            # Recently played gives the games played within a 14 day period
            # If the user has played over 14 different games we want to make sure we don't scale past our 14 day period
            if (today - new_date).days < 14:
                date = new_date

 
def link_steam_library(library_data : dict, steam_profile_data : dict, member_id : int, cur : db.extensions.cursor, conn : db.extensions.connection, is_sync = False):
    #conn,cur = create_connection()

    uid = get_user_id(member_id, cur)

    # need to make sure to do a db lookup to see if the game already exists
    # might need to use locks to ensure one sync at a time
    logger.info(library_data)

    
    throttle_counter = 0
    for i, game in enumerate(library_data['games']):
        # We might need to check to see if the game is marked as not on steam so we can update it 
        app_id = game['appid']

        if game_in_db(app_id, cur):
            logger.info(f"Processing {game['name']} from existing game data")
        else:
            logger.info(f"Processing {game['name']} from new game data")
            add_game_to_database_from_steam(game,cur)
            # We add a cooldown to API look ups in order to not stress the network on the deployment 
            throttle_counter += 1
            if throttle_counter >= 30:
                throttle_counter = 0
                conn.commit()
                logger.info(f"Throttle limit reached. Commiting data for batch {i}/{len(library_data['games'])} before resting")
                time.sleep(25)

        gid = get_game_id(app_id, cur)
        playtime = game['playtime_forever']
        playtime_seconds = playtime * 60
        cur.execute(
            """INSERT INTO user_games (user_id, game_id, steam_playtime)
                VALUES(%s,%s,%s)
                ON CONFLICT (user_id, game_id)
                DO UPDATE
                    SET steam_playtime = EXCLUDED.steam_playtime
            """,(uid, gid, playtime_seconds))
    
    # Update general steam data profile 
    # Still need to add account age from the time created in the steam_profile
    # When adding the price make sure to only get the values where the price isn't null
    steam_name = steam_profile_data['player']['personaname']
    steam_id = steam_profile_data['player']['steamid']
    game_count = library_data['game_count']
    creation_time_stamp = steam_profile_data['player']['timecreated']
    creation_time = dt.datetime.fromtimestamp(creation_time_stamp, timezone.utc)
    total_library_cost = get_total_library_cost(member_id, cur)
    total_steam_time = get_total_steam_time(member_id, cur)
    if total_steam_time is None:
        total_steam_time = 0
    cur.execute(
        """INSERT INTO general_steam_data (user_id, steam_id, account_name, creation_time, steam_games_count, account_cost, total_steam_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE
                SET 
                    steam_id = EXCLUDED.steam_id,
                    account_name = EXCLUDED.account_name,
                    creation_time = EXCLUDED.creation_time,
                    steam_games_count = EXCLUDED.steam_games_count,
                    account_cost = EXCLUDED.account_cost,
                    total_steam_time = EXCLUDED.total_steam_time
        """,(uid, steam_id, steam_name, creation_time, game_count, total_library_cost, total_steam_time))

    # I think it would be a good idea to pass a status into this function called link/sync
    # If we are linking (getting steam info for the first time) we use the update recently played otherwise we don't need to use that function
    if not is_sync:
        update_user_recently_played(uid, steam_id, cur)

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
    DROP TABLE IF EXISTS todays_news;
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
    DELETE FROM todays_news;
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
    # resetdb()
    # conn,cur = create_connection()
    # print(get_total_library_cost(938183066948612096,cur))
    # close_connection(conn, cur)
    pass