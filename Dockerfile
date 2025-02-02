FROM python:3.10-bullseye
COPY requirements.txt /app/
COPY __main__.py /app/
COPY DJscordBot/ /app/DJscordBot
WORKDIR /app
RUN apt-get -y update && apt-get -y upgrade && apt-get install -y --no-install-recommends ffmpeg
RUN pip install -r requirements.txt
CMD ["python3", "-u", "."]