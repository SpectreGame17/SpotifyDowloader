This program enables you to download entire Spotify playlists as MP3 files quickly and efficiently.  

## Features  
- **Multi-threaded Downloads**: Download multiple songs simultaneously by configuring the number of threads, speeding up the process for large playlists.  
- **Customizable Threads**: Adjust the number of concurrent downloads based on your system's resources.  
- **Metadata Support**: Each MP3 file is saved with proper metadata (title, artist, album, etc.) for better organization.  
- **Playlist Update**: If you need to add some tracks from a playlist, just re-enter the link and folder, and the program will download only the new ones.

## Requirements  
- Spotify API credentials (Client ID and Client Secret).
  https://developer.spotify.com/ 
- Internet connection.  
- Required dependencies (detailed in the setup instructions below).  

## Dependencies  

The following Python libraries are required to run this program:  
- `spotipy`   
- `yt-dlp`
- `mutagen`
- `ffmpeg-python`
- `python-dotenv`
- `colorama`

## Installing Dependencies  
 
Run the following command to install the required libraries:  
```bash
pip install -r requirements.txt
```
## Additional Tool  
 
**FFmpeg**: Required for processing and converting audio files:  
**On macOs** (using Homebrew)
```bash
brew install ffmpeg
```
**On Linux** (Debian/Ubuntu):
```bash
sudo apt update
sudo apt install ffmpeg
```
**On Windows**:
- Download the FFmpeg executable from the official site: https://ffmpeg.org/download.html.
- Add FFmpeg to your system's PATH environment variable (refer to the official guide for 
  instructions).
  
## Usage  
 
1. Clone this repository.
2. Configure Client Id, Client Secret, and Max Threads in .env file:
  Create a .env file in the same directory as your script and add the following variables
```env
CLIENT_ID="your_spotify_client_id"
CLIENT_SECRET="your_spotify_client_secret"
MAX_THREADS=14  # Number of simultaneous downloads (adjust based on your PC's capability)
PREFERRED_CODEC=mp3 # mp3,acc,m4a,opus,vorbis. if you use flac, wav or alac set PREFERRED_QUALITY to 0.
PREFERRED_QUALITY=192 # 320, 256, 192, 160, 128 , 96, 64
```
3. Run the program and enjoy your MP3 downloads!   
