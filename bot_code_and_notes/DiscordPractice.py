import os
from dotenv import load_dotenv
load_dotenv()
import discord
from discord.ext import commands
from discord import app_commands
import logging
import datetime as dt
from datetime import timezone
from SteamPractice import *
from DBpractice import *

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode ='w')
logging.basicConfig(level= logging.DEBUG, handlers=[handler], format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

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

class Client(commands.Bot):
    e = Embedding("https://cdn.discordapp.com/avatars/385277889404207105/fb8b1cae3be44ba623caee0610343864.png?size=1024")

    async def on_ready(self):
        print(f"Logged on as {self.user}")
        
        initialize_db()
        self.varify_guilds_and_members()

        try:
            guild = discord.Object(id = os.getenv("GUILD_ID"))
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {guild.id}")
        except Exception as e:
            print(f"Error syncing commands: {e}")


    async def on_message(self, message):
        # when a person says a message they gain xp
        #print(f"Message from {message.author}: {message.content}")
        if message.author == self.user:
            return
        if message.content.startswith("hello"):
            await message.channel.send(f"Hi there {message.author.display_name}")
            #await message.channel.send(f"Hi there {message.author.display_name}", embed = self.e)
            #await message.channel.send(f"Hi there {message.author.display_name}", embeds = [self.e,self.e,self.e,self.e])
            #await message.channel.send(f"Hi there {message.author.display_avatar.url}")

    async def on_reaction_add(self, reaction, user):
        await reaction.message.channel.send("You reacted")

    start_time = 0
    end_time = 0 
    # When the user changes their status the activity will be updated so after activity will need to check if there is a game that is currently being tracked
    async def on_presence_update(self, before: discord.Member, after: discord.Member):

        
        if after.activity == None and before.activity == None:
            return
       
        if before.activity != None:
            if before.activity.type == discord.ActivityType.playing:
                game = before.activity.name
                self.end_time = dt.datetime.now(timezone.utc)
        
                print(f"{before.display_name} has stopped playing {game} at {self.end_time}")
                print(f"played for {(self.end_time - self.start_time).total_seconds()} seconds")
   
        if after.activity != None:
            if after.activity.type == discord.ActivityType.playing:
                game = after.activity.name
                self.start_time = dt.datetime.now(timezone.utc)
                print(f"{after.display_name} has started to play {game} at {self.start_time}")


    

        # channel = self.get_channel(int(os.getenv("CHANNEL2_ID")))
        # if channel:
        #     print("printing to channel")
        #     print(f"{before.status.name} {after.status.name}")
        #     await channel.send(f"{after.display_name} has started to play {game}")
            # if before.status.name != after.status.name:
            #     await channel.send(f"""
            #                             {after.display_name} has gone from {before.status.name} to {after.status.name}
            #                         """)

        #print(before)
        #print(after)

    def varify_guilds_and_members(self):
        conn,cur = create_connection()

        for guild in self.guilds:
            try:
                cur.execute(
                """SELECT guilds.id 
                    FROM guilds
                    WHERE guilds.guild_id = %s;
                """,(guild.id,))

                if cur.fetchone() == None:
                    logging.info(f"attempting to add guild with id {guild.id} ({guild.name})")
                    cur.execute(
                        """INSERT INTO guilds (guild_id, guild_name)
                            VALUES (%s,%s);
                        """,(guild.id, guild.name))
                    logging.info(f"guild with id {guild.id} ({guild.name}) was added to the database")
            except Exception as e:
                print(f"something went wrong with: {e}")
                logging.error(f"Could not add guild with id {guild.id} ({guild.name})")

            #print(guild.name)
            #print(guild.id)
            for member in guild.members:
                
                if member.id != self.user.id:
                    cur.execute(
                        """SELECT users.discord_id
                            FROM users
                            WHERE users.discord_id = %s;
                        """,(member.id,))

                    if cur.fetchone() == None:
                        logging.info(f"Attempting to add member with id {member.id} ({member.name})")
                        cur.execute(
                            """INSERT INTO users (discord_id, user_name)
                                VALUES (%s,%s);
                            """,(member.id, member.name))
                        logging.info(f"Member with id {member.id} ({member.name}) was added to the database")
        close_connection(conn,cur)
        print("all members varified")


client = Client(command_prefix = "!", intents=intents)

GUILD_ID = discord.Object(id = os.getenv("GUILD_ID"))

@client.tree.command(name = "hello", description="say hello", guild= GUILD_ID)
async def say_hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hi there!")

@client.tree.command(name = "printer", description = "I will print whatever you send me", guild= GUILD_ID)
async def printer(interaction: discord.Interaction, printer: str):
    await interaction.response.send_message(printer)

@client.tree.command(name = "guildcard", description="print your guild card", guild=GUILD_ID)
async def guildcard(interaction: discord.Interaction, user: discord.Member):
    
    user_name = user.display_name
    picture = Embedding(user.display_avatar.url)
    #picture = Embedding("https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/2369900/header.jpg?t=1745815495")

    await interaction.response.send_message(f"Here is {user_name}'s profile", embed = picture)

    #await interaction.followup.send(print_db())

     # if user_name != interaction.user.display_name:
        #     await interaction.response.send_message(f"That is not your profile")
        # else:

client.run(os.getenv("DISCORD_TOKEN"), log_handler=handler, log_level=logging.DEBUG)