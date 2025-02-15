import os
import re
from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from music_downloader.init import sanitize_filename

def apply_metadata_and_rename(temp_file_with_ext, output_folder, track_info):
    """Imposta i metadati sul file scaricato e rinomina il file in base al titolo (e, in caso di conflitto, aggiunge l'autore)."""
    # Aggiunge i metadati
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
        error_file = os.path.join(output_folder, "Error.txt")
        if not os.path.exists(error_file):
            open(error_file, 'w').close()
        with open(error_file, 'a') as file:
            file.write(f"[ERROR] adding metadata to temporary file: {e}\n")

    # Calcola il nome finale
    final_name = sanitize_filename(track_info['name'])
    final_output_path = Path(output_folder) / final_name
    final_file_with_ext = str(final_output_path) + ".mp3"

    if not os.path.exists(final_file_with_ext):
        os.rename(temp_file_with_ext, final_file_with_ext)
    else:
        # Se il file esiste, usa un nome alternativo con titolo e artista
        alt_final_name = sanitize_filename(f"{final_name} - {track_info['artists']}")
        alt_final_output_path = Path(output_folder) / alt_final_name
        alt_final_file_with_ext = str(alt_final_output_path) + ".mp3"
        if not os.path.exists(alt_final_file_with_ext):
            os.rename(temp_file_with_ext, alt_final_file_with_ext)
            final_file_with_ext = alt_final_file_with_ext
        else:
            print(f"File already exists: {alt_final_file_with_ext}. Removing temporary file.")
            os.remove(temp_file_with_ext)

    # Controllo post-rinominazione: verifica che il nome del file corrisponda al titolo nei metadati
    try:
        if os.path.exists(final_file_with_ext):
            audio = MP3(final_file_with_ext, ID3=EasyID3)
            metadata_title = audio.get('title', [final_name])[0]
            sanitized_title = sanitize_filename(metadata_title)
            current_name = Path(final_file_with_ext).stem
            if sanitized_title != current_name:
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
        error_file = os.path.join(output_folder, "Error.txt")
        if not os.path.exists(error_file):
            open(error_file, 'w').close()
        with open(error_file, 'a') as file:
            file.write(f"[ERROR] Error in post-renaming check: {e}\n")
