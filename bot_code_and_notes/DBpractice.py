import psycopg2 as db
import os 
from dotenv import load_dotenv
load_dotenv()
import logging

from SteamPractice import *

# import datetime as dt
# from datetime import timezone
from igdbPractice import *
from enum import Enum
from dateutil.relativedelta import relativedelta
import discord
import asyncio

class activity_errors(Enum):
    NO_CONFLICT = 0
    SESSION_ALREADY_IN_PROGRESS = 1
    DIFFERENT_GAME_IN_PROGRESS = 2
    STREAM_IN_PROGRESS = 3

logger = logging.getLogger(__name__)

def create_connection():
    conn : db.extensions.connection
    cur : db.extensions.cursor
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
        news_channel_id BIGINT,
        level_up_channel_id BIGINT,
        mvp_role_id BIGINT
    );
    """)
    logger.info(f"Verified table: guilds")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        discord_id BIGINT UNIQUE NOT NULL,
        user_name VARCHAR(255)

    );
    """)
    logger.info(f"Verified table: users")

    # add mvps, 2nd, and 3rd places
    cur.execute("""CREATE TABLE IF NOT EXISTS guilds_users (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        guild_id BIGINT REFERENCES guilds(guild_id),
        user_id INT REFERENCES users(id),

        total_messages_sent INT DEFAULT 0,
        messages_sent_this_week INT DEFAULT 0,
        total_stream_time INT DEFAULT 0,
        total_call_time INT DEFAULT 0,

        guild_level INT DEFAULT 1,
        xp INT DEFAULT 0,
        mvp_mult INT DEFAULT 100,
        MVPs INT DEFAULT 0,
        second_places INT DEFAULT 0,
        third_places INT DEFAULT 0
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
        profile_pic TEXT,
        last_sync TIMESTAMPTZ
    );
    """)
    logger.info(f"Verified table: general_steam_data")

    cur.execute("""CREATE TABLE IF NOT EXISTS activity_tracker (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id INT REFERENCES users(id),
        game_id INT REFERENCES games(id),
        activity_type VARCHAR(255),
        start_time TIMESTAMPTZ,
        guild_id BIGINT,
        UNIQUE(user_id, activity_type)
    );
    """)
    logger.info(f"Verified table: activity_tracker")

    cur.execute("""CREATE TABLE IF NOT EXISTS todays_news (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        article_title TEXT,
        gid BIGINT,
        guild_id BIGINT,
        date_added TIMESTAMPTZ,
        UNIQUE(gid, guild_id)
    );
    """)    
    logger.info(f"Verified table: todays_news")

    cur.execute("""CREATE TABLE IF NOT EXISTS server_log (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

        guild_id BIGINT,
        user_id INT REFERENCES users(id),
        game_id INT REFERENCES games(id),
        activity_type VARCHAR(255),
        activity_time INT,

        start_time TIMESTAMPTZ
    );
    """)
    logger.info(f"Verified table: server_log")

    cur.execute(
        """CREATE TABLE IF NOT EXISTS game_filter (
            id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

            game_name VARCHAR(255),
            game_id INT UNIQUE
            
        );
        """
    )
    logger.info(f"Verified table: game_filter")
    # We also want to manually clear the activity tracking table(s) on start up if needed

    close_connection(conn,cur)
    print("Database has been successfully initialized")


# cur.execute("""ALTER TABLE person
# ADD COLUMN price VARCHAR(255)
# """)
def get_user_xp(member_id, guild_id):
    conn,cur = create_connection()
    uid = get_user_id(member_id, cur)
    if uid is None:
        return
    
    cur.execute(
        """SELECT xp FROM guilds_users
            WHERE user_id = %s
            AND guild_id = %s
        """,(uid, guild_id)
    )

    result = cur.fetchone()
    close_connection(conn,cur)

    if result is None:
        logger.warning(f"No data found for uid : {uid} in guild : {guild_id}")
        print(f"No data found for uid : {uid} in guild : {guild_id}")

    return result[0]
        

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
    if result is None:
        logger.error(f"Could not find a uid matching member id : {member_id}")
        return None
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


def add_to_todays_news_database(news_title, gid, guild_id, cur : db.extensions.cursor):
    logger.info(f"Adding title : {news_title} with new_id : {gid} to todays_news db")
    print(f"Adding title : {news_title} with new_id : {gid} to todays_news db")
    today = dt.datetime.now(timezone.utc)
    cur.execute(
        """INSERT INTO todays_news (article_title, gid, guild_id, date_added)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """,(news_title, gid, guild_id, today)
    )

def get_filtered_news_gids(guild_id, cur : db.extensions.cursor):
    news_filter = []
    cur.execute(
        """SELECT gid FROM todays_news
            WHERE guild_id = %s
        """,(guild_id,)
    )

    results = cur.fetchall()
    if not results:
        return news_filter
    
    logger.info(f"current filter: {results}")
    print(f"current filter: {results}")

    for result in results:
        news_filter.append(result[0])

    return news_filter

def process_member_games_into_news(member_id_list, guild_id):
    today = dt.datetime.now(timezone.utc)
    conn,cur = create_connection()
    try:
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

        last_3_weeks = today - dt.timedelta(weeks=3)

        cur.execute(
            """SELECT user_id, game_id, last_time_played FROM user_games
                WHERE last_time_played IS NOT NULL
                AND last_time_played >= %s
                ORDER BY last_time_played
            """,(last_3_weeks,)
        )

        results = cur.fetchall()
        if not results:
            logger.info("No recent games found")
            return {}

        #print(date_cutoff)
        for result in results:
            uid = result[0]
            if uid not in uid_list:
                continue
            discord_id = user_lookup[uid]
            gid = result[1]
            #last_played = result[2]
            
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
        news_filter = get_filtered_news_gids(guild_id, cur)
        game_news, add_to_filter = get_game_news_from_steam(news, news_filter)
        for item in add_to_filter:
            add_to_todays_news_database(item[0], item[1], guild_id, cur)

        return game_news
    
    finally:
        close_connection(conn, cur)

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


def remove_tracked_activity(uid, activity_type, cur : db.extensions.cursor):
    cur.execute(
        """DELETE FROM activity_tracker
            WHERE user_id = %s
            AND activity_type = %s 
        """,(uid, activity_type)
    )


def remove_tracked_game(uid, gid, cur : db.extensions.cursor):
    cur.execute(
        """DELETE FROM activity_tracker
            WHERE user_id = %s
            AND game_id = %s 
        """,(uid, gid)
    )


def update_guilds_users_total_time(uid, guild_id, activity_type, session_time, cur : db.extensions.cursor):
    if activity_type == "IN CALL":
        cur.execute(
            """SELECT total_call_time FROM guilds_users
                WHERE user_id = %s
                AND guild_id = %s
            """,(uid, guild_id)
            )
        result = cur.fetchone()
        if result is None:
            logger.error(f"Could not find a user : {uid} tied to a guild : {guild_id} to update total {activity_type}")
            return
        
        old_total = result[0]
        new_total = old_total + session_time

        cur.execute(
            """UPDATE guilds_users
                SET
                    total_call_time = %s
                WHERE user_id = %s
                AND guild_id = %s
            """,(new_total, uid, guild_id)
        )

    if activity_type == "STREAMING":
        cur.execute(
            """SELECT total_stream_time FROM guilds_users
                WHERE user_id = %s
                AND guild_id = %s
            """,(uid, guild_id)
            )
        result = cur.fetchone()
        if result is None:
            logger.error(f"Could not find a user : {uid} tied to a guild : {guild_id} to update total {activity_type}")
            return
        
        old_total = result[0]
        new_total = old_total + session_time

        cur.execute(
            """UPDATE guilds_users
                SET
                    total_stream_time = %s
                WHERE user_id = %s
                AND guild_id = %s
            """,(new_total, uid, guild_id)
        )

