# SQL using psycopg2

## To create a table
```python
cur.execute("""CREATE TABLE IF NOT EXISTS person (
     id INT PRIMARY KEY,
     name VARCHAR (255),
     age INT,
     gender CHAR
 );
 """)
```

## To add to that created table 
```py
cur.execute("""INSERT INTO person (id, name, age, gender)
VALUES 
(1, 'Steve', 43, 'M'),
(2, 'Mike', 23, 'M'),
(3, 'Patty', 29, 'F'),
(4, 'Sue', 63, 'F'),
(5, 'Lary', 52, 'M');
""")
```
## To get values from DB
```py
cur.execute("SELECT * FROM person;")
```
or
```py
cur.execute("""SELECT * FROM person WHERE age < 50;
""")
```
you can also add
```py
ORDER BY age ASC LIMIT 100
```
to get the first 100 entries ordered by age from lowest to highest

## To use variables in query 
```py
sql = cur.mogrify("""SELECT * FROM  person WHERE starts_with(name,%s) AND age < %s;""", ("J", 50))

cur.execute(sql)

for entry in cur.fetchall():
    print(entry)
```

## To update a table
```py
cur.execute("""UPDATE person
SET
    name = 'Piablo',
    age = 635,
    gender = 'O'
WHERE id = 2;
""")
```
Update the table based on where clause
```py
cur.execute("""UPDATE person
SET
    credit_score = 800
WHERE age > 40 
AND (
    starts_with(name, 'J')
    OR starts_with(name, 'S')
);
""")
```
## To add a column
```py
cur.execute("""ALTER TABLE person
ADD COLUMN credit_score INT;
""")
```
## To delete a column
```py
cur.execute("""ALTER TABLE person
DROP COLUMN credit_score
""")
```
## Joins example

users
| id | username |
| -: | -------- |
|  1 | Mega     |
|  2 | Alice    |
|  3 | Bob      |


games
| id | game_name  |
| -: | ---------- |
|  1 | Minecraft  |
|  2 | Terraria   |
|  3 | Elden Ring |


user_games

| user_id | game_id |
| ------: | ------: |
|       1 |       1 |
|       1 |       2 |
|       2 |       1 |
|       3 |       3 |

```sql
SELECT users.username, games.game_name
FROM users
JOIN user_games
    ON users.id = user_games.user_id
JOIN games
    ON games.id = user_games.game_id;
```
Result
----------
| username | game_name  |
| -------- | ---------- |
| Mega     | Minecraft  |
| Mega     | Terraria   |
| Alice    | Minecraft  |
| Bob      | Elden Ring |

# Discord api
Basic Structure

```py
import discord

class Client(discord.Client):

    async def on_ready(self):
        print(f"Logged on as {self.user}")


intents = discord.Intents.default()
intents.message_content = True

client = Client(intents = intents)
client.run(os.getenv("DISCORD_TOKEN"))
```

## Sending a message
https://discordpy.readthedocs.io/en/stable/api.html#discord.DMChannel.send
```py
async def on_message(self, message):
    if message.contents.startswith("xxx"):
        await message.channel.send("saw the string xxx from {message.author.display_name}")
```

## Embeddings 

https://discordpy.readthedocs.io/en/stable/api.html#discord.Embed

example of the class
```py
class Embedding(discord.Embed):
    def __init__(self,url):
        super().__init__()
        self.description = "asdfasf"
        self.title = "Ball is Ball"
        self.url = url
        self.color = discord.Color.from_str("#B9B944")
        self.set_image(url=url)
        self.set_thumbnail(url = url)
        self.add_field(name="Games",value="🎮 Terraria\n🎮 Baldur's Gate 3\n🎮 Castlevania",inline=False)
        self.add_field(name="Favorite Game", value="Terraria")
```
example of sending an embedded message

```py
e = Embedding("url link")
await message.channel.send("This is just a message", embed = e)
```

can also string multiple embeds in one message
```py
e = Embedding("url link")
await message.channel.send(f"Hi there {message.author.display_name}", embeds = [e,e,e,e])
```
