import os
import re
import uuid
import yt_dlp
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from music_downloader.metadata_manager import apply_metadata_and_rename

def search_youtube(query):
    """Cerca un video su YouTube utilizzando yt-dlp."""
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
    """Scarica un video da YouTube come file audio e restituisce il file scaricato."""
    # Calcola il nome finale basato sul titolo originale
    from music_downloader.init import sanitize_filename
    final_name = sanitize_filename(track_info['name'])
    
    # Genera un nome temporaneo unico
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
        'outtmpl': str(temp_output_path),
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Il file scaricato sarà <temp_output_path>.mp3
    temp_file_with_ext = str(temp_output_path) + ".mp3"
    # Ora, applica i metadati e gestisci la rinomina tramite il modulo metadata_manager
    apply_metadata_and_rename(temp_file_with_ext, output_folder, track_info)
