# DJscord

Made with Python 3.10  
In alpha early development

# Unique Features

* Playlists
    * Playlists are identified in queue
    * Possibility to loop within a playlist
    * Possibility to remove all songs in a playlist


# Config file and the resources folder

## Resources folder

You may need to create a folder to store the resources that the bot may need

## Config file
The config is the most important file

You can create a discord application by going here https://discord.com/developers/applications

Here are the two lines that must be in the `config.json` file
```json
{
    "prefix": "$",
    "discord-token": "<token>"
}
```
**You must put the config file at the root of the bot's resources folder.**

If you want to enable adding music from spotify, add the following lines to the config.json to make it look like that  

You can create a spotify application by going here https://developer.spotify.com/dashboard/applications
```json
{
    "spotify-client-id": "<id>",
    "spotify-client-secret": "<secret>"
}
```

Other settings include:
- `minutes-before-disconnecting` : Automaticaly disconnect the bot after n minutes without playing any sound 

# Docker Installation

The simplest way to run the bot is to run it in a docker container.



## Build image

First, we need to build the image.

> You may need to use sudo to run docker commands

```bash
docker build . -t djscordbot:latest
```



## Run with mounted resources folder

Mounting the resource folder is necessary as the config file and other resources files are not copied in the container. This allows to change the config file or add resources if needed without having to rebuild the image.

```bash
docker run -d --name djscordbot --restart unless-stopped -v ./resources/:/app/resources djscordbot:latest
```

## Stop the container
```bash
docker stop djscordbot
```





# Default Installation

## Clone repo and install dependencies
```bash
sudo apt install python3 python3-pip ffmpeg git
git clone https://github.com/yrigaudeau/my-discord-bot.git
cd my-discord-bot
pip install -r requirements.txt
```
## Running as user
It's recommended to run the python script as user on the system (not as root). You can run the bot on your current username or create a new one with home folder
```bash
sudo useradd -md /var/lib/dj-patrick dj-patrick
```



## Run
```bash
sudo -u dj-patrick python3 .
```

## Install as service
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