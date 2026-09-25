import os
from dotenv import load_dotenv
load_dotenv()
import discord
from discord.ext import commands
from discord import app_commands
import logging
# import datetime as dt
# from datetime import timezone
from SteamPractice import *
from DBpractice import *
import asyncio
from igdbPractice import *
from discord.ext import tasks 
import random
from zoneinfo import ZoneInfo
import calendar

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode ='w')
logging.basicConfig(level= logging.DEBUG, handlers=[handler], format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

lock = asyncio.Lock()
igdbclient = IGDBClient()

LEVEL_THRESHOLDS = [
    0, # lv. 1
    8000, # lv. 2
    17000, # lv. 3

    27000, # lv. 4
    38000, # lv. 5
    50000, # lv. 6

    63000, # lv. 7
    77000, # lv. 8
    92000, # lv. 9

    108000, # lv. 10
    125000, # lv. 11
    143000, # lv. 12

    162000, # lv. 13
    182000, # lv. 14
    203000, # lv. 15

    225000, # lv. 16
    248000, # lv. 17
    272000, # lv. 18

    297000, # lv. 19
    323000, # lv. 20
    350000  # lv. 21
]

RANK_TITLES = {
    1 : "Recruit",
    2 : "Rank 2-er",
    3 : "Rank 3-er",
    4 : "Rank 4-er",
    5 : "Rank 5-er",
    6 : "Rank 6-er",
    7 : "Rank 7-er",
}

banner_color = {
            1 : discord.Color.from_str("#444443"),
            2 : discord.Color.from_str("#CD7801"),
            3 : discord.Color.from_str("#FF0000"),
            4 : discord.Color.from_str("#C9C902"),
            5 : discord.Color.from_str("#00FF08"),
            6 : discord.Color.from_str("#3300FF"),
            7 : discord.Color.from_str("#CE00C0")
        }

activity_key = {
            0 : "⬛",
            1 : "🟨",
            2 : "🟩",
            3 : "🟦",
            4 : "🟪"
        }


class PageChange(discord.ui.View):
    def __init__(self, page1, page2, page3):
        super().__init__(timeout = 60)
        self.message = None
        self.curr_page = 0

        self.server_stats_card = page1
        self.steam_stats_card = page2

        self.library_page = 0
        self.last_page = (len(page3) - 1)
        self.game_library_card = page3

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view = None)

    @discord.ui.button(label="Prev", style = discord.ButtonStyle.blurple)
    async def left(self, interaction : discord.Interaction, button):
        started_on_page = True

        if self.curr_page != 2:
            page = self.curr_page
            page -= 1

            if page < 0:
                self.curr_page = 2
                started_on_page = False
            else:
                self.curr_page = page

        match self.curr_page:
            case 2:
                if not started_on_page:
                    self.library_page = self.last_page
                    await interaction.response.edit_message(embed = self.game_library_card[self.library_page], view = self)
                    return
                if self.library_page == 0:
                    self.curr_page = 1
                    await interaction.response.edit_message(embed= self.steam_stats_card, view = self)
                    return

                self.library_page -= 1
                await interaction.response.edit_message(embed= self.game_library_card[self.library_page], view = self)

            case 1:
                await interaction.response.edit_message(embed= self.steam_stats_card, view = self)

            case 0:
                await interaction.response.edit_message(embed= self.server_stats_card, view = self)


    @discord.ui.button(label = "Next", style = discord.ButtonStyle.blurple)
    async def right(self, interaction : discord.Interaction, button):
        started_on_page = True
        if self.curr_page != 2:
            self.curr_page += 1
            started_on_page = False

        match self.curr_page:
            case 2:
                if not started_on_page:
                    self.library_page = 0
                    await interaction.response.edit_message(embed= self.game_library_card[self.library_page], view = self)
                    return

                if self.library_page == self.last_page:
                    self.library_page = 0
                    #change to 0
                    self.curr_page = 0
                    await interaction.response.edit_message(embed= self.server_stats_card, view = self)
                    return
            
                self.library_page += 1
                await interaction.response.edit_message(embed= self.game_library_card[self.library_page], view = self)

            case 1:
                await interaction.response.edit_message(embed= self.steam_stats_card, view = self)


class ConfirmDeny(discord.ui.View):

    def __init__(self, discord_id, interaction : discord.Interaction):
        super().__init__(timeout=60)
        self.discord_user = discord_id
        self.first_interaction = interaction
        self.confirmed = False
        self.message = None
        self.timed_out = False

    async def on_timeout(self):
        message = await self.first_interaction.original_response()
        await message.edit(content=f"{self.first_interaction.user.mention} I do have other things to attend to, you know. Honestly, must you make my job more difficult than it needs to be? Try again when you're ready, but next time, do try not to keep me waiting.",embed=None,view=None)
        self.stop()

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