def get_user_guilds(uid, cur : db.extensions.cursor):
    guild_list = []
    cur.execute(
        """SELECT guild_id FROM guilds_users
            WHERE user_id = %s
        """,(uid,)
    )

    results = cur.fetchall()
    if not results:
        return guild_list

    for result in results:
        guild_list.append(result[0])

    return guild_list


def get_member_id(uid , cur : db.extensions.cursor):
    cur.execute(
        """SELECT discord_id FROM users
            WHERE id = %s
        """,(uid,)
    )
    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find a discord id for uid : {uid}")
        return

    return result[0]


def restart_tracked_activities():
    logger.info("Began retarting tracked activities....")
    print("Began retarting tracked activities....")

    conn, cur = create_connection()
    try:
        cur.execute(
            """SELECT * FROM activity_tracker
            """
        )

        results = cur.fetchall()

        if not results:
            logger.info("No activities are currently being tracked. Ending replacement process")
            return
        
        time_buffer = dt.timedelta(minutes=3)

        for result in results:
            user_id = result[1]
            game_id = result[2]
            activity_type = result[3]
            guild_id = result[5]

            member_id = get_member_id(user_id, cur)

            if activity_type == "PLAYING":
                game_name = get_game_name_from_id(game_id, cur)
                end_game_tracker(member_id, game_name, activity_type, guild_id, cur)
                start_activity_tracker(member_id, game_name, activity_type, guild_id, cur, time_buffer)
            else:
                end_voice_tracker(member_id, activity_type, guild_id, cur)
                start_activity_tracker(member_id, None, activity_type, guild_id, cur, time_buffer)

    finally:
        close_connection(conn, cur)
    
def add_to_server_log_for_syncing_process(uid, gid, activity_type, activity_time, start_time, cur : db.extensions.cursor):
    #guild_list = get_user_guilds(uid, cur)
    #for guild_id in guild_list:
    cur.execute(
        """INSERT INTO server_log (guild_id, user_id, game_id, activity_type, activity_time, start_time)
            VALUES (%s,%s,%s,%s,%s,%s)
        """,(None, uid, gid, activity_type, activity_time, start_time)
    )


def add_to_server_log(uid, gid, activity_type, guild_id, activity_time, start_time, cur : db.extensions.cursor):
    cur.execute(
        """INSERT INTO server_log (guild_id, user_id, game_id, activity_type, activity_time, start_time)
            VALUES (%s,%s,%s,%s,%s,%s)
        """,(guild_id, uid, gid, activity_type, activity_time, start_time)
    )


