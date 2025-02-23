This program enables you to download entire Spotify playlists, album or song as MP3 files quickly and efficiently.  

## Features  
- **Multi-threaded Downloads**: Download multiple songs simultaneously by configuring the number of threads, speeding up the process for large playlists.  
- **Customizable Coded**: Customizable music quality.  
- **Metadata Support**: Each MP3 file is saved with proper metadata (title, artist, album, etc.) for better organization.  
- **Playlist Update**: If you need to add some tracks from a playlist, just re-enter the link and folder, and the program will download only the new ones.

## Requirements  
- Spotify API credentials (Client ID and Client Secret).
  [spotify.com](https://developer.spotify.com/)
- Internet connection.  
- Required dependencies (detailed in the setup instructions below).  
- Python 
  [python.org](https://www.python.org/)

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
  
## Installation  
 
1. Clone this repository.
2. Configure Client Id, Client Secret, and Max Threads in .env file:
  Create a .env file in the same directory as your script and add the following variables
  ```env
  CLIENT_ID="your_spotify_client_id"
  CLIENT_SECRET="your_spotify_client_secret"
  MAX_THREADS=14  # Number of simultaneous downloads (adjust based on your PC's capability)
  PREFERRED_QUALITY=192 # 320, 256, 192, 160, 128 , 96, 64
  XDG_CACHE_HOME=./yt-cache
  ```
3. Run the program and enjoy your MP3 downloads!
  -You can simply open it in Visual Studio and run it in a dedicated terminal.
  -You can create a `spotifydl.bat` file like this:
  ```bat
  @echo off
  cd /d "C:\Scripts\SpotifyDowloader"
  setlocal
  if exist .env (
    for /f "usebackq delims=" %%a in (".env") do set %%a
  )
  python "MultiThreadsSpotify.py"
  endlocal

  ```
  Remember, this is an example; your path may be different; then you need to add the path you set to the system's PATH environment variable, and you will be able to simply type `spotifydl` in the terminal to start the program.

  ## Usage
  Once the Python script is installed correctly, simply run it. For help, you can type `help`. The available commands are as follows and perform the corresponding actions:

- **"download"**: Download any item from Spotify.
- **"update <playlist number>"**: Update a specific playlist using the number obtained from `list`. If you don't enter a number, all playlists will be updated automatically with the latest changes.
- **"list"**: Show a list of the downloaded playlists.
- **"addMeta"**: Add the metadata of a Spotify song to a specific file.
- **"settings"**: Edit the .env settings from the app.
- **"exit"**: Closes the program.

It takes some time for the program to find one or more songs (depending on your connection, whether the song is difficult to find, has restrictions, or is not very popular). Therefore, even if you see warnings related to the cache or other information, always wait for a final output, either an error or a success message.