class GuildCard(discord.Embed):
    def __init__(self, user, banner_color = None):
        super().__init__()
        self.profile_picture = user.display_avatar.url
        self.user_name = user.display_name
        self.banner_color = banner_color

    # Profile Data = [total_messages_sent, total_stream_time, total_call_time, guild_level, xp, mvps, second_places, third_places, server_playtime]
    def server_stats_card(self, activity_data, recent_game_name, recent_game_image_url, profile_data, member_id, guild_id):
        
        self.title = f"{self.user_name}"
        self.set_thumbnail(url = self.profile_picture)

        level = get_user_level(member_id, guild_id)
        rank = get_user_rank_title(level)
        self.banner_color = banner_color[level]
        self.color = self.banner_color
        
        if level < 21:
            self.description = (
                f"### Level {level} - {RANK_TITLES[rank]} \n"
                f"### XP : {int((profile_data[4] - LEVEL_THRESHOLDS[level - 1]) / 100)} / {int(LEVEL_THRESHOLDS[level] / 100)}\n\n"
            )
        else:
            self.description = (
                f"### Level {level} - {RANK_TITLES[rank]} \n"
                f"### XP : MAX\n\n"
            )

        self.add_field(name = "📅 - Weekly Activity", value= "-" * 52, inline=False)
        self.add_field(
                    name="Activity Key",
                    value=(
                        "```text\n"
                        "⬛ <1h    "
                        "🟨 1-2h   "
                        "🟩 2-3h   \n"
                        "🟦 3-5h   "
                        "🟪 5h+  "
                        "(2 week avg.)"
                        "```\n"
                    ),
                    inline=False
                )
        #print(activity_data)
        for i in range(7):
            day = calendar.day_abbr[i]
            activity_color = 0
            if i in activity_data:
                week2_data = activity_data[i]['week2']
                week1_data = activity_data[i]['week1']
                activity_color = (week2_data + week1_data)/2

                if activity_color > 5:
                    activity_color = 4
                elif activity_color > 3 and activity_color <= 5:
                    activity_color = 3
                elif activity_color > 2 and activity_color <= 3:
                    activity_color = 2
                elif activity_color > 1 and activity_color <= 2:
                    activity_color = 1
                else:
                    activity_color = 0

            self.add_field(name=f"{day}:", value= activity_key[activity_color])
                
        stream_time = format_timedelta(dt.timedelta(seconds = profile_data[1]))
        call_time = format_timedelta(dt.timedelta(seconds = profile_data[2]))
        game_time = format_timedelta(dt.timedelta(seconds = profile_data[8]))
        messages = profile_data[0]
        # self.add_field(name = "🎥 Stream Time", value = stream_time, inline=True)
        # self.add_field(name = "🔊 Call Time", value = call_time, inline=True)
        # self.add_field(name = "🔊 Playtime", value = call_time, inline=True)
        # self.add_field(name = "📨 Messages Sent", value = f"{messages}", inline=True)
        # self.add_field(name="Most Recent Game", value="", inline=False)
        self.add_field(name=f"📊 - General Stats", value= "-" * 52, inline=False)
        self.add_field(
            name=" ",
            value=(
                "```text\n"
                f"{"🎥 Stream :" :<15} {stream_time :>8}\n\n" 
                f"{"🔊 Voice :" :<15} {call_time :>8}\n\n" 
                f"{"🕹️ Gaming :" :<15} {game_time :>8}\n\n"
                f"{"📨 Messages :" :<15} {messages :>6}\n\n"
                f"         MVPS\n"
                "--------------------------\n"
                f"🏆 : {profile_data[5]} | 🥈: {profile_data[6]} | 🥉: {profile_data[7]}   {"|" :<10}\n"
                "```\n"
            )
        )
        
        if recent_game_name is None:
            recent_game_name = "N/A"
        if recent_game_image_url is not None:
            self.set_image(url= recent_game_image_url)
        self.add_field(name=f"Most Recent Game", value= f"({recent_game_name})", inline=False)
        # self.add_field(name="Games",value="🎮 Terraria\n🎮 Baldur's Gate 3\n🎮 Castlevania",inline=False)
        # self.add_field(name="Recently Played Game", value="Terraria")

    def steam_stats_card(self, steam_data):
        # [account_name, creation_time, steam_games_count, account_cost, total_steam_time, last_sync, profile_pic, auto_sync_steam, most_played_game_dict]
        self.title = "Steam Stats"
        self.color = self.banner_color

        self.add_field(name=f"General Steam Stats", value= "-" * 52, inline=False)
        if steam_data is None:
            self.description = (
                f"### Steam Profile"
            )
            self.add_field(name=f"Steam Profile Not Linked", value= "If you would like to link steam please do so", inline=False)
            return

        self.set_thumbnail(url = steam_data[6])
        self.description = (
            f"### {steam_data[0]}"
        )
        

        today = dt.datetime.now(timezone.utc)
        age = relativedelta(today, steam_data[1])
        creation_time = format_age(age)
        steam_games_count = steam_data[2]

        # going to have to format this
        account_cost = steam_data[3]

        total_steam_time = format_timedelta(dt.timedelta(seconds = steam_data[4]))
        last_sync = steam_data[5].date()
        auto_sync_value = steam_data[7]
        if auto_sync_value is not None:
            if auto_sync_value == True:
                auto_sync_value = "ON"
            else:
                auto_sync_value = "OFF"

        game_name = ""
        if len(steam_data[8]) == 0:
            game_name = "N/A"
            playtime = "N/A"
        else:
            most_played_game = list(steam_data[8].items())
            game_name, game_data = most_played_game[0]
            playtime = format_timedelta(dt.timedelta(seconds = game_data['playtime']))
        
            self.set_image(url=game_data['img'])

        self.add_field(
            name="",
            value=(
                "```text\n"
                f"🕰️ Account Age ---  {creation_time}\n\n" 
                f"---------------------------------\n"
                f"📚 Games in Library   ---  {steam_games_count}\n\n"
                f"---------------------------------\n"
                f"💵 Aprox. Libray value\n        ${account_cost}\n\n" 
                f"---------------------------------\n"
                f"👾 Total Game Time   ---  {total_steam_time}\n\n"
                "```\n"
            )
        )

        self.add_field(name=f"Most Played Game", value= f"({game_name} - {playtime})", inline=False)

        self.set_footer(text= f"\n\nLast synced {last_sync}            Auto-Sync: {auto_sync_value}")
    

    def game_library_card(self, game_library, start_index):

        # if we don't have a game library then don't make this

        self.title = f"{self.user_name}"
        self.color = self.banner_color
        self.set_thumbnail(url = self.profile_picture)

        if game_library is None or len(game_library) == 0:
            self.add_field(
                name="Wow much empty...", 
                value="", 
                inline=False
            )
            return

        end_index = start_index + 25
        if end_index > len(game_library):
            end_index = len(game_library)

        game_list = list(game_library.items())
        # print(game_list)
        game_library_page = game_list[start_index: end_index]
        for game_name, game_data in game_library_page:

            server_time = format_timedelta(dt.timedelta(seconds = game_data['server_time']))

            if game_data['steam_time'] is None:
                steam_time = 0
            else:
                steam_time = format_timedelta(dt.timedelta(seconds = game_data['steam_time']))

            self.add_field(name=f"🎮 {game_name}", value=f"[Server Time: {server_time}]\n [Steam Time : {steam_time}]", inline=False)

        self.set_footer(text= f"\n\nGames ({start_index} - {end_index}) / {len(game_library)}")


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

