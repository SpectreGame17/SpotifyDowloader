import os
import re
import uuid
import threading
import shutil
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import spotipy
import yt_dlp
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from colorama import Fore, Style

# Carica le variabili d'ambiente dal file .env
load_dotenv()
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
max_threads = int(os.getenv("MAX_THREADS", "4"))
#codec = os.getenv("PREFERRED_CODEC", "mp3")  # Impostiamo il codec senza il punto
codec = "mp3" #Il supporto a codec diversi non è al momento dispobile
codec = '.' + codec if not codec.startswith('.') else codec  # Aggiungiamo il punto se manca
#set dati file scaricati
DATA_FILE = "data.dat"
# Lock per operazioni critiche sui file
file_lock = threading.Lock()
# Set globale per tracce in elaborazione (chiave: (titolo, artista) in lowercase)
in_processing = set()




def log_error(message, output_folder):
    """Scrive un messaggio di errore nel file log.txt nella cartella di output."""
    log_file = os.path.join(output_folder, "log.txt")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def clear_terminal():
    """Pulisce il terminale a seconda del sistema operativo."""
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')


def get_spotify_playlist_tracks(playlist_url):
    """Ottiene la lista dei brani da una playlist di Spotify."""
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    if "playlist" in playlist_url:
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
    else:
        raise ValueError("Invalid playlist URL")

    tracks = []
    offset = 0
    playlist_info = sp.playlist(playlist_id)
    playlist_name = playlist_info['name']

    clear_terminal()
    print(Fore.GREEN + Style.BRIGHT + f"You're downloading from: {playlist_name}" + Style.RESET_ALL)

    while True:
        results = sp.playlist_tracks(playlist_id, offset=offset)
        for item in results['items']:
            track = item['track']
            if track:
                name = track.get('name', 'Unknown Track')
                artists = ', '.join([artist.get('name', 'Unknown Artist') for artist in track.get('artists', [])])
                album = track.get('album', {}).get('name', 'Unknown Album')
                track_number = track.get('track_number', None)
                release_date = track['album'].get('release_date', 'Unknown Year')
                year = release_date.split("-")[0]
                tracks.append({
                    'name': name,
                    'artists': artists,
                    'album': album,
                    'track_number': track_number,
                    'year': year  
                })
            else:
                print(Fore.YELLOW + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Track is None, skipping...")

        if len(results['items']) < 100:
            break
        offset += 100

    return tracks


def get_spotify_album_tracks(album_url):
    """Ottiene la lista dei brani da un album di Spotify."""
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)

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


def track_already_downloaded(track, output_folder):
    """
    Controlla se un brano è già presente nella cartella, verificando i metadati (titolo e artista).
    Vengono controllati solo i file finali (quelli con metadati).
    """
    for file in Path(output_folder).glob(f"*{codec}"):
        try:
            audio = MP3(str(file), ID3=EasyID3)
            title = audio.get('title', [None])[0]
            artist = audio.get('artist', [None])[0]
            if title and artist:
                if title.strip().lower() == track['name'].strip().lower() and artist.strip().lower() == track['artists'].strip().lower():
                    return True
        except Exception:
            continue
    return False


def search_youtube(query, output_folder):
    """
    Cerca un video su YouTube utilizzando yt-dlp.
    Prova prima con la query originale e, in caso di errore (ad esempio 403), prova ad aggiungere "lyrics".
    Restituisce l'URL del primo risultato disponibile.
    """
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch5',
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
        except Exception as e:
            log_error(f"YouTube search error for query '{query}': {e}", output_folder)
            info = None
        if info and 'entries' in info and len(info['entries']) > 0:
            for entry in info['entries']:
                webpage_url = entry.get('webpage_url')
                if webpage_url:
                    return webpage_url
    # Se la ricerca con la query originale non ha prodotto risultati, prova con "lyrics"
    alt_query = query + " lyrics"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(alt_query, download=False)
        except Exception as e:
            log_error(f"YouTube search error for alternative query '{alt_query}': {e}", output_folder)
            return None
        if info and 'entries' in info and len(info['entries']) > 0:
            for entry in info['entries']:
                webpage_url = entry.get('webpage_url')
                if webpage_url:
                    return webpage_url
    return None


