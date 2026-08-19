import psycopg2 as db
import os 
from dotenv import load_dotenv
load_dotenv()
import logging

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

        steam_id VARCHAR(255),
        steam_hours INT DEFAULT 0,
        steam_games_count INT DEFAULT 0,
        total_gaming_hours INT DEFAULT 0,
        auto_sync BOOLEAN DEFAULT FALSE
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
        game_name VARCHAR(255),

        on_steam BOOLEAN,
        img VARCHAR (255),
        steam_app_id INT
    );
    """)
    logger.info(f"Verified table: games")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_games (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_key INT REFERENCES users(id),
        game_id INT REFERENCES games(id),

        seen_playing_in_server BOOLEAN DEFAULT FALSE,
        server_hours INT DEFAULT 0,
        unsyced_hours INT DEFAULT 0,
        last_time_played INT,
        steam_play_time INT
    );
    """)
    logger.info(f"Verified table: user_games")

    cur.execute("""CREATE TABLE IF NOT EXISTS general_steam_data (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id INT REFERENCES users(id),

        account_age INT,
        steam_games_count INT DEFAULT 0,
        steam_time INT,
        last_sync INT
    );
    """)
    logger.info(f"Verified table: general_steam_data")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_recently_played (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_key INT REFERENCES users(id),

        g1 INT,
        g2 INT,
        g3 INT,
        g4 INT,
        g5 INT
    );
    """)
    logger.info(f"Verified table: user_recently_played")

    # cur.execute("""CREATE TABLE IF NOT EXISTS daily_game_stats (
    #     id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    #     user_key INT,
    #     game_key INT,
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
        user_id INT REFERENCES users(id),
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

def add_cost(price):
    conn,cur = create_connection()

    cur.execute("""UPDATE person
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
    resetdb()