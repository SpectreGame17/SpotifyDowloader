# Usa l'immagine ufficiale di Python 3.12.8
FROM python:3.12.8

# Installa FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Installa le librerie per Mutagen (per manipolare file audio, come MP3)
RUN apt-get install -y libmagic1

# Imposta la cartella di lavoro nel container
WORKDIR /app

# Copia i file del progetto dentro il container
COPY . .

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Imposta la variabile d'ambiente XDG_CACHE_HOME per evitare problemi con la cache
ENV XDG_CACHE_HOME=/app/yt-cache

# Copia il file .env
COPY .env .env

# Comando per avviare il programma
CMD ["python", "MultiThreadsSpotify.py"]
