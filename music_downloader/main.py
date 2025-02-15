import os
from concurrent.futures import ThreadPoolExecutor
from music_downloader.spotify_handler import (
    get_spotify_playlist_tracks,
    get_spotify_album_tracks,
    get_spotify_single_track,
    track_already_downloaded
)
from music_downloader.youtube_downloader import search_youtube, download_from_youtube
from music_downloader.init import clear_terminal

def process_track(track, output_folder):
    """Processa un singolo brano: controlla se è già presente (con metadati),
    altrimenti lo cerca su YouTube, lo scarica e imposta i metadati."""
    try:
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

def main():
    while True:
        spotify_url = input("Enter the Spotify link: ")
        output_folder = input("Enter the destination folder: ")

        if not output_folder:
            output_folder = "/app/downloads"

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        clear_terminal()
        print(f"The songs will be saved in: {output_folder}")

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
        max_threads = int(max_threads) if max_threads is not None else 4  

        with ThreadPoolExecutor(max_threads) as executor:
            for track in tracks:
                executor.submit(process_track, track, output_folder)
        
        clear_terminal()
        print("\nDownload complete!")
        again = input("Do you want to download another item? (y/n): ").strip().lower()
        if again != 'y':
            print("Exiting...")
            break

if __name__ == "__main__":
    main()
