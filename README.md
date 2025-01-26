This program enables you to download entire Spotify playlists as MP3 files quickly and efficiently.  

## Features  
- **Multi-threaded Downloads**: Download multiple songs simultaneously by configuring the number of threads, speeding up the process for large playlists.  
- **Customizable Threads**: Adjust the number of concurrent downloads based on your system's resources.  
- **Metadata Support**: Each MP3 file is saved with proper metadata (title, artist, album, etc.) for better organization.  

## Requirements  
- A valid Spotify account (free or premium).  
- Internet connection.  
- Required dependencies (detailed in the setup instructions below).  

## Dependencies  

The following Python libraries are required to run this program:  
- `spotipy` (install via `pip install spotipy`)  
- `yt-dlp` (install via `pip install yt-dlp`)  

### Installing Dependencies  
Run the following command to install the required libraries:  
```bash
pip install spotipy yt-dlp
```
### Additional Tool  
- **FFmpeg**: Required for processing and converting audio files.
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
2. Configure the number of threads in the settings file or command-line arguments.  
3. Provide a Spotify playlist link.  
4. Run the program and enjoy your MP3 downloads!  
