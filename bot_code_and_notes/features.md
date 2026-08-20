## On start up
on_ready()
1. Initialize the database when online
2. Add all members to the db
3. Clear all the items in the activity monitoring table

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
3. When user unlinks their steam remove steam id from **users**, remove all **user_games** that haven't been seen from activity monitoring, delete row from **general_steam_data**
4. User can either link through a custom id url or through steam id

## Calendar for past activity monitoring 
could have an internal calendar

| 1 | 2 | 3 | 4 | 5 | 6 | 7 |

current day = 1
when it becomes 12 current day += 1 and if current day > 7 day = 1 again 

## Daily stats/ weekly stats