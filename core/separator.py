"""
separator.py - Vocal separation using Meta's Demucs v4
Separates audio into vocals and instrumental tracks
"""

import os
import shutil
import subprocess
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


def separate_vocals(audio_path: str, output_dir: str) -> dict:
    """
    Separate vocals from instrumental. Tries Demucs first, then falls back to FFmpeg.
    
    Args:
        audio_path: Path to the input WAV audio file
        output_dir: Directory to save separated tracks
        
    Returns:
        Dict with paths: {'vocals': '...', 'instrumental': '...'}
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🎼 Separating vocals from instrumental...")
    
    # Try Demucs first if installed
    try:
        import demucs
        return separate_vocals_demucs(audio_path, output_dir)
    except (ImportError, RuntimeError):
        print("   ⚠️ Demucs not found or failed to load. Using FFmpeg fallback...")
        return separate_vocals_ffmpeg(audio_path, output_dir)


def separate_vocals_demucs(audio_path: str, output_dir: str) -> dict:
    """Original Demucs implementation."""
    print(f"   Using AI Vocal Separation (Demucs)...")
    print(f"   This may take 2-5 minutes on CPU...")
    
    # Run Demucs with two-stems mode (vocals + no_vocals)
    cmd = [
        "python", "-m", "demucs",
        "--two-stems", "vocals",
        "-n", "htdemucs",
        "-o", output_dir,
        audio_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("Demucs execution failed")
    
    audio_name = os.path.splitext(os.path.basename(audio_path))[0]
    demucs_output = os.path.join(output_dir, "htdemucs", audio_name)
    
    v_src = os.path.join(demucs_output, "vocals.wav")
    i_src = os.path.join(demucs_output, "no_vocals.wav")
    
    v_dst = os.path.join(output_dir, "vocals.wav")
    i_dst = os.path.join(output_dir, "instrumental.wav")
    
    shutil.copy2(v_src, v_dst)
    shutil.copy2(i_src, i_dst)
    
    return {"vocals": v_dst, "instrumental": i_dst}


def separate_vocals_ffmpeg(audio_path: str, output_dir: str) -> dict:
    """
    Simple vocal removal using FFmpeg's stereotools (center removal).
    This is not as high quality as AI, but it is fast and always works.
    """
    print(f"   Using FFmpeg Center Isolation (Alternative)...")
    
    v_dst = os.path.join(output_dir, "vocals_isolated.wav")
    i_dst = os.path.join(output_dir, "instrumental.wav")
    
    # Isolation (Vocals) - Try to enhance center
    # Instrumental (No Vocals) - Use stereotools to reduce mid/center signal
    
    # Instrumental: Classic vocal removal by subtracting one channel from the other
    # This removes the center signal (where vocals usually reside)
    inst_cmd = [
        get_ffmpeg_path(), "-y", "-i", audio_path,
        "-af", "pan=stereo|c0=c0-c1|c1=c1-c0,compand=attacks=0:points=-30/-30|-20/-20|0/0",
        i_dst
    ]
    
    # Vocals: For FFmpeg fallback, we'll just use the original audio for transcription
    # as high-quality vocal extraction is not possible without AI.
    # Whisper is usually smart enough to handle background music.
    voc_cmd = [
        get_ffmpeg_path(), "-y", "-i", audio_path,
        "-ac", "1",
        v_dst
    ]
    
    try:
        subprocess.run(inst_cmd, check=True, capture_output=True)
        subprocess.run(voc_cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg vocal removal failed: {e.stderr.decode()}")
    
    return {"vocals": v_dst, "instrumental": i_dst}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python separator.py <audio_file.wav>")
        sys.exit(1)
    
    result = separate_vocals(sys.argv[1], "./output/separated")
    print(f"\nResults: {result}")