def manually_end_game_session(uid, guild_id, activity_type, cur : db.extensions.cursor):
    logger.info(f"Attempting to end manual tracking on for user : {uid}...")
    cur.execute(
        """SELECT game_id, start_time FROM activity_tracker
            WHERE user_id = %s
            AND activity_type = %s
        """,(uid, activity_type)
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
    add_to_server_log(uid, gid, activity_type, guild_id, session_time, start_time, cur)
    member_id = get_member_id(uid, cur)
    calculate_user_xp(member_id, None, activity_type, session_time, cur)

    logger.info(f"Successfully recorded manual tracking on gid : {gid} for user : {uid} with a total of {session_time} seconds...")


def end_game_tracker(member_id, game_name, activity_type, guild_id, cur : db.extensions.cursor):

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
        logger.error(f"Could not find start time for {game_name} because it does not exist")
        return

    time_in_game = get_server_time(uid, gid, cur)
    if time_in_game == None:
        logger.error(f"Could not find a valid time server time for game : {game_name} and user : {member_id}. Aborting operation")
        return

    today = dt.datetime.now(tz = timezone.utc)
    start_time = result[0]
    time_played = (today - start_time).total_seconds()
    if time_played < 0:
        time_played = 0
    if time_played > 43200:
        time_played = 43200
    # Make sure to add a tracking limit here maybe 12 hours?
    total_time = time_in_game + time_played

    update_user_game_time(total_time, uid, gid, cur)
    remove_tracked_game(uid, gid, cur)
    if time_played > 0:
        add_to_server_log(uid, gid, activity_type, guild_id, time_played, start_time, cur)
        calculate_user_xp(member_id, None, activity_type, time_played, cur)
    logger.info(f"Successfully ended tracking on {game_name} for user : {member_id} at time : {today}...")
# also will want to add this data to the server log


def end_voice_tracker(member_id, activity_type, guild_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)
    cur.execute(
        """SELECT start_time FROM activity_tracker
            WHERE user_id = %s
            AND activity_type = %s
        """,(uid, activity_type)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find start time for activity_type : {activity_type} because it does not exist")
        return 

    today = dt.datetime.now(tz = timezone.utc)
    start_time = result[0]
    time_tracked = (today - start_time).total_seconds()
    if time_tracked < 0:
        time_tracked = 0
    # Total time for streaming and call will be in guilds_users

    if activity_type == "IN CALL":
        error_status = check_for_activity(uid, None, activity_type, cur)
        if error_status == activity_errors.STREAM_IN_PROGRESS:
            end_voice_tracker(member_id, "STREAMING", guild_id, cur)
        print(f"User id : {uid} was in call for {time_tracked} seconds")
    else:
        print(f"User id : {uid} was streaming for {time_tracked} seconds")

    update_guilds_users_total_time(uid, guild_id, activity_type, time_tracked, cur)
    add_to_server_log(uid, None, activity_type, guild_id, time_tracked, start_time, cur)
    calculate_user_xp(member_id, guild_id, activity_type, time_tracked, cur)
    remove_tracked_activity(uid, activity_type, cur)
    logger.info(f"Successfully recorded activity : {activity_type} with user : {member_id} with a total of {time_tracked} seconds")


def end_tracker(member_id, game_name, activity_type : str, guild_id, cur : db.extensions.cursor):

    if activity_type == "PLAYING":
        logger.info(f"Attempting to end tracking on {game_name} for user : {member_id}...")
        end_game_tracker(member_id, game_name, activity_type, guild_id, cur)
    else:
        logger.info(f"Attempting to end tracking on activity : {activity_type} for user : {member_id}...")
        end_voice_tracker(member_id, activity_type, guild_id, cur)
          

def check_for_activity(uid, gid, activity_type, cur: db.extensions.cursor):
    if activity_type == "PLAYING":
        cur.execute(
            """SELECT game_id FROM activity_tracker
                WHERE user_id = %s
                AND activity_type = %s
            """,(uid, activity_type)
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

    # This section is for the case when we need to end an IN CALL activity but need
    # to know if there is a STREAMING activity for the user so we can end that as well
    activity = "STREAMING"
    cur.execute(
        """SELECT * FROM activity_tracker
            WHERE user_id = %s
            AND activity_type = %s
        """,(uid, activity)
    )
    result = cur.fetchone()
    if result is None:
        return activity_errors.NO_CONFLICT
    else:
        return activity_errors.STREAM_IN_PROGRESS


def start_activity_tracker(member_id : int, game_name : str, activity_type : str, guild_id, cur : db.extensions.cursor, time_buffer : dt.timedelta = None):

    uid = get_user_id(member_id, cur)
    if time_buffer is not None:
        curr_time = dt.datetime.now(timezone.utc) + time_buffer
    else:
        curr_time = dt.datetime.now(timezone.utc)

    if activity_type == "PLAYING":
        logger.info(f"Attempting to start tracking {game_name} for user {member_id}...")

        gid = get_game_id_from_name(game_name, cur)
        game_filter = get_filterd_games(cur)
        if gid in game_filter:
            logger.info(f"Skipping recording game {game_name} because it is in the filter")
            return
        if uid == None or gid == None:
            logger.error(f"Game tracking start up for game : {game_name} and user {member_id} failed because either uid or gid were not found")
            return

        status_code = check_for_activity(uid, gid, activity_type, cur)

        if status_code == activity_errors.SESSION_ALREADY_IN_PROGRESS:
            logger.info(f"Tracking was not updated because {game_name} was already being tracked")
            return
        
        if status_code == activity_errors.DIFFERENT_GAME_IN_PROGRESS:
            logger.info(f"Different game was being tracked. Ending previous tracking for {member_id}")
            manually_end_game_session(uid, guild_id, activity_type, cur)

        cur.execute(
            """INSERT INTO activity_tracker (user_id, game_id, activity_type, start_time)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """,(uid, gid, activity_type, curr_time))
            
        update_user_game_time(None, uid, gid, cur)
        logger.info(f"Finalized tracking start up for game : {game_name} with user : {member_id}")
        return
    
    if activity_type == "IN CALL":
        logger.info(f"Attempting to start tracking time in call for user {member_id}...")
    if activity_type == "STREAMING":
        logger.info(f"Attempting to start tracking streaming time for user {member_id}...")

    # I'm thinking on starting a call I would need to check if we are also tracking a stream and if so we need to end it 
    # We need to do the same thing on stream end

    cur.execute(
        """INSERT INTO activity_tracker (user_id, activity_type, start_time, guild_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, activity_type) DO NOTHING
        """,(uid, activity_type, curr_time, guild_id))
    logger.info(f"Tracking for activity : {activity_type} started sucessfully")


def add_member_to_guilds_users_database(member, guild_id, cur : db.extensions.cursor):
    uid = get_user_id(member.id, cur)
    cur.execute(
        """SELECT * FROM guilds_users
            WHERE user_id = %s
            AND guild_id = %s
        """,(uid, guild_id))
    result = cur.fetchone()
    if result == None:
        logger.info(f"Attempting to add member: {member.id} ({member.name}) of guild : {guild_id} to guilds_users")
        cur.execute(
            """INSERT INTO guilds_users (guild_id, user_id)
                VALUES (%s,%s);
            """,(guild_id, uid))
        logger.info(f"Member: {member.id} ({member.name}) of guild : {guild_id} was added to the database")
    # then have to verify the guilds_users table
    else:
        user_name = get_discord_username(member.id, cur)
        logger.info(f"Verified memeber with username : {user_name} of guild : {guild_id} in guilds_users")


def add_member_to_users_database(member, cur : db.extensions.cursor):
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
    # then have to verify the guilds_users table
    else:
        user_name = get_discord_username(result[0], cur)
        logger.info(f"Verified memeber with username : {user_name}")


def verify_members_and_channels_in_database(total_guilds, bot_profile_id, cur : db.extensions.cursor):
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

        verify_guild_channels(guild, cur)
        

        for member in guild.members:
                if member.id != bot_profile_id:
                    add_member_to_users_database(member, cur)
                    add_member_to_guilds_users_database(member, guild.id, cur)


db_channel_collumn = {
    0 : "weekly_stats_channel_id",
    1 : "news_channel_id",
    2 : "level_up_channel_id"
}



def get_channel(channel_type, guild : discord.Guild, cur : db.extensions.cursor):
    # Get channel will get any channel id that is in the channel id collumn of the data base
    cur.execute(
        f"""SELECT {db_channel_collumn[channel_type]} FROM guilds
            WHERE guild_id = %s
        """,(guild.id,)
    )

    result = cur.fetchone()

    if result is None:
        logger.error(f"Guild {guild.id} does not exist")
        return None
    
    # The channel id is tested to make sure it is still valid
    channel = guild.get_channel(result[0])

    
    if channel is None:
        error = verify_guild_channels(guild, cur)
        # If a new channel fails to be set channel will be none
        if error:
            return None
        return get_channel(channel_type, guild, cur)

    return channel


def verify_guild_channels(guild : discord.Guild, cur : db.extensions.cursor):
    
    channel_list = guild.channels

    if len(channel_list) == 0:
        logger.error(f"Could not find ANY active channels for guild : {guild.id}")
        return
    cur.execute(
        """SELECT weekly_stats_channel_id, news_channel_id, level_up_channel_id FROM guilds
            WHERE guild_id = %s
        """,(guild.id,)
    )

    results = cur.fetchone()
    if results is None:
        return
    # Check if there are channel ids before this 
    for i,result in enumerate(results):
        if result is not None:
            if guild.get_channel(result) is None:
                logger.warning(f"Could not find a channel associated with id : {result} because it may have been deleted")
                cur.execute(
                    F"""UPDATE guilds
                        SET {db_channel_collumn[i]} = NULL
                        WHERE guild_id = %s
                    """,(guild.id,)
                )
                results = list(results)
                results[i] = None
                results = tuple(results)
    #print(results)
    default_channel_id = None
    channel_name = None
    
    for i,channel in enumerate(channel_list):
        if channel.type == discord.ChannelType.text:
            if default_channel_id is None:
                default_channel_id = channel.id
                channel_name = channel.name

            if channel.name == "general":
                default_channel_id = channel.id
                channel_name = channel.name
                break

    if default_channel_id is None:
        return "error"
    
    for i in range(3):
        if results[i] is None:
            logger.info(f"Setting default channel {db_channel_collumn[i]} for guild : {guild.id} to channel : {default_channel_id}({channel_name})")
            cur.execute(
                f"""UPDATE guilds
                    SET {db_channel_collumn[i]} = %s
                    WHERE guild_id = %s
                """,(default_channel_id, guild.id,)
            )

    logger.info(f"All channels for guild : {guild.id} verified")


def update_channel_id(channel_id, channel_collum, guild_id, cur : db.extensions.cursor):
    cur.execute(
        f"""UPDATE guilds
            SET {db_channel_collumn[channel_collum]} = %s
            WHERE guild_id = %s
        """,(channel_id, guild_id)
    )

    logger.info(f"Updated channel {db_channel_collumn[channel_collum]} to {channel_id}")
    
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

    # There is a chance that a game that doesn't exist could be played so if we don't find a backup image it might be best to abort

    if on_steam == False:
        logger.info(f"{name} was not found on steam. Getting image from igdb")
        img = IGDBClient.get_alt_url(name)
        gid = get_game_id_from_name(name,cur)
        if game_in_db_from_gid(gid,cur): # If the game is in the database
            if get_on_steam_from_db(gid,cur): # If the game in the database says it can be found on steam
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
        if img is None:
            print(
                f"\n\n\n None for game : {name} \n\n\n"
            )
        gid = get_game_id_from_name(name, cur)
        if game_in_db_from_gid(gid,cur):
            prev_img = get_game_img(gid,cur)
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

def add_game_to_database_from_steam_with_name_conflict(game_data, cur : db.extensions.cursor):
    name = game_data['name']
    on_steam = True
    appid = game_data['appid']

    img, price = look_up_steam_image_and_price(appid)
    # If we know the game is on steam but the look up fuction failed to get an image then most likely there was a network issue
    logger.warning(f"There was a name conflict with two games ({name}) having the same name but different ids. The older id has now been updated")
    print(f"There was a name conflic with {name}")
    #return
    if game_name_in_database(name,cur):
        gid = get_game_id_from_name(name, cur)
        prev_img = get_game_img(gid, cur)
        if prev_img is not None and img is None:
            logger.warning(f"Tried to update game: {name} with an image that doesn't exist. Keeping existing image")
            return
    cur.execute(
        """INSERT INTO games (game_name, on_steam, img, steam_app_id, steam_price)
            VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT (game_name)
                DO UPDATE 
                    SET
                        game_name = EXCLUDED.game_name,
                        on_steam = EXCLUDED.on_steam,
                        img = EXCLUDED.img,
                        steam_app_id = EXCLUDED.steam_app_id,
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
def update_user_recently_played(uid, steam_id, game_filter, cur : db.extensions.cursor):
    # only update if value is older than the last two weeks or none
    
    games = get_recently_played_games(steam_id)
    print(games)
    if games is None or len(games) == 0 or games['total_count'] == 0:
        return
   
    today = dt.datetime.now(timezone.utc)
    date = today
    recency_scaling = dt.timedelta(days = 1)
    for game in games['games']:
        if check_if_game_is_updatable(game, uid, cur):
            
            appid = game['appid']
            if appid in game_filter:
                logger.info(f"Did not update recently played because {game['name']} is in the filter")
                continue

            gid = get_game_id(appid, cur)

            cur.execute(
                """UPDATE user_games
                    SET
                        last_time_played = %s
                    WHERE user_id = %s
                    AND game_id = %s
                """,(date, uid, gid)
            )
            print(f"Updated rows: {cur.rowcount} of time played")
            new_date = date - recency_scaling
            # Recently played gives the games played within a 14 day period
            # If the user has played over 14 different games we want to make sure we don't scale past our 14 day period
            if (today - new_date).days < 14:
                date = new_date

def get_user_steam_id(member_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)
    cur.execute(
        """SELECT steam_id FROM general_steam_data
            WHERE user_id = %s
        """,(uid,)
    )

    result = cur.fetchone()
    if result is None:
        logger.warning(f"Could not find steam id for user : {uid}")
        return result

    return result[0]

def get_curr_steam_playtime(uid, gid, cur : db.extensions.cursor):
    cur.execute(
        """SELECT steam_playtime FROM user_games
            WHERE user_id = %s
            AND game_id = %s
        """,(uid, gid)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find playtime for uid : {uid} with game gid : {gid}")
        return result

    return result[0]

def get_last_sync_date(uid, cur : db.extensions.cursor):
    cur.execute(
        """SELECT last_sync FROM general_steam_data
            WHERE user_id = %s
        """,(uid,)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find the last time user : {uid} linked their account")
        return

    return result[0]

    

def game_name_in_database(game_name, cur : db.extensions.cursor):
    cur.execute(
        """SELECT game_name FROM games
            WHERE game_name = %s
        """,(game_name,)
    )

    result = cur.fetchone()
    if result is None:
        return False

    return True

def last_synced_within_two_weeks(last_sync_date):
    
    if last_sync_date >= (dt.datetime.now(timezone.utc) - dt.timedelta(weeks = 2)):
        return True

    return False


def get_total_time_played_in_past_period(period_start, uid, gid, cur : db.extensions.cursor):
    
    cur.execute(
        """SELECT activity_time FROM server_log
            WHERE user_id = %s
            AND game_id = %s
            AND start_time > %s
        """,(uid, gid, period_start)
    )

    results = cur.fetchall()
    total_seconds = 0
    for result in results:
        total_seconds += result[0]

    return total_seconds


def link_steam_library(library_data : dict, steam_profile_data : dict, member_id : int, cur : db.extensions.cursor, conn : db.extensions.connection, is_sync = False):
    #conn,cur = create_connection()

    uid = get_user_id(member_id, cur)
    if uid is None:
        logger.error(f"could not find a uid for member : {member_id}")
        return

    # need to make sure to do a db lookup to see if the game already exists
    # might need to use locks to ensure one sync at a time
    logger.info(library_data)

    game_filter = get_filterd_games(cur)

    throttle_counter = 0
    for i, game in enumerate(library_data['games']):
        # We might need to check to see if the game is marked as not on steam so we can update it 
        app_id = game['appid']

        if game_in_db(app_id, cur):
            if not is_sync:
                logger.info(f"Processing {game['name']} from existing game data")
        else:
            logger.info(f"Processing {game['name']} appid : {app_id} from new game data")
            if game_name_in_database(game['name'], cur):
                add_game_to_database_from_steam_with_name_conflict(game, cur)
            else:
                add_game_to_database_from_steam(game,cur)
            # We add a cooldown to API look ups in order to not stress the network on the deployment 
            throttle_counter += 1
            if throttle_counter >= 30:
                throttle_counter = 0
                conn.commit()
                logger.info(f"Throttle limit reached. Commiting data for batch {i + 1}/{len(library_data['games'])} before resting")
                time.sleep(25)
        
        gid = get_game_id(app_id, cur)
        if gid in game_filter:
            logger.debug(f"Skipping game {game['name']} because it was found in the filter")
            continue
        playtime = game['playtime_forever']
        playtime_seconds = playtime * 60
        # If sync then we need to do a database lookup to see if the game has a different time played than what is stored
        # If that is the case we need to update the last time played to today and then add that playtime to the server log
        # No xp will be given but maybe it can contribute to mvp
        if is_sync:
            today = dt.datetime.now(timezone.utc)
            logger.info(f"Starting syncing process for user : {uid} with gid {gid}")
            old_time_seconds = get_curr_steam_playtime(uid, gid, cur)
            
            last_sync = get_last_sync_date(uid, cur)
            if (
                old_time_seconds is not None 
                and playtime_seconds > old_time_seconds 
            ):
                date_buffer = today - dt.timedelta(hours = 12)

                if last_synced_within_two_weeks(last_sync):

                    time_on_record = get_total_time_played_in_past_period(last_sync, uid, gid, cur)
                    time_difference = playtime_seconds - old_time_seconds - time_on_record
                    if time_difference < 0:
                        time_difference = 0

                    cur.execute(
                        """UPDATE user_games
                            SET 
                                last_time_played = %s,
                                server_hours = server_hours + %s
                            WHERE user_id = %s
                            AND game_id = %s
                        """,( date_buffer, time_difference, uid, gid)
                    )
                    logger.info(f"Adding {time_difference} seconds of playtime for user : {uid} in game : {gid}")
                    add_to_server_log_for_syncing_process(uid, gid, "PLAYING", time_difference, date_buffer, cur)
                    if last_sync >= today - dt.timedelta(weeks = 1):
                        calculate_user_xp(member_id, None, "PLAYING", time_difference, cur)
                else:
                    cur.execute(
                        """UPDATE user_games
                            SET 
                                last_time_played = %s
                            WHERE user_id = %s
                            AND game_id = %s
                        """,(date_buffer, uid, gid)
                    )
                    logger.info(f"Updating last_time_played for user : {uid} in game : {gid} but not server hours because the last sync is too old")
                
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
    profile_pic = steam_profile_data['player']['avatarfull']
    if total_steam_time is None:
        total_steam_time = 0
    cur.execute(
        """INSERT INTO general_steam_data (user_id, steam_id, account_name, creation_time, steam_games_count, account_cost, total_steam_time, auto_sync_steam, last_sync, profile_pic)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE
                SET 
                    steam_id = EXCLUDED.steam_id,
                    account_name = EXCLUDED.account_name,
                    creation_time = EXCLUDED.creation_time,
                    steam_games_count = EXCLUDED.steam_games_count,
                    account_cost = EXCLUDED.account_cost,
                    total_steam_time = EXCLUDED.total_steam_time,
                    last_sync = EXCLUDED.last_sync,
                    profile_pic = EXCLUDED.profile_pic
        """,(uid, steam_id, steam_name, creation_time, game_count, total_library_cost, total_steam_time, True, dt.datetime.now(timezone.utc), profile_pic)
    )

    # I think it would be a good idea to pass a status into this function called link/sync
    # If we are linking (getting steam info for the first time) we use the update recently played otherwise we don't need to use that function
    if not is_sync:
        update_user_recently_played(uid, steam_id, game_filter, cur)

    logger.info(f"Library fully processed for {steam_name}")
    print(f"Library fully processed for {steam_name}")


def remove_user_steam_data(dicord_id, cur: db.extensions.cursor):
    uid = get_user_id(dicord_id, cur)

    logger.info(f"Deleting data in user_games with id : {uid}")
    cur.execute(
        """DELETE FROM user_games
            WHERE user_id = %s 
            AND seen_playing_in_server = false
            AND server_hours = 0
        """,(uid,))
    
    cur.execute(
        """UPDATE user_games
            SET steam_playtime = NULL
            WHERE user_id = %s 
            AND seen_playing_in_server = true;
        """,(uid,))
    
    cur.execute(
        """DELETE FROM general_steam_data
            WHERE user_id = %s
        """,(uid,))
    logger.info(f"Deleting data in general_steam_data with id : {uid}")


def get_user_server_stats(member_id, guild_id, cur : db.extensions.cursor):
    stats = []

    uid = get_user_id(member_id, cur)

    
    cur.execute(
        """SELECT total_messages_sent, total_stream_time, total_call_time, guild_level, xp, mvps, second_places, third_places
            FROM guilds_users
            WHERE guild_id = %s
            AND user_id = %s
        """,(guild_id, uid)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find user stats for user with discord id : {member_id} in guild : {guild_id}")
        return None

    for stat in result:
        stats.append(stat)

    cur.execute(
        """SELECT server_hours FROM user_games
            WHERE user_id = %s
            AND server_hours > 0
        """,(uid,)
    )

    result = cur.fetchall()

    if not result:
        stats.append(0)
        return stats

    total = 0
    for time in result:
        total += time[0]
    stats.append(total)

    return stats


def get_user_steam_stats (member_id, cur : db.extensions.cursor):
    steam_stats = []
    uid = get_user_id(member_id, cur)
    if uid is None:
        return
    
    cur.execute(
        """SELECT account_name, creation_time, steam_games_count, account_cost, total_steam_time, last_sync, profile_pic, auto_sync_steam
            FROM general_steam_data
            WHERE user_id = %s
        """,(uid,)
    )

    result = cur.fetchone()
    if result is None:
        logger.warning(f"Could not find steam data for user : {uid}")
        return result

    for stat in result:
        steam_stats.append(stat)
    # today = dt.datetime.now(timezone.utc)
    # age = relativedelta(today, result[1])

    cur.execute(
        """SELECT game_id, steam_playtime FROM user_games
            WHERE user_id = %s
            ORDER BY steam_playtime DESC NULLS LAST
        """,(uid,)
    )

    most_played_game_data = {}
    result = cur.fetchone()
    
    if result is not None:
        gid = result[0]
        playtime = result[1]

        cur.execute(
            """SELECT game_name, img FROM games
                WHERE id = %s
            """,(gid,)
        )

        result = cur.fetchone()

        most_played_game_data[f'{result[0]}'] = {
            'playtime' : playtime,
            'img' : result[1]
        }

    steam_stats.append(most_played_game_data)
        
    #print(steam_stats)

    return steam_stats

# conn,cur = create_connection()
# x = get_user_steam_stats(938183066948612096, cur)
# print(x)
# close_connection(conn,cur)


def get_game_name_from_id(gid, cur : db.extensions.cursor):
    cur.execute(
        """SELECT game_name FROM games
            WHERE id = %s
        """,(gid,)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find game name for gid : {gid}")
        return None

    return result[0]

def add_game_to_library_list(game_library, result, cur : db.extensions.cursor):
    for game in result:
        game_name = get_game_name_from_id(game[0], cur)
        if game_name is None:
            game_library[f'{game_name}'] = None
            logger.error(f"Game {game_name} was not found in the data base so it's stats will be added as None")
        server_time = game[1]
        steam_time = game[2]
        game_stats = {
            'server_time' : server_time,
            'steam_time' : steam_time
        }
        game_library[f'{game_name}'] = game_stats

    return game_library


def get_user_total_game_library (member_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)
    game_library = {}

    cur.execute(
        """SELECT game_id, server_hours, steam_playtime FROM user_games
            WHERE user_id = %s
            AND last_time_played IS NOT NULL
            ORDER BY last_time_played DESC
        """,(uid,)
    )

    result = cur.fetchall()
    if not result:
        logger.warning(f"Could not find a date that was NOT null in library data for uid : {uid}")
    else:
        game_library = add_game_to_library_list(game_library, result, cur)

    # game_library = add_game_to_library_list(game_library, result, cur)
    # for game in result:
    #     game_name = get_game_name_from_id(game[0], cur)
    #     if game_name is None:
    #         game_library[f'{game_name}'] = None
    #         logger.error(f"Game {game_name} was not found in the data base so it's stats will be added as None")
    #     server_time = game[1]
    #     steam_time = game[2]
    #     game_stats = {
    #         'server_time' : server_time,
    #         'steam_time' : steam_time
    #     }
    #     game_library[f'{game_name}'] = game_stats

    cur.execute(
        """SELECT game_id, server_hours, steam_playtime FROM user_games
            WHERE user_id = %s
            AND last_time_played IS NULL
        """,(uid,)
    )

    result = cur.fetchall()
    if not result:
        logger.warning(f"Could not find a data was null in library data for uid : {uid}")
    else:
        game_library = add_game_to_library_list(game_library, result, cur)

    if len(game_library) == 0:
        logger.warning(f"Could not any game data for user with uid : {uid}")
        return None
    
    return game_library



def get_recently_played_game_img(member_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)

    cur.execute(
        """SELECT game_id FROM user_games
            WHERE user_id = %s
            ORDER BY last_time_played DESC NULLS LAST
        """,(uid,)
    )

    result = cur.fetchone()
    if result is None:
        logger.warning(f"Could not find games for user : {uid}")
        return None, None

    gid = result[0]

    cur.execute(
        """SELECT game_name, img FROM games
            WHERE id = %s
        """,(gid,)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find a game matching gid : {gid}")
        return None, None
    
    game_name = result[0]
    img = result[1]

    return game_name, img

def create_clock():
    activity_clock = []
    for i in range(24):
        activity_clock.append(0)

    return activity_clock

def process_activity_data(uid, from_time, to_time, week_period, activity_calendar, cur : db.extensions.cursor):
    activity_clock = create_clock()
    carry_over_clock = create_clock()
    pacific = ZoneInfo("America/Los_Angeles")

    cur.execute(
        """SELECT start_time, activity_time FROM server_log
            WHERE user_id = %s
            AND start_time >= %s
            AND start_time <= %s
            ORDER BY start_time ASC
        """,(uid, from_time, to_time)
    )
    
    results = cur.fetchall()

    if not results:
        print("No results")
        return activity_calendar
    
    cur_day = None
    # print(results)
    # print(len(results))
    for result in results:
        carry_time = False
        # print(type(result[0]))
        relative_time = result[0].astimezone(pacific)
        start_hour_index = relative_time.time().hour

        day = relative_time.weekday()
        #print(day)
        if cur_day is None:
            cur_day = day
        elif cur_day != day:
            cumulative_activity_time = sum(activity_clock)
            if cur_day in activity_calendar:
                activity_calendar[cur_day][week_period] += cumulative_activity_time
            else:
                if week_period == "week2":
                    activity_calendar[cur_day] = {
                        'week2' : cumulative_activity_time,
                        'week1' : 0
                    }
                else:
                    activity_calendar[cur_day] = {
                        'week2' : 0,
                        'week1' : cumulative_activity_time
                    }
            cur_day = day
            if carry_over_clock[0] != 0:
                activity_clock = carry_over_clock
                carry_over_clock = create_clock()
            else:
                activity_clock = create_clock()

        # print(start_hour_index)
        duration = result[1]
        while duration >= 3600 and carry_time is False:
            activity_clock[start_hour_index] = 1
            start_hour_index += 1
            duration -= 3600
            if start_hour_index >= 24:
                start_hour_index = 0
                carry_time = True

        while duration >= 3600 and carry_time is True:
            carry_over_clock[start_hour_index] = 1
            duration -= 3600
            start_hour_index += 1
            if start_hour_index >= 24:
                break

        if duration >= 60 and carry_time is False:
            if start_hour_index >= 24:
                carry_time = True
            hours = duration / 3600
            activity_clock[start_hour_index] = max(activity_clock[start_hour_index],hours)

        if duration >= 60 and carry_time is True:
            if start_hour_index < 24:
                hours = duration / 3600
                carry_over_clock[start_hour_index] = max(carry_over_clock[start_hour_index],hours)

        # print(activity_clock)
        # print(carry_over_clock)
        # print("\n")

    cumulative_activity_time = sum(activity_clock)
    if cur_day in activity_calendar:
        activity_calendar[cur_day][week_period] += cumulative_activity_time
    else:
        if week_period == "week2":
            activity_calendar[cur_day] = {
                'week2' : cumulative_activity_time,
                'week1' : 0
            }
        else:
            activity_calendar[cur_day] = {
                'week2' : 0,
                'week1' : cumulative_activity_time
            }

    #print(activity_calendar)
    return activity_calendar


def get_user_activity(member_id, cur : db.extensions.cursor):
    uid = get_user_id(member_id, cur)

    activity_calendar = {}
    # week 2
    logger.info(f"Getting profile activity for user : {uid} from two weeks ago")
    today = dt.datetime.now(timezone.utc)
    from_time = today - dt.timedelta(weeks = 2)
    to_time = today - dt.timedelta(weeks = 1)
    
    activity_calendar = process_activity_data(uid, from_time, to_time, "week2", activity_calendar, cur)

    # week 1
    logger.info(f"Getting profile activity for user : {uid} from one week ago")
    from_time = today - dt.timedelta(weeks = 1)
    to_time = today
    
    activity_calendar = process_activity_data(uid, from_time, to_time, "week1", activity_calendar, cur)

    logger.info(activity_calendar)
    #print(activity_calendar)
    return activity_calendar

def get_total_weekly_messages(uid, guild_id, cur : db.extensions.cursor):
    cur.execute(
        """SELECT messages_sent_this_week FROM guilds_users
            WHERE guild_id = %s
            AND user_id = %s
        """,(guild_id, uid)
    )

    result = cur.fetchone()
    if result is None:
        logger.warning(f"Could not find message data for user : {uid}")
        return 0

    return result[0]

def get_mvp_scaling(uid, guild_id, cur : db.extensions.cursor):
    cur.execute(
        """SELECT mvp_mult FROM guilds_users
            WHERE guild_id = %s
            AND user_id = %s
        """,(guild_id, uid)
    )

    result = cur.fetchone()
    if result is None:
        logger.warning(f"Could not find message data for user : {uid}")
        return 100

    return result[0]


def create_mvp_entry(mvp_data, discord_id, uid, guild_id, cur):

    mvp_data[discord_id] = {
        'playtime' : 0,
        'call_time' : 0,
        'stream_time' : 0,
        'messages' : get_total_weekly_messages(uid, guild_id, cur),
        'mvp_mult': get_mvp_scaling(uid, guild_id, cur)
    }


def get_week_long_server_data(guild, cur : db.extensions.cursor):

    guild_id = guild.id
    guild_members = []

    for member in guild.members:
        guild_members.append(get_user_id(member.id, cur))

    server_data = {
        'games' : {},
        'call' : {},
        'stream' : {},
        'top_game' : {
            'name' : None,
            'img' : None,
            'time' : 0
        }
    }

    mvp_data = {}
    end_date = dt.datetime.now(timezone.utc) - dt.timedelta(weeks = 1)
    cur.execute(
        """SELECT * FROM server_log
            WHERE start_time >= %s
            AND(
                guild_id = %s
                OR (
                    activity_type = 'PLAYING'
                    AND user_id = ANY(%s)
                )
            )
            ORDER BY start_time DESC
        """,(end_date, guild_id, guild_members)
    )

    results = cur.fetchall()

    if not results:
        logger.warning(f"Could not find data for guild id : {guild_id}")
        return None, None
    
    for result in results:
        activity_type = result[4]

        if activity_type == "PLAYING":
            gid = result[3]
            uid = result[2]
            discord_id = get_member_id(uid, cur)
            game_name = get_game_name_from_id(gid, cur)
            activity_time = result[5]

            server_data['games'].setdefault(game_name, {}).setdefault('players', {}).setdefault(discord_id, 0)
            server_data['games'].setdefault(game_name, {}).setdefault('total_time', 0)

            server_data['games'][game_name]['players'][discord_id] += activity_time
            server_data['games'][game_name]['total_time'] += activity_time

            if discord_id not in mvp_data:
                create_mvp_entry(mvp_data, discord_id, uid, guild_id, cur)
            
            mvp_data[discord_id]['playtime'] += activity_time

        elif activity_type == "IN CALL":
            uid = result[2]
            discord_id = get_member_id(uid, cur)
            activity_time = result[5]

            server_data['call'].setdefault(discord_id, 0)

            server_data['call'][discord_id] += activity_time

            if discord_id not in mvp_data:
                create_mvp_entry(mvp_data, discord_id, uid, guild_id, cur)
            
            mvp_data[discord_id]['call_time'] += activity_time

        elif activity_type == "STREAMING":
            uid = result[2]
            discord_id = get_member_id(uid, cur)
            activity_time = result[5]

            server_data['stream'].setdefault(discord_id, 0)

            server_data['stream'][discord_id] += activity_time

            if discord_id not in mvp_data:
                create_mvp_entry(mvp_data, discord_id, uid, guild_id, cur)
            
            mvp_data[discord_id]['stream_time'] += activity_time

    top_game = None
    top_time = 0
    game_list = list(server_data['games'].items())


    for game_name, game_data in game_list:
        cur_game = game_name
        cur_time = game_data['total_time']

        if cur_time > top_time:
            top_game = cur_game
            top_time = cur_time

    if top_game is not None:
        server_data['top_game']['name'] = top_game

        gid = get_game_id_from_name(top_game, cur)
        server_data['top_game']['img'] = get_game_img(gid, cur)

        server_data['top_game']['time'] = top_time

    print(server_data)
    print('\n')

    return(server_data, mvp_data)

def adjust_mvp_mult(discord_id, guild_id, reset : bool, cur : db.extensions.cursor):
    uid = get_user_id(discord_id, cur)
    if uid is None:
        return
    
    if reset:
        cur.execute(
            """UPDATE guilds_users
                SET mvp_mult = 80
                WHERE user_id = %s
                AND guild_id = %s
            """,(uid, guild_id)
        )
    else:
        cur.execute(
            """UPDATE guilds_users
                SET mvp_mult = LEAST(mvp_mult + 15, 160)
                WHERE user_id = %s
                AND guild_id = %s
            """,(uid, guild_id)
        )

def update_user_mvp_data(discord_id, guild_id, placement, cur : db.extensions.cursor):
    uid = get_user_id(discord_id, cur)
    if uid is None:
        return
    
    match placement:
        case 0:
            column = "mvps"
            add_user_xp(discord_id, guild_id, 100, cur)
            adjust_mvp_mult(discord_id, guild_id, True, cur)
        case 1:
            column = "second_places"
            add_user_xp(discord_id, guild_id, 50, cur)
            adjust_mvp_mult(discord_id, guild_id, False, cur)
        case 2:
            column = "third_places"
            add_user_xp(discord_id, guild_id, 25, cur)
            adjust_mvp_mult(discord_id, guild_id, False, cur)
        case _:
            return
        
    cur.execute(
        f"""
        UPDATE guilds_users
        SET {column} = {column} + 1
        WHERE user_id = %s
        AND guild_id = %s
        """,
        (uid, guild_id)
    )

def add_user_xp(member_id, guild_id, add_value, cur : db.extensions.cursor):

    uid = get_user_id(member_id, cur)
    if uid is None:
        return
    
    if guild_id is not None:
        logger.info(f"Adding {add_value} xp to uid : {uid} in guild : {guild_id}")
        cur.execute(
            """UPDATE guilds_users
                SET xp = xp + %s
                WHERE user_id = %s
                AND guild_id = %s
            """,(add_value, uid, guild_id)
        )
    else:
        logger.warning(f"Adding {add_value} xp to uid : {uid} in ALL guilds")
        cur.execute(
            """UPDATE guilds_users
                SET xp = xp + %s
                WHERE user_id = %s
            """,(add_value, uid)
        )

def update_user_message_count(member_id, guild_id, cur : db.extensions.cursor):
    
    uid = get_user_id(member_id, cur)
    if uid is None:
        return

    if get_total_weekly_messages(uid, guild_id, cur) < 20:
        add_user_xp(member_id, guild_id, 100, cur)

    cur.execute(
        """UPDATE guilds_users
            SET 
                total_messages_sent = total_messages_sent + 1,
                messages_sent_this_week = LEAST(messages_sent_this_week + 1, 20)
            WHERE user_id = %s
            AND guild_id = %s
        """,(uid, guild_id)
    )

def get_mvp_id(guild_id, cur : db.extensions.cursor):
    cur.execute(
        """SELECT mvp_role_id FROM guilds
            WHERE guild_id = %s
        """,(guild_id,)
    )

    result = cur.fetchone()
    if result is None:
        logger.error(f"Could not find mvp data for guild : {guild_id}")
        return "error"

    return result[0]

def update_mvp_role_id(role_id, guild_id, cur : db.extensions.cursor):
    cur.execute(
        """UPDATE guilds
            SET mvp_role_id = %s
            WHERE guild_id = %s
        """,(role_id, guild_id)
    )

# conn,cur = create_connection()
# get_week_long_server_data(1534754711536799864, cur)
# close_connection(conn,cur)  


def get_all_user_games(on_steam : bool, cur : db.extensions.cursor):
    if on_steam:
        cur.execute(
            """SELECT DISTINCT games.steam_app_id
                FROM games
                JOIN user_games
                    ON games.id = user_games.game_id
                WHERE games.on_steam = %s
            """,(on_steam,)
        )
    else:
        cur.execute(
            """SELECT DISTINCT games.game_name
                FROM games
                JOIN user_games
                    ON games.id = user_games.game_id
                WHERE games.on_steam = %s
            """,(on_steam,)
        )
    results = cur.fetchall()
    if not results and on_steam:
        logger.warning(f"Could not find any Steam games in user_games database")
    if not results and not on_steam:
        logger.warning(f"Could not find any NON-Steam games in user_games database")
    return results


def enrich_game_to_database_from_steam(app_id, cur : db.extensions.cursor):
    on_steam = True
    appid = app_id

    name, img, price = enriched_info(appid)
    if name is None:
        return
    # If we know the game is on steam but the look up fuction failed to get an image then most likely there was a network issue
    if game_in_db(appid,cur):
        logger.info(f"currently enriching game : {name}")
        print(f"currently enriching game : {name}")
        gid = get_game_id(appid, cur)
        prev_img = get_game_img(gid, cur)
        if prev_img is not None and img is None:
            logger.warning(f"Tried to update game with Steam id: {app_id} with an image that doesn't exist. Keeping existing image")
            print(f"Tried to update game with Steam id: {app_id} with an image that doesn't exist. Keeping existing image")
            return
    cur.execute(
        """INSERT INTO games (on_steam, img, steam_app_id, steam_price)
            VALUES(%s,%s,%s,%s)
            ON CONFLICT (steam_app_id)
                DO UPDATE 
                    SET
                        on_steam = EXCLUDED.on_steam,
                        img = EXCLUDED.img,
                        steam_price = EXCLUDED.steam_price
        """,(on_steam, img, appid, price)
    )


def game_batch_sync(batch):
    conn, cur = create_connection()
    try:
        for game_id in batch:
            enrich_game_to_database_from_steam(game_id[0], cur)
    finally:
        close_connection(conn, cur)


async def enrich_games_database(IGDBclient):
    conn, cur = create_connection()
    try:
        steam_games = get_all_user_games(on_steam = True, cur = cur)
        non_steam_games = get_all_user_games(on_steam = False, cur = cur)
    finally:
        close_connection(conn, cur)

    if steam_games:
        async def sync_batch(batch, batch_number, max_games):
            await asyncio.to_thread(game_batch_sync, batch)
            logger.info(f"Completed games {batch_number}/{max_games}")
            print(f"Completed games {batch_number}/{max_games}")

        tasks = []
        for i in range(0, len(steam_games), 30):
            batch = steam_games[i : i + 30]
            batch_number = min(len(steam_games), i + 30)
            tasks.append(asyncio.create_task(sync_batch(batch, batch_number, len(steam_games))))

            if len(tasks) == 3:
                await asyncio.gather(*tasks)
                tasks = []
                if i + 30 < len(steam_games):
                    logger.info(f"Now resting for 2 minutes")
                    print("Now resting for 2 minutes")
                    await asyncio.sleep(120)

        if tasks:
            await asyncio.gather(*tasks)

    if non_steam_games:
        await asyncio.to_thread(enrich_games_not_from_steam, non_steam_games, IGDBclient)

    print("Enrichment process completed")
    logger.info("Enrichment process completed")


def enrich_games_not_from_steam(non_steam_games, IGDBclient):
    conn, cur = create_connection()
    try:
        for game_name in non_steam_games:
            print(f"Currently enriching game : {game_name}")
            logger.info(f"Currently enriching game : {game_name}")
            add_game_to_database(game_name[0], IGDBclient, cur)
            time.sleep(15)
    finally:
        close_connection(conn, cur)


def update_game_filter(game_name):
    
    conn, cur = create_connection()
    try:
        game_id = get_game_id_from_name(game_name, cur)
        if game_id is None:
            print(f"Couldn't find game {game_name}")
            logger.warning(f"Could not find game : {game_name} in filter")
            return f"Could not find game : {game_name} in filter"

        print(f"Updating filter with game : {game_name}")
        cur.execute(
            """INSERT INTO game_filter(game_name, game_id)
                VALUES(%s,%s)
                ON CONFLICT DO NOTHING
            """,(game_name, game_id)
        )
        logger.info(f"Filtering out {game_name} from user data")
        cur.execute(
            """DELETE FROM user_games
                WHERE game_id = %s
            """,(game_id,)
        )
    finally:
        close_connection(conn, cur)
        
    return f"Filtered out {game_name} with id: {game_id} from user data"


def get_filterd_games(cur : db.extensions.cursor):
    filter = []
    cur.execute(
        """SELECT game_id FROM game_filter
        """
    )

    results = cur.fetchall()
    if not results:
        logger.info("There are currently no games in the filter")
        return filter

    for result in results:
        filter.append(result[0])

    return filter

# update_game_filter("fdd")
# conn, cur = create_connection()
# games = get_filterd_games(cur)
# print(games)
# if 104 in games:
#     print("found")
# close_connection(conn,cur)

def calculate_user_xp(member_id, guild_id, activity_type, activity_length, cur : db.extensions.cursor):
    xp = 0
    match activity_type:
        case "PLAYING":
            xp = (activity_length / 900) * 2
        case "IN CALL":
            xp = (activity_length / 900) * 3
        case "STREAMING":
            xp = (activity_length / 900) * 6

    xp = int(xp * 100)
    logger.info(f"Calculated {xp} xp for member : {member_id} from guild : {guild_id}")
    add_user_xp(member_id, guild_id, xp, cur)


def update_user_level(level, guild_id, member_id):
    conn, cur = create_connection()
    try:
        uid = get_user_id(member_id, cur)
        if uid is None:
            return
        
        cur.execute(
            """UPDATE guilds_users
                SET guild_level = %s
                WHERE user_id = %s
                AND guild_id = %s
            """,(level, uid, guild_id)
        )
    finally:
        close_connection(conn, cur)

def get_auto_sync_value(member_id):
    conn,cur = create_connection()

    try:
        uid = get_user_id(member_id, cur)
        cur.execute(
            """SELECT auto_sync_steam FROM general_steam_data
                WHERE user_id = %s
            """,(uid,)
        )

        result = cur.fetchone()
        if result is None:
            logger.error(f"Could not find auto-sync data for user : {uid}")
            return
        return result[0]
    
    finally:
        close_connection(conn, cur)

def auto_sync_toggle_set(member_id, value):
    conn,cur = create_connection()
    try:
        toggle = value

        if toggle is None:
            uid = get_user_id(member_id, cur)
            if uid is None:
                return
            
            cur.execute(
                """SELECT auto_sync_steam FROM general_steam_data
                    WHERE user_id = %s
                """,(uid,)
            )

            result = cur.fetchone()
            if result is None:
                logger.error(f"Could not find auto-sync data for user : {uid}")
                return

            toggle = result[0]
            if toggle == True:
                toggle = False
            elif toggle == False:
                toggle = True
            
        cur.execute(
            """UPDATE general_steam_data
                SET auto_sync_steam = %s
            """,(toggle,)
        )
        return toggle
    finally:
        close_connection(conn, cur)


def weekly_cleanup():
    conn,cur = create_connection()

    try:
        logger.info("resetting weekly user messages")
        print("resetting weekly user messages")
        print("Cleaning up news filter from the last 2 days")

        cur.execute(
            """UPDATE guilds_users
                SET messages_sent_this_week = 0
            """
        )
    finally:
        close_connection(conn, cur)

def daily_cleanup():
    
    conn,cur = create_connection()
    today = dt.datetime.now(timezone.utc)
    try:
        logger.info("Cleaning up news filter from the last 2 days")
        print("Cleaning up news filter from the last 2 days")

        last_2_days = today - dt.timedelta(days=2)
        cur.execute(
            """DELETE FROM todays_news
                WHERE date_added < %s
            """,(last_2_days,)
        )

        logger.info("Cleaning up server log from the last 2 weeks")
        print("Cleaning up server log from the last 2 days")

        last_2_weeks = today - dt.timedelta(weeks=2)
        cur.execute(
            """DELETE FROM server_log
                WHERE start_time < %s
            """,(last_2_weeks,)
        )
    finally:
        close_connection(conn, cur)

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

LINK_SEM = asyncio.Semaphore(7)
async def linking_task(app_id, is_sync, game, i, library_data, game_filter, uid, member_id):
    async with LINK_SEM:
        await asyncio.to_thread(linking_process_for_threading, app_id, is_sync, game, i, library_data, game_filter, uid, member_id)


def linking_process_for_threading(app_id, is_sync, game, i, library_data, game_filter, uid, member_id):
    conn, cur = create_connection()
    try:
        
        logger.info(f"Processing {game['name']} appid : {app_id} from new game data")
        print(f"Processing {game['name']} appid : {app_id}")
        if game_name_in_database(game['name'], cur):
            add_game_to_database_from_steam_with_name_conflict(game, cur)
        else:
            add_game_to_database_from_steam(game,cur)
            
        
        gid = get_game_id(app_id, cur)
        if gid in game_filter:
            logger.debug(f"Skipping game {game['name']} because it was found in the filter")
            return
        playtime = game['playtime_forever']
        playtime_seconds = playtime * 60
        # If sync then we need to do a database lookup to see if the game has a different time played than what is stored
        # If that is the case we need to update the last time played to today and then add that playtime to the server log
        # No xp will be given but maybe it can contribute to mvp
        
        cur.execute(
            """INSERT INTO user_games (user_id, game_id, steam_playtime)
                VALUES(%s,%s,%s)
                ON CONFLICT (user_id, game_id)
                DO UPDATE
                    SET steam_playtime = EXCLUDED.steam_playtime
            """,(uid, gid, playtime_seconds))
    finally:
        close_connection(conn, cur)

async def link_steam_library_async(library_data : dict, steam_profile_data : dict, member_id : int, cur : db.extensions.cursor, conn : db.extensions.connection, is_sync = False):
    #conn,cur = create_connection()

    uid = get_user_id(member_id, cur)
    if uid is None:
        logger.error(f"could not find a uid for member : {member_id}")
        return

    # need to make sure to do a db lookup to see if the game already exists
    # might need to use locks to ensure one sync at a time
    logger.info(library_data)

    game_filter = get_filterd_games(cur)

    tasks = []
    throttle_counter = 0
    for i, game in enumerate(library_data['games']):
        # We might need to check to see if the game is marked as not on steam so we can update it 
        app_id = game['appid']

        if game_in_db(app_id, cur):
            if not is_sync:
                logger.info(f"Processing {game['name']} from existing game data")
            gid = get_game_id(app_id, cur)
            if gid in game_filter:
                logger.debug(f"Skipping game {game['name']} because it was found in the filter")
                continue
            playtime = game['playtime_forever']
            playtime_seconds = playtime * 60
            cur.execute(
                """INSERT INTO user_games (user_id, game_id, steam_playtime)
                    VALUES(%s,%s,%s)
                    ON CONFLICT (user_id, game_id)
                    DO UPDATE
                        SET steam_playtime = EXCLUDED.steam_playtime
                """,(uid, gid, playtime_seconds))
        else:
            tasks.append(asyncio.create_task(linking_task(app_id, is_sync, game, i, library_data, game_filter, uid, member_id)))

        if len(tasks) == 90:
            await asyncio.gather(*tasks)
            tasks = []
            print("resting for 2 minutes")
            await asyncio.sleep(120)

        if tasks:
            await asyncio.gather(*tasks)
    
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
    profile_pic = steam_profile_data['player']['avatarfull']
    if total_steam_time is None:
        total_steam_time = 0
    cur.execute(
        """INSERT INTO general_steam_data (user_id, steam_id, account_name, creation_time, steam_games_count, account_cost, total_steam_time, auto_sync_steam, last_sync, profile_pic)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE
                SET 
                    steam_id = EXCLUDED.steam_id,
                    account_name = EXCLUDED.account_name,
                    creation_time = EXCLUDED.creation_time,
                    steam_games_count = EXCLUDED.steam_games_count,
                    account_cost = EXCLUDED.account_cost,
                    total_steam_time = EXCLUDED.total_steam_time,
                    last_sync = EXCLUDED.last_sync,
                    profile_pic = EXCLUDED.profile_pic
        """,(uid, steam_id, steam_name, creation_time, game_count, total_library_cost, total_steam_time, True, dt.datetime.now(timezone.utc), profile_pic)
    )

    # I think it would be a good idea to pass a status into this function called link/sync
    # If we are linking (getting steam info for the first time) we use the update recently played otherwise we don't need to use that function
    if not is_sync:
        update_user_recently_played(uid, steam_id, game_filter, cur)

    logger.info(f"Library fully processed for {steam_name}")
    print(f"Library fully processed for {steam_name}")


if __name__ == "__main__":
    # resetdb()
    # conn,cur = create_connection()
    # print(get_total_library_cost(938183066948612096,cur))
    # close_connection(conn, cur)
    pass