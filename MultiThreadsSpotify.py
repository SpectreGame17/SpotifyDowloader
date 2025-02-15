import os
import re
import uuid
import threading
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
                print("Track is None, skipping...")

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
    for mp3_file in Path(output_folder).glob("*.mp3"):
        try:
            audio = MP3(str(mp3_file), ID3=EasyID3)
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
        print(f"Skipping, already exists or in processing: {track['name']} - {track['artists']}")
        return None

    in_processing.add(key)
    query = f"{track['name']} \"{track['artists']}\""
    print(f"Searching: {query}")
    youtube_url = search_youtube(query, output_folder)
    if not youtube_url:
        log_error(f"Not found on YouTube: {query}", output_folder)
        in_processing.remove(key)
        return None

    print(f"Downloading from: {youtube_url}")
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

    temp_file = str(temp_output_path) + ".mp3"
    if not os.path.exists(temp_file):
        log_error(f"Temporary file not found for {track['name']}", output_folder)
        in_processing.remove(key)
        return None

    return temp_file


# === FASE 2: Aggiunta metadati ===
def add_metadata_to_file(temp_file, track_info, output_folder):
    """
    Aggiunge i metadati al file audio.
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
        del audio  # Forza il rilascio della risorsa
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
    final_file = str(final_output_path) + ".mp3"

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
                    alt_final_file = str(alt_final_output_path) + ".mp3"
                    if not os.path.exists(alt_final_file):
                        os.rename(temp_file, alt_final_file)
                        final_file = alt_final_file
                    else:
                        # Fallback: aggiungi un suffisso numerico
                        i = 1
                        while os.path.exists(f"{final_output_path}-{i}.mp3"):
                            i += 1
                        final_file = f"{final_output_path}-{i}.mp3"
                        os.rename(temp_file, final_file)
            break
        except OSError as e:
            if hasattr(e, "winerror") and e.winerror == 32:
                print(f"File in use, retrying rename for {final_file} (attempt {attempt+1}/{max_retries})")
                time.sleep(0.5)
            else:
                raise e
    else:
        print(f"Failed to rename {temp_file} after {max_retries} attempts.")
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
                new_final_file = str(new_final_output_path) + ".mp3"
                if not os.path.exists(new_final_file):
                    os.rename(final_file, new_final_file)
                    final_file = new_final_file
                else:
                    print(f"Post-rename target already exists: {new_final_file}. Keeping original file.")
    except Exception as e:
        print(f"Error in post-renaming check for {track_info['name']}: {e}")
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
      - Elimina i file senza estensione .mp3.
      - Per ogni file .mp3, se mancano i metadati (title o artist), li imposta:
          * Usa il nome del file come title.
          * Imposta "Unknown" come artist se mancante.
    """
    for file in Path(output_folder).iterdir():
        if not file.is_file():
            continue
        if file.suffix.lower() != ".mp3":
            print(f"Deleting file without .mp3 extension: {file}")
            try:
                file.unlink()
            except Exception as e:
                log_error(f"Error deleting file {file}: {e}", output_folder)
        else:
            try:
                audio = MP3(str(file), ID3=EasyID3)
                title = audio.get('title', [None])[0]
                artist = audio.get('artist', [None])[0]
                changed = False
                if not title:
                    default_title = file.stem
                    print(f"File {file} missing title. Setting title to '{default_title}'")
                    audio['title'] = default_title
                    changed = True
                if not artist:
                    print(f"File {file} missing artist. Setting artist to 'Unknown'")
                    audio['artist'] = "Unknown"
                    changed = True
                if changed:
                    audio.save()
            except Exception as e:
                log_error(f"Error processing file {file}: {e}", output_folder)
                try:
                    file.unlink()
                except Exception as ex:
                    log_error(f"Error deleting file {file}: {ex}", output_folder)


# === MAIN ===
def main():
    while True:
        spotify_url = input("Enter the Spotify link: ").strip()
        output_folder = input("Enter the destination folder: ").strip()

        if not output_folder:
            output_folder = "/app/downloads"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        clear_terminal()
        print(f"The songs will be saved in: {output_folder}")

        # Estrae le tracce in base al tipo di URL
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
                        print(f"Downloaded: {track['name']} - Temp file: {temp_file}")
                except Exception as e:
                    log_error(f"Error downloading track {track['name']}: {e}", output_folder)
                    print(f"Error downloading track {track['name']}: {e}")

        print("\n=== PHASE 2: Adding metadata ===")
        with ThreadPoolExecutor(max_threads) as executor:
            future_to_item = {executor.submit(add_metadata_to_file, item["temp_file"], item["track"], output_folder): item for item in downloaded_items}
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    success = future.result()
                    if success:
                        print(f"Metadata added for: {item['track']['name']}")
                    else:
                        log_error(f"Error adding metadata for: {item['track']['name']}", output_folder)
                        print(f"Error adding metadata for: {item['track']['name']}")
                except Exception as e:
                    log_error(f"Error adding metadata for {item['track']['name']}: {e}", output_folder)
                    print(f"Error adding metadata for {item['track']['name']}: {e}")

        print("\n=== PHASE 3: Renaming files ===")
        with ThreadPoolExecutor(max_threads) as executor:
            future_to_item = {executor.submit(rename_file, item["temp_file"], item["track"], output_folder): item for item in downloaded_items}
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    final_path = future.result()
                    print(f"File for {item['track']['name']} renamed to: {final_path}")
                except Exception as e:
                    log_error(f"Error renaming file for {item['track']['name']}: {e}", output_folder)
                    print(f"Error renaming file for {item['track']['name']}: {e}")
                finally:
                    finalize_track_processing(item["track"])

        print("\n=== PHASE 4: Final verification ===")
        phase4_verification(output_folder)

        clear_terminal()
        print("\nDownload complete!")
        again = input("Do you want to download another item? (y/n): ").strip().lower()
        if again != 'y':
            print("Exiting...")
            break


if __name__ == "__main__":
    main()
