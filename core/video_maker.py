"""
video_maker.py - Generate karaoke video using FFmpeg
Combines instrumental audio with synced lyrics subtitles into a video file
"""

import os
import subprocess
import json
import shutil
import platform

def get_ffmpeg_path():
    """Returns the absolute path to ffmpeg executable, searching common locations if not in PATH."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path: return ffmpeg_path
    if platform.system() == "Windows":
        home = os.path.expanduser("~")
        winget_path = os.path.join(home, "AppData", "Local", "Microsoft", "WinGet", "Packages")
        if os.path.exists(winget_path):
            for root, dirs, files in os.walk(winget_path):
                if "ffmpeg.exe" in files: return os.path.join(root, "ffmpeg.exe")
    return "ffmpeg"

def get_ffprobe_path():
    """Returns the absolute path to ffprobe executable, searching common locations if not in PATH."""
    ffp_path = shutil.which("ffprobe")
    if ffp_path: return ffp_path
    if platform.system() == "Windows":
        home = os.path.expanduser("~")
        winget_path = os.path.join(home, "AppData", "Local", "Microsoft", "WinGet", "Packages")
        if os.path.exists(winget_path):
            for root, dirs, files in os.walk(winget_path):
                if "ffprobe.exe" in files: return os.path.join(root, "ffprobe.exe")
    return "ffprobe"


def create_karaoke_video(instrumental_path: str, subtitle_path: str, 
                         output_path: str, 
                         bg_color: str = "#0f0c29",
                         video_width: int = 1920,
                         video_height: int = 1080,
                         font_dir: str = None) -> str:
    """
    Generate a karaoke video with instrumental audio and synced lyrics.
    
    Args:
        instrumental_path: Path to instrumental WAV file (no vocals)
        subtitle_path: Path to ASS subtitle file
        output_path: Path for the output MP4 video
        bg_color: Background color hex code
        video_width: Video width in pixels
        video_height: Video height in pixels
        font_dir: Optional directory containing custom fonts
        
    Returns:
        Path to the generated MP4 video
    """
    if not os.path.exists(instrumental_path):
        raise FileNotFoundError(f"Instrumental file not found: {instrumental_path}")
    if not os.path.exists(subtitle_path):
        raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    print(f"🎬 Generating karaoke video...")
    print(f"   Resolution: {video_width}x{video_height}")
    
    # Get audio duration
    duration = get_audio_duration(instrumental_path)
    print(f"   Duration: {duration:.0f} seconds ({duration/60:.1f} minutes)")
    
    # Build FFmpeg command
    # Create gradient background + burn ASS subtitles + add audio
    
    # Escape the subtitle path for FFmpeg filter (Windows paths need special handling)
    sub_path_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")
    
    # Build video filter with gradient background
    vf_filter = (
        f"drawbox=c={bg_color}:replace=1:t=fill,"
        f"drawtext=text='🎤':fontsize=30:fontcolor=white@0.3:x=30:y=30,"
        f"ass='{sub_path_escaped}'"
    )
    
    cmd = [
        get_ffmpeg_path(),
        "-y",                                   # Overwrite output
        "-f", "lavfi",                          # Generate video from filter
        "-i", f"color=c={bg_color}:s={video_width}x{video_height}:d={duration}:r=24",
        "-i", instrumental_path,                # Audio input
        "-vf", f"ass='{sub_path_escaped}'",     # Burn subtitles
        "-c:v", "libx264",                      # Video codec
        "-preset", "medium",                    # Encoding speed/quality trade-off
        "-crf", "23",                           # Quality (lower = better, 23 is good)
        "-c:a", "aac",                          # Audio codec
        "-b:a", "192k",                         # Audio bitrate
        "-shortest",                            # End at shortest stream
        "-pix_fmt", "yuv420p",                  # Compatibility
        output_path
    ]
    
    # If font directory specified, set FONTCONFIG_PATH
    env = os.environ.copy()
    if font_dir and os.path.exists(font_dir):
        env["FONTCONFIG_PATH"] = font_dir
    
    print(f"   Encoding video... (this may take 1-3 minutes)")
    
    try:
        process = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env
        )
    except subprocess.CalledProcessError as e:
        # Try alternative approach without ASS filter (simpler)
        print(f"   ⚠️ ASS filter failed, trying SRT-based approach...")
        return create_karaoke_video_simple(
            instrumental_path, subtitle_path, output_path,
            bg_color, video_width, video_height
        )
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg is not installed. Install it from https://ffmpeg.org/download.html"
        )
    
    if not os.path.exists(output_path):
        raise RuntimeError("Video encoding completed but output file not found.")
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   ✅ Karaoke video created!")
    print(f"   📁 File: {output_path}")
    print(f"   📦 Size: {file_size:.1f} MB")
    
    return output_path


def create_karaoke_video_simple(instrumental_path: str, subtitle_path: str, 
                                 output_path: str,
                                 bg_color: str = "#0f0c29",
                                 video_width: int = 1920,
                                 video_height: int = 1080) -> str:
    """
    Fallback: Generate a simpler karaoke video using subtitles filter.
    Used when ASS rendering has issues with complex text.
    """
    duration = get_audio_duration(instrumental_path)
    
    # Use subtitles filter instead of ass filter
    sub_path_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")
    
    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:s={video_width}x{video_height}:d={duration}:r=24",
        "-i", instrumental_path,
        "-vf", f"subtitles='{sub_path_escaped}'",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg video generation failed: {e.stderr}")
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   ✅ Karaoke video created (simple mode)!")
    print(f"   📁 File: {output_path}")
    print(f"   📦 Size: {file_size:.1f} MB")
    
    return output_path


def get_audio_duration(audio_path: str) -> float:
    """Get the duration of an audio file in seconds using ffprobe."""
    cmd = [
        get_ffprobe_path(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        audio_path
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError):
        # Fallback: estimate 4 minutes
        print("   ⚠️ Could not detect audio duration, estimating 4 minutes")
        return 240.0


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python video_maker.py <instrumental.wav> <subtitles.ass> [output.mp4]")
        sys.exit(1)
    
    instrumental = sys.argv[1]
    subtitles = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) > 3 else "./output/karaoke_output.mp4"
    
    create_karaoke_video(instrumental, subtitles, output)
