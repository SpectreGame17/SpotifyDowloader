import os
from concurrent.futures import ThreadPoolExecutor
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import yt_dlp
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from pathlib import Path

def get_spotify_playlist_tracks(playlist_url):
    """Extract song titles and artist names from a Spotify playlist."""
    client_id = ""  # Enter your Spotify Client ID
    client_secret = ""  # Enter your Spotify Client Secret

    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))

    if "playlist" in playlist_url:
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
    else:
        raise ValueError("Invalid playlist URL")

    tracks = []
    offset = 0

    while True:
        results = sp.playlist_tracks(playlist_id, offset=offset)

        for item in results['items']:
            track = item['track']
            if track:
                name = track.get('name', 'Unknown Track')
                artists = ', '.join([artist.get('name', 'Unknown Artist') for artist in track.get('artists', [])])
                album = track.get('album', {}).get('name', 'Unknown Album')
                track_number = track.get('track_number', None)

                if artists:
                    tracks.append({
                        'name': name,
                        'artists': artists,
                        'album': album,
                        'track_number': track_number
                    })
            else:
                print("Track is None, skipping...")

        if len(results['items']) < 100:
            break

        offset += 100

    return tracks

def search_youtube(query):
    """Search for a video on YouTube using yt-dlp."""
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch1',
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info and len(info['entries']) > 0:
            return info['entries'][0]['webpage_url']
        else:
            return None

def download_from_youtube(url, output_folder, track_info):
    """Download a video from YouTube as an audio file and set metadata."""
    file_name = f"{track_info['name']}"  
    output_path = Path(output_folder) / file_name  # Usa Path per unire i percorsi
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }
        ],
        'outtmpl': str(output_path),  # Converti il Path in stringa per yt-dlp
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Add metadata
    try:
        output_path_string = str(output_path) + ".mp3"
        audio = MP3((output_path_string), ID3=EasyID3)  # Converti il Path in stringa per mutagen
        audio['title'] = track_info['name']
        audio['artist'] = track_info['artists']
        audio['album'] = track_info['album']
        if track_info['track_number']:
            audio['tracknumber'] = str(track_info['track_number'])
        audio.save()
    except Exception as e:
        print(f"Error adding metadata to {file_name}: {e}")

def process_track(track, output_folder):
    """Process a single track: search on YouTube, download, and set metadata."""
    query = f"{track['name']} {track['artists']} audio"
    print(f"Searching: {query}")
    youtube_url = search_youtube(query)

    if youtube_url:
        print(f"Downloading from: {youtube_url}")
        download_from_youtube(youtube_url, output_folder, track)
    else:
        print(f"Not found on YouTube: {query}")

if __name__ == "__main__":
    playlist_url = input("Enter the Spotify playlist link: ")
    output_folder = input("Enter the destination folder: ")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print("Extracting tracks from the playlist...")
    tracks = get_spotify_playlist_tracks(playlist_url)

    print("\nDownloading tracks...")
    max_threads = 14
    with ThreadPoolExecutor(max_threads) as executor:
        for track in tracks:
            executor.submit(process_track, track, output_folder)

    print("\nDownload complete!")