class WeekBreakdown(discord.Embed):
    def __init__(self, server_data, guild):
        super().__init__()

        self.title = "Weekly Breakdown"
        self.description = " "

        stream_data = sorted(
            server_data['stream'].items(),
            key = lambda x : x[1],
            reverse = True
        )
        self.add_field(
            name=(
                "\n"
                "Time Streamed\n"
                "-------------------------------------\n"
            ), 
            value = create_string_from_list(stream_data, guild),
            inline=False
        )

        call_data = sorted(
            server_data['call'].items(),
            key = lambda x : x[1],
            reverse = True
        )

        self.add_field(
            name=(
                "\n"
                "Time In Call\n"
                "-------------------------------------\n"
            ), 
            value = create_string_from_list(call_data, guild),
            inline=False
        )

        self.add_field(
            name=(
                "\n"
                "Games Played This Week\n"
                "-------------------------------------\n"
            ), 
            value = "",
            inline=False
        )
        #game_list = list(server_data['games'].items())
        game_list = sorted(
            server_data['games'].items(),
            key = lambda x : x[1]['total_time'],
            reverse = True
        )

        if len(game_list) == 0:
            return
        
        total_games = len(game_list)
        if total_games > 17:
            game_list = game_list[ : 18]

        for game_name, game_data in game_list:
            if game_name == game_list[0][0]:
                self.add_field(
                    name=f"🌟 {game_name}", 
                    value= (
                        create_string(game_data['players'], game_data['total_time'], guild)
                    ),
                    inline= False
                )
            else:
                self.add_field(
                    name=f"🎲 {game_name}", 
                    value= (
                        create_string(game_data['players'], game_data['total_time'], guild)
                    ),
                    inline= False
                )

        if server_data['top_game']['name'] is not None:
            name = server_data['top_game']['name']
            time = server_data['top_game']['time']
            time = format_timedelta(dt.timedelta(seconds = time))
            img = server_data['top_game']['img']
            if img:
                self.set_image(url=img)
            self.add_field(name="Most Popular Game", value=f"{name} - {time}", inline=False)
        else:
            self.add_field(name="Most Popular Game", value=f"N/A - N/A", inline=False)


def create_string_from_list(item_list, guild):
    if len(item_list) == 0:
        return " "
    string = (
        "```text\n"
        f"{'Name' : <20} | {'Time' : >6}\n"
        "---------------------------------\n"
    )

    total_time = 0
    for user, data in item_list:
        discord_name = guild.get_member(user).display_name
        time_played = data
        total_time += time_played
        
        time_played = format_timedelta(dt.timedelta(seconds = time_played))
        string += f"{discord_name:<20} | {time_played:>6}\n"
        
    total_time = format_timedelta(dt.timedelta(seconds = total_time))
    string += (
        f"\n{'total:' : <22} {total_time : >6}\n"
        "```"
    )

    return string

        
def create_string(single_game_data, t_time, guild : discord.Guild):
    if len(single_game_data) == 0:
        return " "
    string = (
        "```text\n"
        f"{'Name' : <20} | {'Time' : >6}\n"
        "---------------------------------\n"
    )

    #total_time = 0
    sorted_game_data = sorted(
        single_game_data.items(),
        key = lambda x : x[1],
        reverse = True
    )

    for user, ply_time in sorted_game_data:
        discord_name = guild.get_member(user).display_name
        time_played = ply_time
        
        time_played = format_timedelta(dt.timedelta(seconds = time_played))
        string += f"{discord_name:<20} | {time_played:>6}\n"
        
    total_time = format_timedelta(dt.timedelta(seconds = t_time))
    string += (
        f"\n{'total:' : <22} {total_time : >6}\n"
        "```"
    )

    return string


class SampleDiscordProfile(discord.Embed):
    def __init__(self, profile_details):
        super().__init__()
        self.title = f"{profile_details['player']['personaname']}"
        #self.description = "Check the link if you're unsure"
        self.url = profile_details['player']['profileurl']
        self.set_image(url=profile_details['player']['avatarfull'])

processing_user = set()

