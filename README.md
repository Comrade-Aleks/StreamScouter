# Game Streamer Tracker
This is an app that tracks the top whatever number of streamers for any game you want.
it has the function to notify you if a new streamer comes up. 

To get it running, you will first have to go to the [Twitch developers website](https://dev.twitch.tv) create an account.
then go to your console (it should be in the top right corner)

after this, you go to "Applications" then "Register your Application"

Once Registerd, you should be seeing your client ID, this string of numbers and letters should go into the client ID part of the settings within the app

On the same website, you will also see "New Secret" you will have to click this, also do the "im not a robot" thing and you will get another string of numbers and letters:
this string is called client secret and should go into its own part of the settings tab within the app.

after filling both inputs (client ID and client secret) you can save and then click generate access token. 

once the access token is generated, it will be saved in a .env file within the folder the app is located.

Now you are basically done. and can use the app.

How to use: 

1. write a game name (must be the whole name as written on twitch)
2. choose how many streamers you want to look after (it will look from most views and down)
3. click the button and it should work.

REMEMBER 
this app is designed to also run in the background, so if you click the X to close window it will be minimized to the ash tray (small icon in bottom right corner)
to fully close it or to show the app again, just right click the icon and press one of the two buttons. 

also, the api wont work with over 60 names. so so try to keep it below that. 

