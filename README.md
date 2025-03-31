# DJscord

Made with Python 3.10.<br>
Powerd by py-cord and yt-dlp.
<br><br>

# Features

* Plays YT videos, Spotify tracks or any usual audio file
* Repeat, seek, goto, move or remove tracks in the queue
* Automatic AFK leave
* Supports YT Playlists
    * Playlists are identified in queue
    * Able to loop a playlist

<br>

# Config file and the resources folder



## The Config file
A config file is mandatory to run the bot, as it needs a Discord Application Token.
You can create a Discord Application by going here https://discord.com/developers/applications

Running the bot without a config file will create a default at the correct place (i.e. `./resources/config.json`).
Although it creates one for you, you still have to replace the field for `discord-token`:
```json
{
    "discord-token": "<your discord token here>"
}
```


The Spotify search isn't enabled by default as it needs credentials to access to the API. If you want to enable adding music from spotify links, you may create a Spotify application and add the following lines to the `config.json` file.
```json
{
    "spotify-client-id": "<id>",
    "spotify-client-secret": "<secret>"
}
```
You can create a spotify application by going here https://developer.spotify.com/dashboard/applications

> Under the hood, the bot will gather the track artist and song name from the Spotify API and then make a YT search query to find a matching video tu use. Most of the times is works fine, but it may give weird results. To give more acurate results, we first try to use the **`song.link`** public API to get a matching video. As of 2025/03/31, the API is limited to 10 request per minute, so if we can't use the API or if any other problem occurs, it will fallback to the default search method.


### Other settings:
- `minutes-before-disconnecting` : Automaticaly disconnect the bot after n minutes without playing any sound 


## Resources folder

You may need to create a folder to store the resources that the bot may need, mainly the config file. But you can also spice up when the bot is joining and/or leaving when he's AFK with sounds!

The bot will pick a random sound for the startup in the `./resources/sounds/startup` folder and for the leave sound in the `./resources/sounds/leave`

<br>

# Installation

## Docker

The simplest way to run the bot is to run it in a docker container.

### Build image

First, we need to clone the repo and build the image.

> You may need to use sudo to run docker commands

```bash
git clone https://github.com/Kumkwats/DJscord.git
cd DJscord
docker build . -t djscordbot:latest
```


### Run with mounted resources folder

Mounting the resource folder is necessary as the config file and other resources files are not copied in the container. This allows us to change the config file or add resources if needed and we don't have to recreate the resources each time we are updating and rebuilding the image.

```bash
docker run -d --name djscordbot --restart unless-stopped -v ./resources/:/app/resources djscordbot:latest
```

### Stop the container
```bash
docker stop djscordbot
```

<br>

## Installation as a systemd service

### Clone repo and install dependencies
```bash
sudo apt install python3 python3-pip ffmpeg git
git clone https://github.com/Kumkwats/DJscord.git
cd DJscord
pip install -r requirements.txt
```
### Running as user
It's recommended to run the python script as user on the system (not as root). You can run the bot on your current username or create a new one with home folder
```bash
sudo useradd -md /var/lib/dj-patrick dj-patrick
```



### Run
```bash
sudo -u dj-patrick python3 .
```

### Install as service
```bash
sudo mv dj-patrick.service /etc/systemd/system
sudo mkdir /opt/dj-patrick
sudo cp * /opt/dj-patrick
sudo systemctl daemon-reload
sudo systemctl enable dj-patrick
sudo systemctl start dj-patrick
```

### Uninstall
```bash
sudo systemctl disable dj-patrick
sudo systemctl stop dj-patrick
sudo rm /etc/systemd/system/dj-patrick.service
sudo systemctl daemon-reload
sudo rm -r /opt/dj-patrick
sudo rm -r /var/lib/dj-patrick
```