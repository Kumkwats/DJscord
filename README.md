# DJscord

Started as a fork of a friend [repository](https://github.com/yrigaudeau/my-discord-bot) to add some little features and bug fixes but then has become his own custom thing over the years.

Made with **Python 3.12**<br>
Powered by **discord.py** and **yt-dlp**.

<br><br>

# Features

* Plays YT videos, Spotify tracks or any usual audio file
* Repeat, seek, goto, move or remove tracks in the queue
* Supports:
    * Youtube:
        * Search queries
        * Video links
        * Playlist links
    * Spotify (if given developper credentials):
        * Song link
        * Album/Single link
        * Playlist link



<br><br>



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

> Under the hood, the bot will gather the track artist and song name from the Spotify API and then make a YT search query to find a matching video tu use. Most of the times is works fine, but it may give weird results. To give more acurate results, we first try to use the **`song.link`** public API to get a matching video. As of 2025/10/09, the API is limited to 10 request per minute, so if it can't use the API or if any other problem occurs, it will fallback to the default search method.



<br>



## Resources folder

You may need to create a folder to store the resources that the bot may need, mainly the config file. But you can also spice up when the bot is joining and/or leaving when he's AFK with sounds!

The bot will pick a random sound for the startup in the `./resources/sounds/startup` folder and for the leave sound in the `./resources/sounds/leave`


<br><br><br>



# Installation

## Docker

The simplest way to run the bot is to run it in a docker container.

### Build image

First, you need to clone the repo and build the image.

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



<br><br>



## Docker Compose

You can also use Docker compose to simplify this setup. Here's a basic example :

```yaml
services:
  djscordbot:
    image: djscordbot:local
    build:
      context: <the-root-folder-of-this-repo>
      dockerfile: <path-to-the-dockerfile-if-needed>
    restart: unless-stopped
    volumes: #mandatory for the config file ATM
      - <path-to-the-resource-folder-to-mount>:/app/resources
```


<br><br>



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
sudo useradd -md /var/lib/djscord djscord
```



### Run
```bash
sudo -u djscord python3 .
```

### Install as service
```bash
sudo mv djscord.service /etc/systemd/system
sudo mkdir /opt/djscord
sudo cp * /opt/djscord
sudo systemctl daemon-reload
sudo systemctl enable djscord
sudo systemctl start djscord
```

### Uninstall
```bash
sudo systemctl disable djscord
sudo systemctl stop djscord
sudo rm /etc/systemd/system/djscord.service
sudo systemctl daemon-reload
sudo rm -r /opt/djscord
sudo rm -r /var/lib/djscord
```