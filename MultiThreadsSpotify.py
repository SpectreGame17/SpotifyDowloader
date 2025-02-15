import os
import re
import spotipy
import uuid
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

def track_already_downloaded(track, output_folder):
    """Controlla se un brano è già presente nella cartella, verificando i metadati (titolo e artista)."""
    for mp3_file in Path(output_folder).glob("*.mp3"):
        try:
            audio = MP3(str(mp3_file), ID3=EasyID3)
            title = audio.get('title', [None])[0]
            artist = audio.get('artist', [None])[0]
            if title and artist:
                # Confronta in modo case-insensitive e rimuove spazi iniziali/finali
                if title.strip().lower() == track['name'].strip().lower() and artist.strip().lower() == track['artists'].strip().lower():
                    return True
        except Exception as e:
            continue
    return False

def get_spotify_album_tracks(album_url):
    """Ottiene la lista dei brani da un album di Spotify."""
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    
    # Estrae l'ID dell'album dall'URL
    if "album" in album_url:
        album_id = album_url.split("/")[-1].split("?")[0]
    else:
        raise ValueError("Invalid album URL")
    
    album_info = sp.album(album_id)
    album_name = album_info.get('name', 'Unknown Album')
    
    clear_terminal()
    print(Fore.GREEN + Style.BRIGHT + f"You're downloading from Album: {album_name}" + Style.RESET_ALL)
    
    tracks = []
    for track in album_info['tracks']['items']:
        name = track.get('name', 'Unknown Track')
        artists = ', '.join([artist.get('name', 'Unknown Artist') for artist in track.get('artists', [])])
        track_number = track.get('track_number', None)
        release_date = album_info.get('release_date', 'Unknown Year')
        year = release_date.split("-")[0]
        
        tracks.append({
            'name': name,
            'artists': artists,
            'album': album_name,
            'track_number': track_number,
            'year': year  
        })
    return tracks