class Client(commands.Bot):
    #e = Embedding("https://cdn.discordapp.com/avatars/385277889404207105/fb8b1cae3be44ba623caee0610343864.png?size=1024")
    async def on_ready(self):
        print(f"Logged on as {self.user}")
        
        initialize_db()
        self.verify_guilds_and_members()
        for guild in self.guilds:
            await verify_MVP_role(guild)

        try:
            # guild = discord.Object(id = os.getenv("GUILD_ID"))
            # synced = await self.tree.sync(guild=guild)
            # print(f"Synced {len(synced)} commands to guild {guild.id}")
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands to all guilds")
            
        except Exception as e:
            print(f"Error syncing commands: {e}")

        if not get_game_news.is_running():
            get_game_news.start()
        if not weekly_game_library_enrichment.is_running():
            weekly_game_library_enrichment.start()
        if not end_of_day_processes.is_running():
            end_of_day_processes.start()


    async def on_message(self, message : discord.Message):
        # when a person says a message they gain xp
        #print(f"Message from {message.author}: {message.content}")
        
        if message.author == self.user:
            return
        if message.content.startswith("hello"):
            await message.channel.send(f"Hi there {message.author.display_name}")
            #await message.channel.send(f"Hi there {message.author.display_name}", embed = self.e)
            #await message.channel.send(f"Hi there {message.author.display_name}", embeds = [self.e,self.e,self.e,self.e])
            #await message.channel.send(f"Hi there {message.author.display_avatar.url}")
            # print(message.author.guild.id)
        conn,cur = create_connection()
        update_user_message_count(message.author.id, message.guild.id, cur)
        close_connection(conn,cur)

        if message.content.startswith("m"):
            await mvp_process(message.guild)
        
        # conn,cur = create_connection()
        # restart_tracked_activities(cur)
        # close_connection(conn,cur)


    async def on_reaction_add(self, reaction, user):
        return
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
                # get a dictionary of guild_id : user_level
                member_id = before.id
                if member_id in processing_user or member_id == self.user.id:
                    return
                
                try:
                    processing_user.add(member_id)
                    snapshot, guild_table = get_level_snapshot(member_id, self.guilds)
                    #print(f"IN : {snapshot}")

                    await asyncio.to_thread(end_game_tracking_process, before.id, game, "PLAYING", before.guild.id)

                    new_snapshot, _ = get_level_snapshot(member_id, self.guilds)
                    #print(f"OUT : {new_snapshot}")
                    for guild_id in new_snapshot:
                        if new_snapshot[guild_id] != snapshot[guild_id]:
                            print(f"User went from level {snapshot[guild_id]} to level {new_snapshot[guild_id]} in server {guild_id}")
                            #await level_up_message(snapshot[guild_id], new_snapshot[guild_id], member_id, guild_table[guild_id])
                            asyncio.create_task(level_up_message(snapshot[guild_id], new_snapshot[guild_id], member_id, guild_table[guild_id]))
                    # get a new dictionary of guild_id : user_level if the levels are different from the old one send the level up message
                    end_time = dt.datetime.now(timezone.utc)
                    print(f"{before.display_name} has stopped playing {game} at {end_time}")
                finally:
                    processing_user.discard(member_id)
                #print(f"played for {(end_time - start_time).total_seconds()} seconds")

        # At 12 or whenever make sure to calculate the time for all currently active games then add them to the players/guild. Then change the time to that current time. Maybe doesn't matter for weekly
        if after.activity != None:
            if after.activity.type == discord.ActivityType.playing:
                game = after.activity.name
                start_time = dt.datetime.now(timezone.utc)
                await asyncio.to_thread(start_game_tracking_process, game, after, "PLAYING", after.guild.id)
                print(f"{after.display_name} has started playing {game} at {start_time}")

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
        #d.channels c : discord.channel.TextChannel
        
        verify_members_and_channels_in_database(total_guilds, bot_profile_id, cur)
        close_connection(conn,cur)

        print("All guilds and members verified")

    async def on_member_join(self, member):
        await asyncio.to_thread(self.verify_guilds_and_members)

    async def on_voice_state_update(self, member:discord.Member, before : discord.member.VoiceState, after : discord.member.VoiceState):
        # This will handle streaming time and voice enter time
        # Ending a call will also need to end any streams
        # We are looking for going from channel to no channel
        guild_id = member.guild.id
        a_state1 = "IN CALL"
        a_state2 = "STREAMING"

        # Call was joined
        if before.channel == None and after.channel != None:
            conn,cur = create_connection()
            start_activity_tracker(member.id, None, a_state1, guild_id, cur)
            close_connection(conn,cur)

        # Call was ended
        if before.channel != None and after.channel == None:
            conn,cur = create_connection()
            end_tracker(member.id, None, a_state1, guild_id, cur)
            close_connection(conn,cur)

        # Stream was started
        if before.self_stream == False and after.self_stream == True:
            conn,cur = create_connection()
            start_activity_tracker(member.id, None, a_state2, guild_id, cur)
            close_connection(conn,cur)

        # Stream ended
        if before.self_stream == True and after.self_stream == False:
            conn,cur = create_connection()
            end_tracker(member.id, None, a_state2, guild_id, cur)
            close_connection(conn,cur)

        #print(member.display_name)
        #print(type(before))
        #print(before)
        #print(type(after))
        #print(after)
    async def on_guild_join(self, guild : discord.Guild):
        print(f"Just joined {guild.name} id : {guild.id}")

        await asyncio.to_thread(self.verify_guilds_and_members)
        await verify_MVP_role(guild)
        
        
aaaa = {
    "Alex": {
        "playtime": 4820,
        "call_time": 1630,
        "stream_time": 740,
        "messages": 18,
        "mvp_mult": 100,
        "score": 0
    },
    "Jordan": {
        "playtime": 3150,
        "call_time": 920,
        "stream_time": 450,
        "messages": 25,
        "mvp_mult": 100,
        "score": 0
    },
    "Sam": {
        "playtime": 2100,
        "call_time": 1440,
        "stream_time": 360,
        "messages": 12,
        "mvp_mult": 110,
        "score": 0
    },
    "Taylor": {
        "playtime": 1650,
        "call_time": 720,
        "stream_time": 120,
        "messages": 20,
        "mvp_mult": 100,
        "score": 0
    },
    "Morgan": {
        "playtime": 980,
        "call_time": 1800,
        "stream_time": 540,
        "messages": 25,
        "mvp_mult": 90,
        "score": 0
    },
    "Chris": {
        "playtime": 4200,
        "call_time": 300,
        "stream_time": 0,
        "messages": 8,
        "mvp_mult": 105,
        "score": 0
    },
    "Jamie": {
        "playtime": 1350,
        "call_time": 600,
        "stream_time": 900,
        "messages": 16,
        "mvp_mult": 100,
        "score": 0
    },
    "Riley": {
        "playtime": 2700,
        "call_time": 480,
        "stream_time": 180,
        "messages": 25,
        "mvp_mult": 95,
        "score": 0
    },
    "Casey": {
        "playtime": 750,
        "call_time": 2100,
        "stream_time": 300,
        "messages": 14,
        "mvp_mult": 100,
        "score": 0
    },
    "Caiatl, Empress of Cabussy": {
        "playtime": 3600,
        "call_time": 1080,
        "stream_time": 660,
        "messages": 22,
        "mvp_mult": 115,
        "score": 0
    }
}

