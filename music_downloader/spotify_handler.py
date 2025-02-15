import os
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from colorama import Fore, Style
from pathlib import Path
from dotenv import load_dotenv
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

# Carica le variabili d'ambiente dal file .env
load_dotenv()
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

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

    # Pulizia del terminale e stampa informativa
    from music_downloader.init import clear_terminal
    clear_terminal()
    print(Fore.GREEN + Style.BRIGHT + f"You're downloading from: {playlist_name}" + Style.RESET_ALL)

    while True:
        results = sp.playlist_tracks(playlist_id, offset=offset)

        for item in results['items']:
            track = item['track']
            if track:
                name = track.get('name', 'Unknown Track')
                artists = ', '.join([artist.get('name', 'Unknown Artist') if artist.get('name') else 'Unknown Artist'
                                     for artist in track.get('artists', [])])
                album = track.get('album', {}).get('name', 'Unknown Album')
                track_number = track.get('track_number', None)
                release_date = track['album'].get('release_date', 'Unknown Year')
                year = release_date.split("-")[0]

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
    
    from music_downloader.init import clear_terminal
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
    
    from music_downloader.init import clear_terminal
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
    """Controlla se un brano è già presente nella cartella, verificando i metadati (titolo e artista)."""
    for mp3_file in Path(output_folder).glob("*.mp3"):
        try:
            audio = MP3(str(mp3_file), ID3=EasyID3)
            title = audio.get('title', [None])[0]
            artist = audio.get('artist', [None])[0]
            if title and artist:
                if title.strip().lower() == track['name'].strip().lower() and \
                   artist.strip().lower() == track['artists'].strip().lower():
                    return True
        except Exception:
            continue
    return False