# === FASE 1: Download dei file (senza metadati e senza rinomina) ===
def download_track(track, output_folder):
    """
    Scarica il brano da YouTube e restituisce il percorso del file temporaneo.
    Se il brano è già presente (verificato sui file finali) o in elaborazione, ritorna None.
    """
    key = (track['name'].strip().lower(), track['artists'].strip().lower())
    if key in in_processing or track_already_downloaded(track, output_folder):
        print(Fore.YELLOW + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Skipping, already exists or in processing: {track['name']} - {track['artists']}")
        return None

    in_processing.add(key)
    query = f"{track['name']} \"{track['artists']}\""
    print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Searching: {query}")
    youtube_url = search_youtube(query, output_folder)
    if not youtube_url:
        log_error(f"Not found on YouTube: {query}", output_folder)
        in_processing.remove(key)
        return None

    print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Downloading from: {youtube_url}")
    temp_name = uuid.uuid4().hex
    temp_output_path = Path(output_folder) / temp_name
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': os.getenv("PREFERRED_CODEC", "mp3"),
            'preferredquality': os.getenv("PREFERRED_QUALITY", "192"),
        }],
        'outtmpl': str(temp_output_path),
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        log_error(f"Download error for {track['name']}: {e}", output_folder)
        in_processing.remove(key)
        return None

    temp_file = str(temp_output_path) + codec
    if not os.path.exists(temp_file):
        log_error(f"Temporary file not found for {track['name']}", output_folder)
        in_processing.remove(key)
        return None

    return temp_file


# === FASE 2: Aggiunta metadati ===
def add_metadata_to_file(temp_file, track_info, output_folder):
    """
    Aggiunge i metadati al file audio in base al codec scelto.
    Ritorna True se va a buon fine, False altrimenti.
    """
    try:
        audio = MP3(temp_file, ID3=EasyID3)
        audio['title'] = track_info['name']
        audio['artist'] = track_info['artists']
        audio['album'] = track_info['album']
        if track_info['track_number']:
            audio['tracknumber'] = str(track_info['track_number'])
        audio.save()
        del audio  # Rilascia la risorsa
        return True
    except Exception as e:
        log_error(f"Error adding metadata for {track_info['name']}: {e}", output_folder)
        return False