# bbbb = {
#     "Alex": "(37.49 + 9.06 + 0.82 + 18.00) * 1.00 = 65.37",
#     "Jordan": "(24.50 + 5.11 + 0.50 + 25.00) * 1.00 = 55.11",
#     "Sam": "(16.33 + 8.00 + 0.40 + 12.00) * 1.10 = 40.40",
#     "Taylor": "(12.83 + 4.00 + 0.13 + 20.00) * 1.00 = 36.96",
#     "Morgan": "(7.62 + 10.00 + 0.60 + 25.00) * 0.90 = 38.90",
#     "Chris": "(32.67 + 1.67 + 0.00 + 8.00) * 1.05 = 44.45",
#     "Jamie": "(10.50 + 3.33 + 1.00 + 16.00) * 1.00 = 30.83",
#     "Riley": "(21.00 + 2.67 + 0.20 + 25.00) * 0.95 = 46.92",
#     "Casey": "(5.83 + 11.67 + 0.33 + 14.00) * 1.00 = 31.83",
#     "Caiatl, Empress of Cabussy": "(28.00 + 6.00 + 0.73 + 22.00) * 1.15 = 65.13"
# }

# Bot command helpers
#-----------------
def get_level_snapshot(member_id, guilds):
    users_guilds_and_levels = {}
    guild_table = {}
    for guild in guilds:
        for member in guild.members:
            if member.id == member_id:
                users_guilds_and_levels[guild.id] = get_user_level(member_id, guild.id)
                guild_table[guild.id] = guild
    return users_guilds_and_levels, guild_table

async def create_mvp_role(guild : discord.Guild, cur : db.extensions.cursor, conn : db.extensions.connection):
    role = await guild.create_role(
        name = "🏆 MVP 🏆",
        color= discord.Color.gold(),
        hoist= True,
        mentionable = False
    )
    update_mvp_role_id(role.id, guild.id, cur)
    conn.commit()
    return role.id

async def verify_MVP_role(guild : discord.Guild):
    conn,cur = create_connection()

    role_id = get_mvp_id(guild.id, cur)
    if role_id == "error":
        close_connection(conn, cur)
        return
    if role_id is None:
        logger.warning(f"Could not find an assigned MVP role. Creating MVP role...")
        role_id = await create_mvp_role(guild, cur, conn)

    role = guild.get_role(role_id)
    if role is None:
        logger.warning(f"MVP role might have been deleted. Creating MVP role...")
        role_id = await create_mvp_role(guild, cur, conn)
        role = guild.get_role(role_id)

    close_connection(conn,cur)

    return role


def calculate_mvp_score(mvp_data):
    user_score_breakdown = {}

    for user in mvp_data:
        playtime_score = (mvp_data[user]['playtime'] / 900) * 2
        call_time_score = (mvp_data[user]['call_time'] / 900) * 4
        stream_time_score = (mvp_data[user]['stream_time'] / 900) * 6
        messages_score = min(mvp_data[user]['messages'], 20) 
        score_mult = mvp_data[user]['mvp_mult'] / 100

        mvp_data[user]['score'] = (playtime_score + call_time_score + stream_time_score + messages_score) * score_mult

        user_score_breakdown[user] = f"({playtime_score: .2f} +{call_time_score: .2f} +{stream_time_score: .2f} + {messages_score}) *{score_mult: .2f} = {mvp_data[user]['score']: .2f}"

    print(mvp_data)
    print('\n')
    print(user_score_breakdown)

    return user_score_breakdown

def create_mvp_breakdown_message(leaderboard, user_score_breakdown, guild : discord.Guild):
    # add more to this later
    string = (
            "```text\n"
            f"Point calculation:\n(playtime + call time + stream time + messages) * score_mult\n\n"
            "🏆 WEEKLY MVP\n"
            "────────────────────────────────────────\n\n"
        )

    # for i, (user, _) in enumerate(leaderboard):
    #     match i:
    #         case 0:
    #             string += f"🥇 {guild.get_member(user).display_name : <20} {user_score_breakdown[user]}\n"
    #         case 1:
    #             string += f"🥈 {guild.get_member(user).display_name : <20} {user_score_breakdown[user]}\n"
    #         case 2:
    #             string += f"🥉 {guild.get_member(user).display_name : <20} {user_score_breakdown[user]}\n"
    #         case _:
    #             string += f"{i + 1}. {guild.get_member(user).display_name : <20} {user_score_breakdown[user]}\n"

    for i, (user, _) in enumerate(leaderboard):
        match i:
            case 0:
                string += f"{"🥇":<3} {guild.get_member(user).display_name : <20}\n{user_score_breakdown[user]}\n\n"
            case 1:
                string += f"{"🥈":<3} {guild.get_member(user).display_name : <20}\n{user_score_breakdown[user]}\n\n"
            case 2:
                string += f"{"🥉":<3} {guild.get_member(user).display_name : <20}\n{user_score_breakdown[user]}\n\n"
            case _:
                string += f"{i + 1}.   {guild.get_member(user).display_name : <20}\n{user_score_breakdown[user]}\n\n"

    string += (
        f"Congrats {guild.get_member(leaderboard[0][0]).display_name} on being this weeks mvp"
    )

    string += "```"

    return string

def get_prev_mvp(guild : discord.Guild, role : discord.Role):
    for member in guild.members:
       if role in member.roles:
           return member

