# DJscord

Discord bot for playing music in server voice channel.

Started as a fork of a friend [repository](https://github.com/yrigaudeau/my-discord-bot) to add some little features and bug fixes but then has become his own custom thing over the years.

Made with **Python 3.12**<br>
Powered by **discord.py** and **yt-dlp**.

> [!CAUTION]
> Be aware that the messages sent by the bot are in the imaginary language known as 	<ins>**French**</ins>

<br>



# Features

* Play YT videos, Spotify tracks in a server voice channel
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
    * Should support [every sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) that is supported by **yt_dlp** but *"The only reliable way to check if a site is supported is to try it."*


<br>
<br>

# Setup

## Resource Folder Structure

Djscord will create the mandatory folders for its function : `resources/` where it stores `config.json` and `resources/download/` where it store downloaded audio files for playback in the voice channel.

DJscord can play custom sounds when it joins the voice channel. To add them, place audio files in the folder `resources/sounds/startup/`


## Configuration

There are 2 main ways to pass configs to DJscord : Environment Variables (includes `.env` file) or the `config.json` file mentionned above.

> [!IMPORTANT]
> Environment variables are the recommended way.<br>
> Both can coexist but the environment variables will take precedence over the JSON file.

<br>

### Discord Token

In order for Djscord to be able to communicate with Discord, you need to create a Discord Application [here](https://discord.com/developers/applications) and get a **bot token**.

> **Config key:**
> - Env variable : `DISCORD_TOKEN`
> - config.json : `discord-token`

<br>

### Spotify Developper Credentials (Optional)

The Spotify search isn't enabled by default as it needs credentials to access to the API. If you want to enable adding music from spotify links, you may create a Spotify application [here](https://developer.spotify.com/dashboard/applications)

> **Config key:**
> - Env variable : `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET`
> - config.json : `spotify-client-id` & `spotify-client-secret`

<br>

### BgUtils POT Provider (Optional)

[BgUtils POT Provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) is a HTTP server that can be run alongside Djscord to generate PO Tokens for yt_dlp to **help** prevent 403 errors and bot checks.

> [!NOTE]
> "Providing a PO token does not guarantee bypassing 403 errors or bot checks, but it may help your traffic seem more legitimate."

If you've setup the POT Provider, you need to specify the IP address in the config.

> **Config key:**
> - Env variable : `YTDLP_BGUTIL_SERVER_IP`
> - config.json : `bgutil-server-ip`


<br>
<br>

# Installation

## Docker Compose

Docker Compose is the simplest way to setup.

You just need to create a compose.yaml file in the root of the repo :

```yaml
services:
  djscordbot:
    image: djscordbot:local
    build:
      context: <path/of/the/root/folder/of/this/repo>
      dockerfile: <path/to/the/dockerfile>
    restart: unless-stopped
```

<br>

To pass environment variables, you can either use :

- The `environment` attribute to set them up directly :

```yaml
    environment:
      - DISCORD_TOKEN: "<your_bot_token_here>"
      - ...
```

- The `env_file` attribute if you choose to use the `.env` file: 

```yaml
    env_file: "<path/to/file.env>"
```

<br>

If using `config.json` or you want to be able to view the resource folder, you need to mount a folder to act as the resource folder.

```yaml
    volumes:
      - <path-to-the-resource-folder-to-mount>:/app/resources
```


Then to launch it with the command :

```bash
docker compose up --build -d
```

> [!IMPORTANT]
> Depending on how you've setup Docker, you may need to have admin privileges (e.g. `sudo`) to execute docker commands

<br>
<br>

## Linux installation and `systemd` service

> [!CAUTION]
> This method of installation has not be really maintained and lacks multiple steps:
> - Setup of the external tools necessary for the yt_dlp plugins used in Djscord : **Deno** (included in the dockerfile) for resolving JS challenges and the **POT Provider**
> - **Config setup** with environment variables or `config.json`. Please refer to the setup and docker section for this.

<br>

### Dependencies

DJscord needs **Python 3.12** with **pip**, **ffmpeg** for encoding/decoding the audio and **git** for cloning and updating the project.

**Ubuntu:**
```bash
sudo apt install python3 python3-pip ffmpeg git
```

<br>

### Clone repo and install python packages dependencies

```bash
git clone https://github.com/Kumkwats/DJscord.git
cd DJscord
pip install -r requirements.txt
```

> [!NOTE]
> Although not used in this tutorial, I recommend using Python's virtual environment.

<br>

### Run

> [!WARNING]
> You should always execute the run commands in the root folder of the repo

```bash
python3 .
```

<br>

### Running as user

It's recommended to run the python script as user on the system (not as root). You can run the bot on your current username or create a new one with a home folder that is the root folder of the repo

#### Create a user:
```bash
sudo useradd -md /var/lib/djscord djscord
```

#### Run as this new user:
```bash
sudo -u djscord python3 .
```

<br>

### Install as a `systemd` service

```bash
sudo mv djscord.service /etc/systemd/system
sudo mkdir /opt/djscord
sudo cp * /opt/djscord
sudo systemctl daemon-reload
sudo systemctl enable djscord
sudo systemctl start djscord
```

### Uninstall the service

```bash
sudo systemctl disable djscord
sudo systemctl stop djscord
sudo rm /etc/systemd/system/djscord.service
sudo systemctl daemon-reload
sudo rm -r /opt/djscord
sudo rm -r /var/lib/djscord
```