# === FASE 3: Rinomina del file ===
def rename_file(temp_file, track_info, output_folder):
    """
    Rinomina il file temporaneo in base al titolo del brano.
    Se esiste già un file con quel nome, prova a usare "nome brano - nome autore".
    Se anche questo esiste, aggiunge un suffisso numerico.
    Ritorna il percorso finale del file.
    Implementa un meccanismo di retry se il file è in uso.
    """
    final_name = re.sub(r'[\/:*?."<>|]', " ", track_info['name']).strip().rstrip('.')
    final_output_path = Path(output_folder) / final_name
    final_file = str(final_output_path) + codec

    max_retries = 5
    for attempt in range(max_retries):
        try:
            with file_lock:
                if not os.path.exists(final_file):
                    os.rename(temp_file, final_file)
                else:
                    # Prova con "nome brano - nome autore"
                    alt_final_name = f"{final_name} - {track_info['artists']}"
                    alt_final_name = re.sub(r'[\/:*?."<>|]', " ", alt_final_name).strip().rstrip('.')
                    alt_final_output_path = Path(output_folder) / alt_final_name
                    alt_final_file = str(alt_final_output_path) + codec
                    if not os.path.exists(alt_final_file):
                        os.rename(temp_file, alt_final_file)
                        final_file = alt_final_file
                    else:
                        # Fallback: aggiungi un suffisso numerico
                        i = 1
                        while os.path.exists(f"{final_output_path}-{i}{codec}"):
                            i += 1
                        final_file = f"{final_output_path}-{i}{codec}"
                        os.rename(temp_file, final_file)
            break
        except OSError as e:
            if hasattr(e, "winerror") and e.winerror == 32:
                print(Fore.YELLOW + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"File in use, retrying rename for {final_file} (attempt {attempt+1}/{max_retries})")
                time.sleep(0.5)
            else:
                raise e
    else:
        print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Failed to rename {temp_file} after {max_retries} attempts.")
        return None

    # Post-rinominazione: controlla che il nome del file corrisponda ai metadati
    try:
        if os.path.exists(final_file):
            audio = MP3(final_file, ID3=EasyID3)
            metadata_title = audio.get('title', [final_name])[0]
            sanitized_title = re.sub(r'[\/:*?."<>|]', " ", metadata_title).strip().rstrip('.')
            current_name = Path(final_file).stem
            if sanitized_title != current_name:
                new_final_output_path = Path(output_folder) / sanitized_title
                new_final_file = str(new_final_output_path) + codec
                if not os.path.exists(new_final_file):
                    os.rename(final_file, new_final_file)
                    final_file = new_final_file
                else:
                    print(Fore.YELLOW + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Post-rename target already exists: {new_final_file}. Keeping original file.")
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Error in post-renaming check for {track_info['name']}: {e}")
        error_file = os.path.join(output_folder, "Error.txt")
        with open(error_file, 'a') as file:
            file.write(f"[ERROR] Post-renaming check for {track_info['name']}: {e}\n")

    return final_file


def finalize_track_processing(track):
    """Rimuove la traccia dal set in_processing."""
    key = (track['name'].strip().lower(), track['artists'].strip().lower())
    in_processing.discard(key)


# === FASE 4: Verifica finale e correzione ===
def phase4_verification(output_folder):
    """
    Controlla tutti i file nella cartella di output:
      - Per ogni file .mp3, se mancano i metadati (title o artist), li imposta:
          * Usa il nome del file come title.
          * Imposta "Unknown" come artist se mancante.
    """
    for file in Path(output_folder).iterdir():
        if not file.is_file():
            continue

        # Processa solo i file con estensione .mp3
        if file.suffix.lower() != ".mp3":
            continue

        try:
            audio = MP3(str(file), ID3=EasyID3)
            title = audio.get('title', [None])[0]
            artist = audio.get('artist', [None])[0]
            changed = False
            if not title:
                default_title = file.stem
                print(Fore.YELLOW + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL +
                      f"File {file} missing title. Setting title to '{default_title}'")
                audio['title'] = default_title
                changed = True
            if not artist:
                print(Fore.YELLOW + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL +
                      f"File {file} missing artist. Setting artist to 'Unknown'")
                audio['artist'] = "Unknown"
                changed = True
            if changed:
                audio.save()
        except Exception as e:
            log_error(f"Error processing file {file}: {e}", output_folder)

def spotifydl(spotify_url, output_folder, flag):
    
            if not output_folder:
                output_folder = "/app/downloads"
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            clear_terminal()
            
            # Estrae le tracce in base al tipo di URL e ne verifica la correttezza
            if "playlist" in spotify_url:
                print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Extracting tracks from the playlist...")
                tracks = get_spotify_playlist_tracks(spotify_url)
                if flag == 1:
                    save_entry(spotify_url, output_folder)
            elif "album" in spotify_url:
                print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Extracting tracks from the album...")
                tracks = get_spotify_album_tracks(spotify_url)
            elif "track" in spotify_url:
                print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Extracting track information...")
                tracks = get_spotify_single_track(spotify_url)
            else:
                print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Unsupported Spotify URL.")
                return #in caso di errore esce dalla funzione
                
            print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"The songs will be saved in: {output_folder}")

            # Deduplica le tracce basandosi su (titolo, artista)
            unique_tracks = []
            seen = set()
            for track in tracks:
                key = (track['name'].strip().lower(), track['artists'].strip().lower())
                if key not in seen:
                    unique_tracks.append(track)
                    seen.add(key)
            tracks = unique_tracks

            print("\n=== PHASE 1: Download tracks ===")
            downloaded_items = []  # Lista di dict: { 'track': ..., 'temp_file': ... }
            with ThreadPoolExecutor(max_threads) as executor:
                future_to_track = {executor.submit(download_track, track, output_folder): track for track in tracks}
                for future in as_completed(future_to_track):
                    track = future_to_track[future]
                    try:
                        temp_file = future.result()
                        if temp_file:
                            downloaded_items.append({"track": track, "temp_file": temp_file})
                            print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Downloaded: {track['name']} - Temp file: {temp_file}")
                    except Exception as e:
                        log_error(f"Error downloading track {track['name']}: {e}", output_folder)
                        print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Error downloading track {track['name']}: {e}")

            print("\n=== PHASE 2: Adding metadata ===")
            with ThreadPoolExecutor(max_threads) as executor:
                future_to_item = {executor.submit(add_metadata_to_file, item["temp_file"], item["track"], output_folder): item for item in downloaded_items}
                for future in as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        success = future.result()
                        if success:
                            print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Metadata added for: {item['track']['name']}")
                        else:
                            log_error(f"Error adding metadata for: {item['track']['name']}", output_folder)
                            print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Error adding metadata for: {item['track']['name']}")
                    except Exception as e:
                        log_error(f"Error adding metadata for {item['track']['name']}: {e}", output_folder)
                        print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Error adding metadata for {item['track']['name']}: {e}")

            print("\n=== PHASE 3: Renaming files ===")
            with ThreadPoolExecutor(max_threads) as executor:
                future_to_item = {executor.submit(rename_file, item["temp_file"], item["track"], output_folder): item for item in downloaded_items}
                for future in as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        final_path = future.result()
                        print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"File for {item['track']['name']} renamed to: {final_path}")
                    except Exception as e:
                        log_error(f"Error renaming file for {item['track']['name']}: {e}", output_folder)
                        print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Error renaming file for {item['track']['name']}: {e}")
                    finally:
                        finalize_track_processing(item["track"])

            print("\n=== PHASE 4: Final verification ===")
            phase4_verification(output_folder)
            clear_terminal()
            