async def mvp_process(guild : discord.Guild):
    #channel = guild.get_channel(int(os.getenv("CHANNEL2_ID")))
    conn, cur = create_connection()

    try:
        channel = get_channel(0, guild, cur)
        if channel is None:
            return

        #server_data, mvp_data = get_week_long_server_data(guild, cur)
        server_data, mvp_data = await asyncio.to_thread(get_week_long_server_data, guild, cur)
        if server_data is None and mvp_data is None:
            print("No data found")
            return

        #user_score_breakdown = bbbb
        # mvp_data = aaaa
        if server_data is None:
            return
        if len(server_data) == 0:
            return
        #BOOKMARK we can get the users total messages from here
        user_score_breakdown = calculate_mvp_score(mvp_data)
        
        #contestants = list(user_score_breakdown.items())
        contestants = sorted(
            mvp_data.items(),
            key = lambda x : x[1]['score'],
            reverse = True
        )

        placements = len(contestants)
        if placements >= 4:
            placements = 3

        
        mvp_role = await verify_MVP_role(guild)
        last_mvp = get_prev_mvp(guild, mvp_role)
        if last_mvp is not None:
            await last_mvp.remove_roles(mvp_role)

        mvp_winner = guild.get_member(contestants[0][0])
        await mvp_winner.add_roles(mvp_role)

        for place in range(placements): 
            update_user_mvp_data(contestants[place][0], guild.id, place, cur)
    finally:
        close_connection(conn, cur)

    
    # server, steam, library = create_guild_cards(mvp_winner, guild.id)
    server, steam, library = await asyncio.to_thread(create_guild_cards, mvp_winner, guild.id)
    view = PageChange(server, steam, library)

    weekly_card = WeekBreakdown(server_data, guild)

    leaderboard = sorted(
        mvp_data.items(),
        key = lambda x:x[1]['score'],
        reverse=True
    )
    
    mvp_breakdown = await asyncio.to_thread(create_mvp_breakdown_message, leaderboard, user_score_breakdown, guild)
    s = f"Hey {mvp_winner.mention}! You are this weeks MVP, Great Job!\n" + mvp_breakdown

    msg = await channel.send(content = s, embed = server, view = view)
    view.message = msg

    await channel.send("Here's the weekly breakdown brought to you by yours truly", embed=weekly_card)
    

def create_guild_cards(user, guild_id):
    server_stats_card = create_server_profile_card(user, guild_id)
    b_color = server_stats_card.banner_color
    library_stats_card = create_game_library_card(user, b_color)
    steam_card = create_steam_card(user, b_color)

    return server_stats_card, steam_card, library_stats_card


