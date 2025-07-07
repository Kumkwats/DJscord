FROM python:3.10-bullseye
COPY requirements.txt /app/
COPY __main__.py /app/
COPY DJscordBot/ /app/DJscordBot

WORKDIR /app

RUN apt-get -y update && apt-get -y upgrade && apt-get install -y --no-install-recommends ffmpeg

# getting latest version of discord.py while waiting for the update to go live in PyPI
RUN git clone https://github.com/Rapptz/discord.py ./dev/discord.py
RUN python3 -m pip install ./dev/discord.py/[voice]

RUN pip install -r requirements.txt


CMD ["python3", "-u", "."]