def load_entries():
    """Legge tutte le righe del file e salva spotify_url e output_folder in due liste."""
    spotify_urls = []
    output_folders = []

    if not os.path.exists(DATA_FILE):
        return spotify_urls, output_folders  # Se il file non esiste, ritorna liste vuote

    with open(DATA_FILE, "r") as file:
        for line in file:
            parts = line.strip().split(" ", 1)  # Divide in due parti: URL e cartella
            if len(parts) == 2:
                spotify_urls.append(parts[0])
                output_folders.append(parts[1])

    return spotify_urls, output_folders

def clean_entries():
    """Rimuove dal file data.dat le voci con cartelle non più esistenti."""
    spotify_urls, output_folders = load_entries()
    
    # Filtra solo gli elementi con una cartella esistente
    valid_entries = [(url, folder) for url, folder in zip(spotify_urls, output_folders) if os.path.exists(folder)]

    # Riscrive il file data.dat con solo le voci valide
    with open(DATA_FILE, "w") as file:
        for url, folder in valid_entries:
            file.write(f"{url} {folder}\n")

    return valid_entries  # Ritorna la lista pulita


def save_entry(spotify_url, output_folder):
    """Scrive spotify_url e output_folder nel file data.dat, aggiungendo alla fine se esiste già."""
    with open(DATA_FILE, "a") as file:
        file.write(f"{spotify_url} {output_folder}\n")

def has_content(file):
    """Restituisce 1 se il file data.dat contiene dati, altrimenti 0."""
    if not os.path.exists(file):
        return 0  # Il file non esiste, quindi è vuoto

    # Controlla se il file ha contenuto
    with open(file, "r") as file:
        for line in file:
            if line.strip():  # Se c'è almeno una riga non vuota
                return 1
    return 3  # Il file è vuoto



def update():

    result = has_content(DATA_FILE)
    if result == 1:
        valid_entries = clean_entries()
        for url, folder in valid_entries:
            spotifydl(url, folder, 0)
        return
    elif result == 3:
        print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"The playlist database is corrupted.")
    elif result == 0:
        print(Fore.RYELLOW + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"No playlist has been downloaded yet.")
    else:
        print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"Unexpected error.")

def addmeta():
    # Richiedi il percorso del file all'utente
            file_path = input(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Enter the file path: ").strip()

            # Rimuovi eventuali virgolette iniziali e finali (sia " che ')
            if (file_path.startswith('"') and file_path.endswith('"')) or (file_path.startswith("'") and file_path.endswith("'")):
                file_path = file_path[1:-1]

            # Controlla se il file esiste
            if os.path.exists(file_path): 
                # Richiedi il link Spotify
                spotify_url = input(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Enter the Spotify link: ").strip()
                # Rimuovi virgolette se presenti
                if (spotify_url.startswith('"') and spotify_url.endswith('"')) or (spotify_url.startswith("'") and spotify_url.endswith("'")):
                    spotify_url = spotify_url[1:-1]

                # Ottieni il percorso della cartella in cui si trova il file
                directory_path = os.path.dirname(file_path)
                
                # Se il link contiene "track", procedi con l'estrazione dei metadati
                if "track" in spotify_url:
                    print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Extracting track information...")
                    track_info = get_spotify_single_track(spotify_url)
                    
                    # Passa il percorso completo del file a add_metadata_to_file
                    if add_metadata_to_file(file_path, track_info[0], directory_path):
                        print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Metadata added successfully.")
                    else:
                        print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Failed to add metadata.")
                else:
                    print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"{spotify_url} is not a valid track link.")
            else:
                print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"{file_path} does not exist")      
  

# === MAIN ===
def main():
    print("Welcome to SpotifyDl. To see the available commands, type help")
    while True:
        rss = input(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Enter command: ").strip().lower()
        if rss == "download" :
            spotify_url = input(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Enter the Spotify link: ").strip()
            output_folder = input(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Enter the destination folder: ").strip()
            spotifydl(spotify_url, output_folder, 1)
            print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Download complete!")
            log_file = os.path.join(output_folder, "log.txt")
            if has_content(log_file) == 1:
                print(Fore.YELLOW + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"An error may have occurred. Please check the log file. If there are incorrect or incomplete files, delete the file and enter the \\update command to attempt to repair the playlist. If the error persists, the track cannot be downloaded.")
        
        elif rss == "help":
            clear_terminal()
            commands = {
               "download": "Download any item from Spotify.",
                "update": "Automatically updates all downloaded playlists with the latest changes.",
                "addMeta": "Add the metadata of a Spotify song to a specific file",
                "exit": "Closes the program."
                }

            print("Comandi disponibili:")
            for command, description in commands.items():
                print(f"- {command}: {description}")

        elif rss == "exit":
            return
        elif rss == "update":
            update()
            print(Fore.GREEN + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + "Update complete!")
        elif rss == "addmeta":
            addmeta()
        else:
            print(Fore.RED + Style.BRIGHT + "[SpotifyDl] " + Style.RESET_ALL + f"{rss} is not a command")
            


if __name__ == "__main__":
    main()