def format_timedelta(td):
    total_minutes = int(td.total_seconds() // 60)

    days, remainder = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")

    return " ".join(parts) if parts else "0m"

def format_age(age):
    parts = []

    if age.years:
        parts.append(f"{age.years}y")

    if age.months:
        parts.append(f"{age.months}mo")

    if age.days:
        parts.append(f"{age.days}d")

    if age.hours:
        parts.append(f"{age.hours}h")

    if age.minutes:
        parts.append(f"{age.minutes}m")

    return " ".join(parts) if parts else "0m"

# def init_guild_card(user, guild_id):
#     game_pic = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/2893570/035bf8ec4e6bd65ebea782063b1157e526533740/header.jpg?t=1773044632"
#     conn,cur = create_connection()
#     game_name, game_pic = get_recently_played_game_img(user.id, cur)
#     pdata = get_user_server_stats(user.id, guild_id, cur)
#     card = GuildCard(user)
#     card.server_stats_card(game_name, game_pic, pdata)
#     library = get_user_total_game_library(user.id, cur)


def create_server_profile_card(user, guild_id):
    #game_pic = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/2893570/035bf8ec4e6bd65ebea782063b1157e526533740/header.jpg?t=1773044632"
    conn,cur = create_connection()
    game_name, game_pic = get_recently_played_game_img(user.id, cur)
    pdata = get_user_server_stats(user.id, guild_id, cur)
    activity_data = get_user_activity(user.id, cur)
    card = GuildCard(user)
    card.server_stats_card(activity_data, game_name, game_pic, pdata, user.id, guild_id)
    close_connection(conn,cur)

    return card


def create_game_library_card(user, b_color):
    library_pages = []

    conn,cur = create_connection()

    library = get_user_total_game_library(user.id, cur)
    start_index = 0
    if library is None:
        card = GuildCard(user, b_color)
        card.game_library_card(library,start_index)
        library_pages.append(card)
        return library_pages
    
    max_index = len(library)
    # Embeds only allow a max of 25 items so this allows us to display games in batches of 25 per page
    while(start_index < max_index):
        card = GuildCard(user, b_color)
        card.game_library_card(library,start_index)
        library_pages.append(card)
        start_index += 25

    close_connection(conn,cur)

    return library_pages


def create_steam_card(user, b_color):
    conn,cur = create_connection()
    steam_stats = get_user_steam_stats(user.id, cur)
    close_connection(conn,cur)
    steam_card = GuildCard(user, b_color)
    steam_card.steam_stats_card(steam_stats)

    return steam_card


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
        

def end_game_tracking_process(member_id, game_name, activity_type, guild_id):
    conn ,cur = create_connection()
    end_tracker(member_id, game_name, activity_type, guild_id, cur)
    close_connection(conn,cur)


def start_game_tracking_process(game, after : discord.Member, activity_type, guild_id):
    conn,cur = create_connection()
    # Immediatly update the game and user profiles with the new data if data not found
    
    if activity_type == "PLAYING":

        if not game_name_in_database(game, cur):
            add_game_to_database(game, igdbclient, cur)
            add_game_to_user_profile(game, after.id, cur)
            conn.commit()

        game_filter = get_filterd_games(cur)
        gid = get_game_id_from_name(game, cur)
        if gid in game_filter:
            logger.info(f"Game : {game} was found in the filter and was not added to member {after.id} profile")
            return
        
        if not user_owns_game(after.id, game, cur):
            add_game_to_user_profile(game, after.id, cur)
            conn.commit()
        start_time = dt.datetime.now(timezone.utc)
        logging.info(f"{after.display_name} has started to play {game} at around {start_time}")

    #gid = get_game_id_from_name(game, cur)
    start_activity_tracker(after.id, game, activity_type, guild_id, cur)
    close_connection(conn,cur)
    #print(f"{after.display_name} has started to play {game} at {self.start_time}")
    

def verify_linking_criteria(member_id, steam_id):
    conn,cur = create_connection()
    error_code, existing_profile_name = check_for_existing_steam_link(member_id, cur)
    close_connection(conn,cur)

    if existing_profile_name is not None:
        return error_code, existing_profile_name

    return verify_steam_access(steam_id)


def syncing_process(member_id):
    conn,cur = create_connection()
    try:
        steam_id = get_user_steam_id(member_id, cur)
        if steam_id is None:
            logger.warning(f"Aborting syncing process for member : {member_id} because no steam id was found")
            return
        error_code, user_profile = verify_steam_access(steam_id)
        # 2 is private so we turn off the auto sync and return
        if error_code == 2:
            # swap auto sync to false
            return
        if error_code == 0:
            game_library = get_steam_game_library(steam_id)
            link_steam_library(game_library, user_profile, member_id, cur, conn, True)
    finally:
        close_connection(conn,cur)


def linking_process(user_profile, interaction):
    conn,cur = create_connection()
    logging.info(f"Getting the game library from {user_profile['player']['personaname']}")
    game_library = get_steam_game_library(user_profile['player']['steamid'])
    link_steam_library(game_library, user_profile, interaction.user.id, cur, conn)
    close_connection(conn,cur)

def get_user_rank_title(user_level):
    rank = (user_level - 1) // 3 + 1

    if rank >= 7:
        return 7
    
    return rank

def get_user_level(member_id, guild_id):
    xp = get_user_xp(member_id, guild_id)

    level = 0
    for milestone in LEVEL_THRESHOLDS:
        if xp >= milestone:
            level += 1
        else:
            break

    return level


async def level_up_message(prev_level, new_level, user_id, guild : discord.Guild):
    conn,cur = create_connection()
    level_up_channel = get_channel(2, guild, cur)
    close_connection(conn,cur)
    if level_up_channel is None:
        logger.error(f"Could not send a message in a channel that doesn't exist")
        return

    user = guild.get_member(user_id)
    server, steam, library = create_guild_cards(user, guild.id)
    view = PageChange(server, steam, library)

    user_name = user.display_name

    await asyncio.to_thread(update_user_level, new_level, guild.id, user_id)

    await level_up_channel.send(
        content= f"Congrats {user.mention} leveled up from {prev_level} {RANK_TITLES[prev_level]}-> {new_level} {RANK_TITLES[new_level]}",
        embed= server, 
        view = view
    )



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

@client.tree.command(name = "game_filter", description = "**Dev command only** Allows games to be filterd in user_games", guild= GUILD_ID)
async def filter_game(interaction : discord.Interaction, game_name : str):

    if interaction.user.id != int(os.getenv("DEV_ID")):
        await interaction.response.send_message("Sorry, only my Boss has access to that command. If you need a game removed from your profile just let him know", ephemeral= True)
        return
    
    await interaction.response.defer(ephemeral=True)

    response = await asyncio.to_thread(update_game_filter, game_name)    

    await interaction.followup.send(content= response, ephemeral=True)


@client.tree.command(name = "toggle_steam_sync", description= "Turns on/off whether your steam account will be updated at the end of the day", guild= GUILD_ID)
async def toggle_sync(interaction: discord.Interaction):
    # BOOKMARK display whether linking is active for user also need to untoggle sync when autosync fails
    await interaction.response.defer(ephemeral=True)
    member_id = interaction.user.id
    sync_value = auto_sync_toggle_set(member_id, None)
    await interaction.followup.send(content= f"Your Steam profile now has auto sync set to -> {sync_value}", ephemeral=True)


@client.tree.command(name = "guildcard", description="print your guild card")
async def guildcard(interaction: discord.Interaction, user: discord.Member):
    if user.id == client.user.id:
        await interaction.response.send_message(f"I am part of the guild but I'm just the record keeper.")
        return
    await interaction.response.defer()

    user_name = user.display_name

    server_stats_card, steam_card, library_stats_card = await asyncio.to_thread(create_guild_cards, user, interaction.guild.id)
    view = PageChange(server_stats_card, steam_card, library_stats_card)

    await interaction.followup.send(f"Here is {user_name}'s profile", embed = server_stats_card, view = view)
    view.message = await interaction.original_response()


syncing_users = set()

@client.tree.command(name = "link_steam", description = "Links your public steam data to your guild profile.")
async def link_steam_id(interaction : discord.Interaction, steam_id : str):
    if interaction.user.id in syncing_users:
        await interaction.response.send_message("Woah there buddy. It seems like you are already syncing a profile right now. Realx I'll be done soon. I'd like to see you try to sort through dozens of games in seconds hmf")
        return
    discord_id = interaction.user.id
    syncing_users.add(discord_id)

    await interaction.response.defer()

    view = ConfirmDeny(interaction.user.id, interaction)
    error_code, user_profile = await asyncio.to_thread(verify_linking_criteria, discord_id, steam_id)

    try:
        match error_code:
            case 0:
                print(f"Found profile : {user_profile['player']['personaname']}")
                sample_profile = SampleDiscordProfile(user_profile)
                await interaction.followup.send(f"Found profile : {user_profile['player']['personaname']}\nWould you like me to link this to your guild profile?", embed=sample_profile,view=view)
            case 1:
                await interaction.followup.send(f"Hmm, I couldn't find a Steam profile with that ID. Could you double-check that you entered the correct numbers and try again?")
                return
            case 2:
                await interaction.followup.send(f"I found your Steam profile, but it looks like it's set to private. Could you go into your Steam profile settings and make sure it's set to public? Once you've done that, try again!")
                return
            case 3:
                await interaction.followup.send(f"Mmm, I just checked and it looks like you already have a Steam profile linked ({user_profile}).\n\nIf you'd like to link a different Steam profile, just use /unlink_steam_data first, then come back and use this command again!")
                return

        await view.wait()

        if view.timed_out == True:
            return
        if not view.confirmed:
            return

        interaction = view.message

        if lock.locked():
            await interaction.message.edit(content="Looks like someone is currently syncing right now. Don't worry! I'll get to you in a bit as soon as I finish up with them",embed=None,view=None)

        async with lock:
            # maybe add a data base look up here to see if the user has a steam profile already
            await interaction.message.edit(content="Syncing now. This might take a minute but I'll let you know when I'm finished",embed=None,view=None)
            await asyncio.to_thread(linking_process, user_profile, interaction)

        # I could also print the steam profile card here
        # we need to implement the syncing 
        # The sync should only update the recently played if the most recent time is older than a day
        await interaction.message.edit(content=f"Alright {interaction.user.mention}, I have fully linked your Profile : {user_profile['player']['personaname']} to the guild")
    finally:
        syncing_users.discard(discord_id)


@client.tree.command(name = "unlink_steam", description = "removes all data associated with your steam account")
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

channel_name = {
    0 : "MVP",
    1 : "News",
    2 : "Level Up"
}
@client.tree.command(name = "set_channel_type", description = "Enter a number (0 - 2). [0 : MVP Channel, 1 : Game News, 2 : Level Up Channel]")
async def set_channel_type(interaction : discord.Interaction, channel_type : int):
    
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            content = """Hmm, it looks like you don't have the permissions to manage channels.Please contact the server owner or a mod who has this permisson""",
            ephemeral=True
        )
        return
    
    if not isinstance(channel_type, int) or channel_type > 2 or channel_type < 0:
        await interaction.response.send_message(
            content= 
            """Please select a number 0 - 2 to set this to the oppropriate channel.\n
            0 : MVP Channel\n
            1 : Game News\n
            2 : Level Up Channel"""
        )
        return
    
    await interaction.response.defer()

    conn,cur = create_connection()
    update_channel_id(interaction.channel_id, channel_type, interaction.guild_id, cur)
    close_connection(conn, cur)

    await interaction.followup.send(content= f"Channel type is now type : {channel_name[channel_type]}")



