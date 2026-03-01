"""
downloader.py - Download audio from YouTube or process local MP3/WAV files
Uses yt-dlp for YouTube downloads
"""

import os
import subprocess
import shutil
import platform

def get_ffmpeg_path():
    """Returns the absolute path to ffmpeg executable, searching common locations if not in PATH."""
    # 1. Try if it's already in PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    # 2. Common WinGet installation path on Windows
    if platform.system() == "Windows":
        home = os.path.expanduser("~")
        winget_base = os.path.join(home, "AppData", "Local", "Microsoft", "WinGet", "Packages")
        if os.path.exists(winget_base):
            for root, dirs, files in os.walk(winget_base):
                if "ffmpeg.exe" in files:
                    return os.path.join(root, "ffmpeg.exe")
    
    return "ffmpeg"  # Fallback to plain command


def download_from_youtube(url: str, output_dir: str) -> str:
    """
    Download audio from a YouTube URL and save as WAV file.
    
    Args:
        url: YouTube video URL
        output_dir: Directory to save the downloaded audio
        
    Returns:
        Path to the downloaded WAV file
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "input_audio.wav")
    
    # Remove existing file if present
    if os.path.exists(output_path):
        os.remove(output_path)
    
    print(f"📥 Downloading audio from YouTube...")
    print(f"   URL: {url}")
    
    cmd = [
        "yt-dlp",
        "-x",                          # Extract audio only
        "--audio-format", "wav",       # Convert to WAV
        "--audio-quality", "0",        # Best quality
        "--ffmpeg-location", get_ffmpeg_path(), # Use the detected ffmpeg path
        "-o", output_path,             # Output path
        "--no-playlist",               # Don't download playlists
        "--quiet",                     # Less output
        "--progress",                  # Show progress
        url
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=False)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to download audio from YouTube: {e}")
    except FileNotFoundError:
        raise RuntimeError(
            "yt-dlp is not installed. Install it with: pip install yt-dlp"
        )
    
    # yt-dlp might save with a different extension, find the actual file
    if not os.path.exists(output_path):
        # Check for common alternative extensions
        base = os.path.join(output_dir, "input_audio")
        for ext in [".wav", ".webm", ".m4a", ".opus", ".mp3"]:
            alt_path = base + ext
            if os.path.exists(alt_path):
                # Convert to WAV if needed
                if ext != ".wav":
                    convert_to_wav(alt_path, output_path)
                    os.remove(alt_path)
                else:
                    output_path = alt_path
                break
        else:
            # Search for any audio file in the directory
            for f in os.listdir(output_dir):
                if f.startswith("input_audio"):
                    found = os.path.join(output_dir, f)
                    if found != output_path:
                        convert_to_wav(found, output_path)
                        os.remove(found)
                    break
    
    if not os.path.exists(output_path):
        raise RuntimeError("Download completed but audio file not found.")
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   ✅ Downloaded: {output_path} ({file_size:.1f} MB)")
    return output_path


def process_local_file(file_path: str, output_dir: str) -> str:
    """
    Process a local audio file (MP3, WAV, etc.) and convert to WAV if needed.
    
    Args:
        file_path: Path to the local audio file
        output_dir: Directory to save the processed audio
        
    Returns:
        Path to the WAV file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "input_audio.wav")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".wav":
        # Copy WAV directly
        print(f"📥 Copying WAV file...")
        shutil.copy2(file_path, output_path)
    else:
        # Convert to WAV using ffmpeg
        print(f"📥 Converting {ext} to WAV...")
        convert_to_wav(file_path, output_path)
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   ✅ Ready: {output_path} ({file_size:.1f} MB)")
    return output_path


def convert_to_wav(input_path: str, output_path: str):
    """Convert any audio file to WAV format using ffmpeg."""
    cmd = [
        get_ffmpeg_path(),
        "-i", input_path,
        "-ar", "44100",        # Sample rate
        "-ac", "2",            # Stereo
        "-y",                  # Overwrite output
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to convert audio to WAV: {e.stderr.decode()}")
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg is not installed. Install it from https://ffmpeg.org/download.html"
        )


def get_audio(source: str, output_dir: str) -> str:
    """
    Universal audio input handler. Accepts YouTube URL or local file path.
    
    Args:
        source: YouTube URL or path to local audio file
        output_dir: Directory to save processed audio
        
    Returns:
        Path to the WAV audio file
    """
    # Check if source is a YouTube URL
    if any(domain in source for domain in [
        "youtube.com", "youtu.be", "youtube.com/watch", "youtube.com/shorts"
    ]):
        return download_from_youtube(source, output_dir)
    else:
        return process_local_file(source, output_dir)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <youtube_url_or_file_path>")
        sys.exit(1)
    
    result = get_audio(sys.argv[1], "./output/temp")
    print(f"\nResult: {result}")
