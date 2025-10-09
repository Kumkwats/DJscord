FROM python:3.12-slim-trixie

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y --no-install-recommends ffmpeg

RUN python -m pip install --upgrade pip

COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt
COPY __main__.py /app/
COPY DJscordBot/ /app/DJscordBot

WORKDIR /app

CMD ["python3", "-u", "."]