# Task loop commands
#----------------------

@tasks.loop(
        time = [
            dt.time(hour = 9, minute = 0, tzinfo=ZoneInfo("America/Los_Angeles")), 
            dt.time(hour = 20, minute = 57, tzinfo=ZoneInfo("America/Los_Angeles"))
        ]
)
async def get_game_news():
    # going to need to get a list off appids from everyones most recently played games that month
    # need to look at all the users who have that game and have played within a month and maybe @ them in the messages
    logger.info("Started news search process...")
    print("Started news search process...")

    for guild in client.guilds:
        member_list = []
        for member in guild.members:
            if member.id != client.user.id:
                member_list.append(member.id)
        # when we store the cannels for a guild find it first here instead
        news_dictionary = await asyncio.to_thread(process_member_games_into_news, member_list)
        #channel = guild.get_channel(int(os.getenv("CHANNEL2_ID")))

        conn,cur = create_connection()
        channel = get_channel(1, guild, cur)
        close_connection(conn,cur)
        if channel is None:
            logger.error(f"Could not find a channel in guild : {guild.id}")
            return

        for game_id, game_data in news_dictionary.items():
            if len(game_data['news_articles']) != 0:
                for article_url in game_data['news_articles']:
                    message = create_response(article_url, game_data['relavent_members'])
                    await channel.send(message)
    logger.info("news search finished")
    print("news search finished")


@tasks.loop(
    time = [
        dt.time(hour = 17, minute = 3, tzinfo=ZoneInfo("America/Los_Angeles"))
    ]
)
async def weekly_game_library_enrichment():
    
    if dt.datetime.now(timezone.utc).weekday() == 3:
        logger.info("Starting library enrichment")
        print("Starting library enrichment")
        await enrich_games_database(igdbclient)

SYNC_WORKERS = 5
syncing_process_sem = asyncio.Semaphore(SYNC_WORKERS)

async def syncing_process_task(member_id, guilds):
    async with syncing_process_sem:
        logger.info(f"Started syncing process for member : {member_id} with guilds : {guilds}")
        print(f"Started syncing process for member : {member_id}")

        snapshot, guild_table = get_level_snapshot(member_id, guilds)
        # put syncing process on a differnt thread
        await asyncio.to_thread(syncing_process, member_id)
        new_snapshot, _ = get_level_snapshot(member_id, guilds)
        for guild_id in new_snapshot:
            if new_snapshot[guild_id] != snapshot[guild_id]:
                print(f"User went from level {snapshot[guild_id]} to level {new_snapshot[guild_id]} in server {guild_id}")
                asyncio.create_task(level_up_message(snapshot[guild_id], new_snapshot[guild_id], member_id, guild_table[guild_id]))

# @tasks.loop(
#     time = [
#         dt.time(hour =11, minute = 58, tzinfo = ZoneInfo("America/Los_Angeles"))
#     ]
# )
@tasks.loop(
    time = [
        dt.time(hour =18, minute = 14, tzinfo = ZoneInfo("America/Los_Angeles"))
    ]
)
async def end_of_day_processes():
    #BOOKMARK need to also refresh things like weekly messages, clear 2 week old server_log, clear 2 day old news filter
    #await asyncio.to_thread(restart_tracked_activities)
    #await asyncio.sleep(120)

    logger.info("Began syncing process for users' steam library")
    print("Began syncing process for users' steam library")

    checked_members = set()
    tasks = []
    for guild in client.guilds:
        for member in guild.members:
            if member.id in checked_members or member.id == client.user.id:
                continue
            checked_members.add(member.id)

            auto_sync_enabled = get_auto_sync_value(member.id)
            
            if auto_sync_enabled == True:
                tasks.append(asyncio.create_task(syncing_process_task(member.id, client.guilds)))
            
    if tasks:
        await asyncio.gather(*tasks)


client.run(os.getenv("DISCORD_TOKEN"), log_handler=handler, log_level=logging.DEBUG)

