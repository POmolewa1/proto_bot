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

class activity_errors(Enum):
    NO_CONFLICT = 0
    SESSION_ALREADY_IN_PROGRESS = 1
    DIFFERENT_GAME_IN_PROGRESS = 2
    STREAM_IN_PROGRESS = 3

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
        user_name VARCHAR(255)

    );
    """)
    logger.info(f"Verified table: users")

    cur.execute("""CREATE TABLE IF NOT EXISTS guilds_users (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        guild_id BIGINT REFERENCES guilds(guild_id),
        user_id INT REFERENCES users(id),

        total_messages_sent INT DEFAULT 0,
        messages_sent_this_week INT DEFAULT 0,
        total_stream_time INT DEFAULT 0,
        total_call_time INT DEFAULT 0,

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
        gid INT UNIQUE
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


def add_to_todays_news(news_title, gid, cur : db.extensions.cursor):
    cur.execute(
        """INSERT INTO todays_news (article_title, gid)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """,(news_title, gid)
    )


def process_member_games_into_news(member_id_list):
    conn,cur = create_connection()
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
    close_connection(conn, cur)
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


def restart_tracked_activities(cur : db.extensions.cursor):

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

    
def add_to_server_log_for_syncing_process(uid, gid, activity_type, activity_time, start_time, cur : db.extensions.cursor):
    guild_list = get_user_guilds(uid, cur)
    for guild_id in guild_list:
        cur.execute(
            """INSERT INTO server_log (guild_id, user_id, game_id, activity_type, activity_time, start_time)
                VALUES (%s,%s,%s,%s,%s,%s)
            """,(guild_id, uid, gid, activity_type, activity_time, start_time)
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
    # Make sure to add a tracking limit here maybe 12 hours?
    total_time = time_in_game + time_played

    update_user_game_time(total_time, uid, gid, cur)
    remove_tracked_game(uid, gid, cur)
    add_to_server_log(uid, gid, activity_type, guild_id, time_played, start_time, cur)
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
                    add_member_to_users_database(member, cur)
                    add_member_to_guilds_users_database(member, guild.id, cur)

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

def last_synced_recently(uid, cur : db.extensions.cursor):
    cur.execute(
        """SELECT last_sync FROM general_steam_data
            WHERE user_id = %s
        """,(uid,)
    )

    result = cur.fetchone()
    if result is None:
        return False

    last_sync_date = result[0]

    if last_sync_date >= (dt.datetime.now(timezone.utc) - dt.timedelta(days = 2)):
        return True

    return False

 
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
            if not is_sync:
                logger.info(f"Processing {game['name']} from existing game data")
        else:
            logger.info(f"Processing {game['name']} from new game data")
            add_game_to_database_from_steam(game,cur)
            # We add a cooldown to API look ups in order to not stress the network on the deployment 
            throttle_counter += 1
            if throttle_counter >= 30:
                throttle_counter = 0
                conn.commit()
                logger.info(f"Throttle limit reached. Commiting data for batch {i + 1}/{len(library_data['games'])} before resting")
                time.sleep(25)
        
        gid = get_game_id(app_id, cur)
        playtime = game['playtime_forever']
        playtime_seconds = playtime * 60
        # If sync then we need to do a database lookup to see if the game has a different time played than what is stored
        # If that is the case we need to update the last time played to today and then add that playtime to the server log
        # No xp will be given but maybe it can contribute to mvp
        if is_sync:
            logger.info(f"Starting syncing process for user : {uid} with gid {gid}")
            old_time_seconds = get_curr_steam_playtime(uid, gid, cur)
            if (
                old_time_seconds is not None 
                and playtime_seconds > old_time_seconds 
                and last_synced_recently(uid,cur)
            ):
                date_buffer = dt.datetime.now(timezone.utc) - dt.timedelta(hours = 12)
                cur.execute(
                    """UPDATE user_games
                        SET last_time_played = %s
                        WHERE user_id = %s
                        AND game_id = %s
                    """,(date_buffer, uid, gid)
                )

                time_difference = playtime_seconds - old_time_seconds
                logger.info(f"Adding {time_difference} seconds of playtime for user : {uid} in game : {gid}")
                # technically this would need to be done for each guild the user is in
                add_to_server_log_for_syncing_process(uid, gid, "PLAYING", time_difference, date_buffer, cur)
            
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
        update_user_recently_played(uid, steam_id, cur)

    logger.info(f"Library fully processed for {steam_name}")


def remove_user_steam_data(dicord_id, cur: db.extensions.cursor):
    uid = get_user_id(dicord_id, cur)

    logger.info(f"Deleting data in user_games with id : {uid}")
    cur.execute(
        """DELETE FROM user_games
            WHERE user_id = %s 
            AND seen_playing_in_server = false;
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
        """SELECT total_messages_sent, total_stream_time, total_call_time, guild_level, xp 
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
        """SELECT account_name, creation_time, steam_games_count, account_cost, total_steam_time, last_sync, profile_pic
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
        logger.error("Could not find game name for gid : {gid}")
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

    
conn,cur = create_connection()
get_user_activity(938183066948612096, cur)
close_connection(conn,cur)       

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