## On start up
on_ready()
1. Initialize the database when online
2. Add all members to the db
3. Clear all the items in the activity monitoring table

## New users
1. New users are added to the guild and their profiles will be set up

## Command to set active channel to send messages/announcements in
1. /set_channel? could have a channel for gaming news| level up | weekly stats
2. Also worth having a happy holidays thing that celebrates holidays

## Activity monitoring 

on_presence_update()
1. Look to see what game the user is playing
2. If game is started to be played:
    * use **after**.activity to get the name of the game and if not already add it to the db
    * get the date and time and store that
    * put that game along with the user id in the activity monitoring table
    * update the user_games last played
3. After activity ends:
    * use **before**.activity to get the name and look up that id in the table
    * get the current time and subtract it from start time to get *seconds played*
    * store seconds played in the **user_games** along with the 
4. Stream monitoring. Use it to find the games as well as to give xp to the user

## Steam linking

1. When linking steam will add all the games found to the games list
2. Auto sync will be on by default unless the user changes their profile settings or unliks their steam
3. The sync should only update the recently played if the most recent time is older than a day
3. When user unlinks their steam remove steam id from **users**, remove all **user_games** that haven't been seen from activity monitoring, delete row from **general_steam_data**
4. User can either link through a custom id url or through steam id

## Steam Syncinc 
1. Sync is automatically set at first then if the profile goes to private or the user unsyncs then it is turned off
2. When the hours for a game changes update recently played if not already. Maybe if the time checked is within 6 or so hours of the recently played

## Game recommendation feature

1. Checks all the people in the voice call to see what games everyone has
2. There could be a recommend all command that just says what games everyone has 
3. Maybe I could update the price of each game in the library once a day to see if there is a sale

## Calendar for past activity monitoring 
could have an internal calendar

| 1 | 2 | 3 | 4 | 5 | 6 | 7 |

current day = 1
when it becomes 12 current day += 1 and if current day > 7 day = 1 again 

1. maybe a two week or so callendar that tracks activity and averages them to be added to player profile 
2. Maybe each player could get 14 columns and could average the days they play into 14

## Weekly stats

1. Messages, stream time, game time, and stuff should all contribute to weekly stats
2. There should be a player of the week or mvp sytem where every win increases the difficulty of getting mvp and decreases for people who havn't won
3. Weekly stats should keep track of the games played that week 


4. Maybe I could refresh the price info at night time 