import os
import re
import spotipy
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from pathlib import Path
from colorama import Fore, Style

# Carica le variabili d'ambiente dal file .env
load_dotenv()
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

def clear_terminal():
    """Pulisce il terminale a seconda del sistema operativo."""
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:  # macOS e Linux
        os.system('clear')

def get_spotify_playlist_tracks(playlist_url):
    """Ottiene la lista dei brani da una playlist di Spotify."""
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    
    # Estrae l'ID della playlist dall'URL
    if "playlist" in playlist_url:
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
    else:
        raise ValueError("Invalid playlist URL")

    tracks = []
    offset = 0

    # Ottiene i dettagli della playlist
    playlist_info = sp.playlist(playlist_id)
    playlist_name = playlist_info['name']

    clear_terminal()
    # Stampa il nome della playlist in verde e grassetto
    print(Fore.GREEN + Style.BRIGHT + f"You're downloading from: {playlist_name}" + Style.RESET_ALL)

    while True:
        results = sp.playlist_tracks(playlist_id, offset=offset)

        for item in results['items']:
            track = item['track']
            if track:
                name = track.get('name', 'Unknown Track')
                artists = ', '.join([artist.get('name', 'Unknown Artist') if artist.get('name') else 'Unknown Artist' for artist in track.get('artists', [])])
                album = track.get('album', {}).get('name', 'Unknown Album')
                track_number = track.get('track_number', None)
                release_date = track['album'].get('release_date', 'Unknown Year')
                year = release_date.split("-")[0]  # Prende solo l'anno

                if artists:
                    tracks.append({
                        'name': name,
                        'artists': artists,
                        'album': album,
                        'track_number': track_number,
                        'year': year  
                    })
            else:
                print("Track is None, skipping...")

        # Se non ci sono più brani da caricare, esce dal loop
        if len(results['items']) < 100:
            break

        offset += 100

    return tracks

def search_youtube(query):
    """Cerca un video su YouTube utilizzando yt-dlp."""
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch1',  # Cerca il primo risultato su YouTube
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info and len(info['entries']) > 0:
            return info['entries'][0]['webpage_url']
        else:
            return None

def download_from_youtube(url, output_folder, track_info):
    """Scarica un video da YouTube come file audio e imposta i metadati."""
    file_name = re.sub(r'[\/:*?."<>|]', " ", track_info['name'])  # Pulisce il nome del file
    output_path = Path(output_folder) / file_name  # Crea il percorso del file
    preferred_codec = os.getenv("PREFERRED_CODEC", "mp3")  # Default: "mp3"
    preferred_quality = os.getenv("PREFERRED_QUALITY", "192")  # Default: "192"
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': preferred_codec,
                'preferredquality': preferred_quality,
            }
        ],
        'outtmpl': str(output_path),  # Converte il percorso in stringa per yt-dlp
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Aggiunge i metadati al file MP3 scaricato
    try:
        output_path_string = str(output_path) + ".mp3"
        audio = MP3(output_path_string, ID3=EasyID3)  # Apre il file MP3
        audio['title'] = track_info['name']
        audio['artist'] = track_info['artists']
        audio['album'] = track_info['album']
        if track_info['track_number']:
            audio['tracknumber'] = str(track_info['track_number'])
        audio.save()
    except Exception as e:
        print(f"Error adding metadata to {file_name}: {e}")
        file_path = os.path.join(output_folder, "Error.txt")

        if not os.path.exists(file_path):
            open(file_path, 'w').close()

        with open(file_path, 'a') as file:
            file.write(f"[ERROR] adding metadata to {file_name}: {e}\n")

def process_track(track, output_folder):
    """Processa un singolo brano: lo cerca su YouTube, lo scarica e imposta i metadati."""
    try:
        query = f"{track['name']} \"{track['artists']}\""
        print(f"Searching: {query}")
        youtube_url = search_youtube(query)

        if youtube_url:
            print(f"Downloading from: {youtube_url}")
            download_from_youtube(youtube_url, output_folder, track)
        else:
            print(f"Not found on YouTube: {query}")
         
    except Exception as e:
        print(f"Error processing track {track['name']} by {track['artists']}: {e}")
        file_path = os.path.join(output_folder, "Not found.txt")

        if not os.path.exists(file_path):
            open(file_path, 'w').close()

        with open(file_path, 'a') as file:
            file.write(f"[MISSING] Song not found: {track['name']} by {track['artists']}: {e}\n")

# --- Funzione principale ---
if __name__ == "__main__":
    while True:  # Ciclo infinito
        playlist_url = input("Enter the Spotify playlist link: ")
        output_folder = input("Enter the destination folder: ")

        if not output_folder:
            output_folder = "/app/downloads"  # Cartella predefinita nel container

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        clear_terminal()
        print(f"The songs will be saved in: {output_folder}")

        print("Extracting tracks from the playlist...")
        tracks = get_spotify_playlist_tracks(playlist_url)

        print("\nDownloading tracks...")
        max_threads = os.getenv("MAX_THREADS")
        if max_threads is not None:
            max_threads = int(max_threads)
        else:
            max_threads = 4  

        with ThreadPoolExecutor(max_threads) as executor:
            for track in tracks:
                executor.submit(process_track, track, output_folder)

        clear_terminal()
        print("\nDownload complete!")

        # Chiede all'utente se vuole ripetere il processo
        again = input("Do you want to download another playlist? (y/n): ").strip().lower()
        if again != 'y':
            print("Exiting...")
            break  # Esce dal ciclo e termina il programma
