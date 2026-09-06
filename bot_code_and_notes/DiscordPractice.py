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
import asyncio
from igdbPractice import *
from discord.ext import tasks 
import random
from zoneinfo import ZoneInfo

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode ='w')
logging.basicConfig(level= logging.DEBUG, handlers=[handler], format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

lock = asyncio.Lock()
igdbclient = IGDBClient()

class ConfirmDeny(discord.ui.View):

    def __init__(self, discord_id):
        super().__init__()
        self.discord_user = discord_id
        self.confirmed = False
        self.message = None


    @discord.ui.button(label = "Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction : discord.Interaction, button):
        current_user = interaction.user.id
        if current_user != self.discord_user:
            await interaction.response.send_message(content="Sorry I'm pretty sure this isn't your command. Only the person who sent the command can interact with it", ephemeral=True)
            return
        self.confirmed = True

        await interaction.response.edit_message(content="Thank You",embed=None,view=None)
        self.message = interaction
        self.stop()


    @discord.ui.button(label = "Deny", style= discord.ButtonStyle.red)
    async def deny(self, interaction : discord.Interaction, button):
        current_user = interaction.user.id
        if current_user != self.discord_user:
            await interaction.response.send_message("Sorry I'm pretty sure this isn't your command. Only the person who sent the command can interact with it", ephemeral=True)
            return

        await interaction.response.edit_message(content="Got it. If the profile isn't the one you expected try searching by id name",embed=None,view=None) 
        self.stop()


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


class SampleDiscordProfile(discord.Embed):
    def __init__(self, profile_details):
        super().__init__()
        self.title = f"{profile_details['player']['personaname']}"
        #self.description = "Check the link if you're unsure"
        self.url = profile_details['player']['profileurl']
        self.set_image(url=profile_details['player']['avatarfull'])

class Client(commands.Bot):
    e = Embedding("https://cdn.discordapp.com/avatars/385277889404207105/fb8b1cae3be44ba623caee0610343864.png?size=1024")
    async def on_ready(self):
        print(f"Logged on as {self.user}")
        
        initialize_db()
        self.verify_guilds_and_members()

        try:
            guild = discord.Object(id = os.getenv("GUILD_ID"))
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {guild.id}")
        except Exception as e:
            print(f"Error syncing commands: {e}")

        if not get_game_news.is_running():
            get_game_news.start()



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

    
    # When the user changes their status the activity will be updated so after activity will need to check if there is a game that is currently being tracked
    async def on_presence_update(self, before: discord.Member, after: discord.Member):

        # Might be better to add the game to the db and then enrich it for tracking purposes
        if after.activity == None and before.activity == None:
            return

       # ending session is still not implemented yet
        if before.activity != None:
            if before.activity.type == discord.ActivityType.playing:
                game = before.activity.name
                end_time = dt.datetime.now(timezone.utc)
            
        
                print(f"{before.display_name} has stopped playing {game} at {end_time}")
                #print(f"played for {(end_time - start_time).total_seconds()} seconds")

        # At 12 or whenever make sure to calculate the time for all currently active games then add them to the players/guild. Then change the time to that current time. Maybe doesn't matter for weekly
        if after.activity != None:
            if after.activity.type == discord.ActivityType.playing:
                game = after.activity.name
                
                await asyncio.to_thread(start_game_tracking_process, game, after)

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

    def verify_guilds_and_members(self):

        conn,cur = create_connection()
        total_guilds = self.guilds
        bot_profile_id = self.user.id
        verify_member_in_database(total_guilds, bot_profile_id, cur)
        close_connection(conn,cur)

        print("All guilds and members verified")

    async def create_new_member_profile(interaction : discord.Interaction, steam_id : str):
        pass


# Bot command helpers
#-----------------
def create_response(url, user_list):
    variant = random.randint(1,3)
    members = ""

    count = 0
    for user in user_list:
        member = client.get_user(user)
        if len(user_list) > 2 and count != (len(user_list) - 1):
            members += f"{member.display_name}, "
            count += 1
        elif len(user_list) >= 2 and count == (len(user_list) - 1):
            members += f"and {member.display_name}"
            count += 1
        else:
            members += f"{member.display_name} "
            count += 1

    match variant:
        case 1:
            message = f"Hey {members}.\n I found some news that you might like to see \n {url}"
            return message
        case 2:
            message = f"Hey {members}.\n Check out this news \n {url}"
            return message
        case 3:
            message = f"Hey {members} \n I saw you guys playing this game recently and thought you might like to see this \n {url}"
            return message

def start_game_tracking_process(game, after : discord.Member):
    conn,cur = create_connection()
    if not game_name_in_database(game, cur):
        add_game_to_database(game, igdbclient, cur)
        add_game_to_user_profile(game, after.id, cur)
    close_connection(conn,cur)

    # Need to make sure to add the game to the user's guild profile
    # If there is something already in the tracker maybe wait a few seconds and then test again and then replace
    conn,cur = create_connection()
    #gid = get_game_id_from_name(game, cur)
    start_game_tracker(after.id, game, cur)
    close_connection(conn,cur)
    #print(f"{after.display_name} has started to play {game} at {self.start_time}")
    start_time = dt.datetime.now(timezone.utc)
    logging.info(f"{after.display_name} has started to play {game} at around {start_time}")


def verify_linking_criteria(member_id, steam_id):
    conn,cur = create_connection()
    error_code, existing_profile_name = check_for_existing_steam_link(member_id, cur)
    close_connection(conn,cur)

    if existing_profile_name is not None:
        return error_code, existing_profile_name

    return verify_steam_access(steam_id)


def linking_process(user_profile, interaction):
    conn,cur = create_connection()
    logging.info(f"Getting the game library from {user_profile['player']['personaname']}")
    game_library = get_steam_game_library(user_profile['player']['steamid'])
    link_steam_library(game_library, user_profile, interaction.user.id, cur)
    close_connection(conn,cur)


# Bot /commands
#---------------------

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
    #picture = Embedding("http://images.igdb.com/igdb/image/upload/t_thumb/co904o.jpg")

    await interaction.response.send_message(f"Here is {user_name}'s profile", embed = picture)

    #await interaction.followup.send(print_db())

     # if user_name != interaction.user.display_name:
        #     await interaction.response.send_message(f"That is not your profile")
        # else:

@client.tree.command(name = "link_steam_with_steam_id", description = "Links your public steam data to your guild profile.", guild = GUILD_ID)
async def link_steam_id(interaction : discord.Interaction, steam_id : str):
    view = ConfirmDeny(interaction.user.id)
    error_code, user_profile = verify_linking_criteria(interaction.user.id, steam_id)

    match error_code:
        case 0:
            await interaction.response.defer()
            print(f"Found profile : {user_profile['player']['personaname']}")
            sample_profile = SampleDiscordProfile(user_profile)
            await interaction.followup.send(f"Found profile : {user_profile['player']['personaname']}\nWould you like me to link this to your guild profile?", embed=sample_profile,view=view)
        case 1:
            await interaction.response.send_message(f"Hmm, I couldn't find a Steam profile with that ID. Could you double-check that you entered the correct numbers and try again?")
            return
        case 2:
            await interaction.response.send_message(f"I found your Steam profile, but it looks like it's set to private. Could you go into your Steam profile settings and make sure it's set to public? Once you've done that, try again!")
            return
        case 3:
            await interaction.response.send_message(f"Mmm, I just checked and it looks like you already have a Steam profile linked ({user_profile}).\n\nIf you'd like to link a different Steam profile, just use /unlink_steam_data first, then come back and use this command again!")
            return

    await view.wait()
    
    if not view.confirmed:
        return

    interaction = view.message

    if lock.locked():
        await interaction.message.edit(content="Looks like someone is currently syncing right now. Don't worry I'll get to you in a bit as soon as I finish up with them",embed=None,view=None)

    async with lock:
        await interaction.message.edit(content="Syncing now. This might take a minute but I'll let you know when I'm finished",embed=None,view=None)
        await asyncio.to_thread(linking_process, user_profile, interaction)

    # I could also print the steam profile card here
    # we need to implement the syncing 
    # The sync should only update the recently played if the most recent time is older than a day
    
    await interaction.message.edit(content=f"Alright {interaction.user.mention}, I have fully linked your Profile : {user_profile['player']['personaname']} to the guild")


@client.tree.command(name = "unlink_steam_data", description = "removes all data associated with your steam accound", guild=GUILD_ID)
async def unlink_steam(interation : discord.Interaction):
    discord_id = interation.user.id
    guild_id = interation.guild.id
    guild = client.get_guild(guild_id)
    member = guild.get_member(discord_id)

    conn,cur = create_connection()
    steam_name = get_steam_name(discord_id, cur)
    await interation.response.send_message(f"Deleting account tied to {steam_name}")
    remove_user_steam_data(discord_id, cur)
    close_connection(conn,cur)

    og_message = await interation.original_response()
    await og_message.edit(content=f"Account succesfully unlinked for {member.display_name}")

# set announcment command
# 1. look at the channel and guild that the user set the command
# 2. store the channel id in the guilds database
# 3. The guild database could have collumns for |guild_id|game_news|weekly_stats|

# Task loop commands
#----------------------

@tasks.loop(
        time = [
            dt.time(hour=18, minute=18, tzinfo=ZoneInfo("America/Los_Angeles")), 
            dt.time(hour = 21, minute = 0, tzinfo=ZoneInfo("America/Los_Angeles"))
        ]
)
async def get_game_news():
    # going to need to get a list off appids from everyones most recently played games that month
    # need to look at all the users who have that game and have played within a month and maybe @ them in the messages
    conn,cur = create_connection()
    for guild in client.guilds:
        member_list = []
        for member in guild.members:
            if member.id != client.user.id:
                member_list.append(member.id)
        # when we store the cannels for a guild find it first here instead
        channel = guild.get_channel(int(os.getenv("CHANNEL2_ID")))
        news_dictionary = process_member_games_into_news(member_list, cur)

        for game_id, game_data in news_dictionary.items():
            if len(game_data['news_articles']) != 0:
                for article_url in game_data['news_articles']:
                    message = create_response(article_url, game_data['relavent_members'])
                    await channel.send(message)
    close_connection(conn,cur)

client.run(os.getenv("DISCORD_TOKEN"), log_handler=handler, log_level=logging.DEBUG)