def get_spotify_single_track(track_url):
    """Ottiene le informazioni di un singolo brano di Spotify."""
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    
    # Estrae l'ID del brano dall'URL
    if "track" in track_url:
        track_id = track_url.split("/")[-1].split("?")[0]
    else:
        raise ValueError("Invalid track URL")
    
    track = sp.track(track_id)
    name = track.get('name', 'Unknown Track')
    artists = ', '.join([artist.get('name', 'Unknown Artist') for artist in track.get('artists', [])])
    album = track.get('album', {}).get('name', 'Unknown Album')
    track_number = track.get('track_number', None)
    release_date = track.get('album', {}).get('release_date', 'Unknown Year')
    year = release_date.split("-")[0]
    
    clear_terminal()
    print(Fore.GREEN + Style.BRIGHT + f"You're downloading track: {name}" + Style.RESET_ALL)
    
    return [{
        'name': name,
        'artists': artists,
        'album': album,
        'track_number': track_number,
        'year': year  
    }]

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
    """Scarica un video da YouTube come file audio, imposta i metadati e rinomina il file."""
    # Calcola il nome finale basato sul titolo originale, pulito da caratteri non ammessi
    final_name = re.sub(r'[\/:*?."<>|]', " ", track_info['name']).strip().rstrip('.')
    
    # Genera un nome temporaneo unico usando uuid per garantire l'unicità in ambienti multithread
    temp_name = uuid.uuid4().hex
    temp_output_path = Path(output_folder) / temp_name

    preferred_codec = os.getenv("PREFERRED_CODEC", "mp3")
    preferred_quality = os.getenv("PREFERRED_QUALITY", "192")
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': preferred_codec,
            'preferredquality': preferred_quality,
        }],
        'outtmpl': str(temp_output_path),  # Usa il nome temporaneo per il download
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Il file scaricato sarà salvato come <temp_output_path>.mp3
    temp_file_with_ext = str(temp_output_path) + ".mp3"
    try:
        audio = MP3(temp_file_with_ext, ID3=EasyID3)
        audio['title'] = track_info['name']
        audio['artist'] = track_info['artists']
        audio['album'] = track_info['album']
        if track_info['track_number']:
            audio['tracknumber'] = str(track_info['track_number'])
        audio.save()
    except Exception as e:
        print(f"Error adding metadata to temporary file: {e}")
        file_path = os.path.join(output_folder, "Error.txt")
        if not os.path.exists(file_path):
            open(file_path, 'w').close()
        with open(file_path, 'a') as file:
            file.write(f"[ERROR] adding metadata to temporary file: {e}\n")

    # Rinomina il file temporaneo con il nome finale (aggiungendo l'estensione .mp3)
    final_output_path = Path(output_folder) / final_name
    final_file_with_ext = str(final_output_path) + ".mp3"
    if not os.path.exists(final_file_with_ext):
        os.rename(temp_file_with_ext, final_file_with_ext)
    else:
        # Se esiste già un file con il nome basato sul titolo, genera un nome alternativo con titolo e artista
        alt_final_name = f"{final_name} - {track_info['artists']}"
        alt_final_name = re.sub(r'[\/:*?."<>|]', " ", alt_final_name).strip().rstrip('.')
        alt_final_output_path = Path(output_folder) / alt_final_name
        alt_final_file_with_ext = str(alt_final_output_path) + ".mp3"
        if not os.path.exists(alt_final_file_with_ext):
            os.rename(temp_file_with_ext, alt_final_file_with_ext)
            final_file_with_ext = alt_final_file_with_ext
        else:
            print(f"File already exists: {alt_final_file_with_ext}. Removing temporary file.")
            os.remove(temp_file_with_ext)

    # Controllo post-rinominazione: verifica se il nome del file corrisponde al titolo nei metadati
    try:
        if os.path.exists(final_file_with_ext):
            audio = MP3(final_file_with_ext, ID3=EasyID3)
            metadata_title = audio.get('title', [final_name])[0]
            sanitized_title = re.sub(r'[\/:*?."<>|]', " ", metadata_title).strip().rstrip('.')
            current_name = Path(final_file_with_ext).stem  # nome senza estensione
            if sanitized_title != current_name:
                # Rinomina in base al titolo sanificato
                new_final_output_path = Path(output_folder) / sanitized_title
                new_final_file_with_ext = str(new_final_output_path) + ".mp3"
                if not os.path.exists(new_final_file_with_ext):
                    os.rename(final_file_with_ext, new_final_file_with_ext)
                    print(f"File renamed post-download to: {new_final_file_with_ext}")
                    final_file_with_ext = new_final_file_with_ext
                else:
                    print(f"Post-rename target already exists: {new_final_file_with_ext}. Keeping original file.")
    except Exception as e:
        print(f"Error in post-renaming check: {e}")
        file_path = os.path.join(output_folder, "Error.txt")
        if not os.path.exists(file_path):
            open(file_path, 'w').close()
        with open(file_path, 'a') as file:
            file.write(f"[ERROR] Error in post-renaming check: {e}\n")

def process_track(track, output_folder):
    """Processa un singolo brano: controlla se è già presente (con metadati), altrimenti lo cerca su YouTube, lo scarica e imposta i metadati."""
    try:
        # Se nei metadati di un file già esistente troviamo lo stesso titolo e artista, salta il download
        if track_already_downloaded(track, output_folder):
            print(f"Skipping, already exists (by metadata): {track['name']} - {track['artists']}")
            return

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
        spotify_url = input("Enter the Spotify link: ")
        output_folder = input("Enter the destination folder: ")

        if not output_folder:
            output_folder = "/app/downloads"  # Cartella predefinita nel container

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        clear_terminal()
        print(f"The songs will be saved in: {output_folder}")

        # Determina il tipo di link e ottiene le tracce corrispondenti
        if "playlist" in spotify_url:
            print("Extracting tracks from the playlist...")
            tracks = get_spotify_playlist_tracks(spotify_url)
        elif "album" in spotify_url:
            print("Extracting tracks from the album...")
            tracks = get_spotify_album_tracks(spotify_url)
        elif "track" in spotify_url:
            print("Extracting track information...")
            tracks = get_spotify_single_track(spotify_url)
        else:
            print("Unsupported Spotify URL.")
            continue

        print("\nDownloading tracks...")
        max_threads = os.getenv("MAX_THREADS")
        if max_threads is not None:
            max_threads = int(max_threads)
        else:
            max_threads = 4  

        with ThreadPoolExecutor(max_threads) as executor:
            for track in tracks:
                executor.submit(process_track, track, output_folder)

        # clear_terminal()
        print("\nDownload complete!")

        # Chiede all'utente se vuole ripetere il processo
        again = input("Do you want to download another item? (y/n): ").strip().lower()
        if again != 'y':
            print("Exiting...")
            break  # Esce dal ciclo e termina il programma
