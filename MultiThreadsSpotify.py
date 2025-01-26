import os
from concurrent.futures import ThreadPoolExecutor
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import yt_dlp

def get_spotify_playlist_tracks(playlist_url):
    """Extract song titles and artist names from a Spotify playlist."""
    client_id = ""  # Enter your Spotify Client ID
    client_secret = ""  # Enter your Spotify Client Secret

    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
    
    # Extract the playlist ID from the URL (handling different Spotify URL formats)
    if "playlist" in playlist_url:
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
    else:
        raise ValueError("Invalid playlist URL")
    
    # Initialize a list to collect the tracks
    tracks = []
    offset = 0  # Offset for pagination

    while True:
        # Fetch a batch of tracks (up to 100 at a time)
        results = sp.playlist_tracks(playlist_id, offset=offset)
        
        # Add the fetched tracks to the list
        for item in results['items']:
            track = item['track']
            name = track['name']
            artists = ', '.join([artist['name'] for artist in track['artists'] if artist.get('name')])  # Check artist names

            # Avoid adding tracks without artists
            if artists:
                tracks.append(f"{name} - {artists}")
            else:
                print(f"Track without artists found: {name}")
        
        # Stop if fewer than 100 tracks are fetched, indicating the end
        if len(results['items']) < 100:
            break
        
        # Update the offset to fetch the next page of tracks
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

def download_from_youtube(url, output_folder):
    """Download a video from YouTube as an audio file."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def process_track(track, output_folder):
    """Process a single track: search on YouTube and download."""
    print(f"Searching: {track}")
    youtube_url = search_youtube(track)

    if youtube_url:
        print(f"Downloading from: {youtube_url}")
        download_from_youtube(youtube_url, output_folder)
    else:
        print(f"Not found on YouTube: {track}")

if __name__ == "__main__":
    playlist_url = input("Enter the Spotify playlist link: ")
    output_folder = input("Enter the destination folder: ")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print("Extracting tracks from the playlist...")
    tracks = get_spotify_playlist_tracks(playlist_url)

    print("\nDownloading tracks...")
    # Use a ThreadPoolExecutor to download in parallel
    max_threads = 14  # Number of simultaneous downloads (adjust based on your PC's capability)
    with ThreadPoolExecutor(max_threads) as executor:
        for track in tracks:
            executor.submit(process_track, track, output_folder)

    print("\nDownload complete!")
