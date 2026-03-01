"""
transcriber.py - Sinhala speech transcription using OpenAI Whisper
Generates word-level timestamps for lyrics synchronization
"""

import os
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


def transcribe_sinhala(vocals_path: str, output_dir: str, model_size: str = "base") -> dict:
    """
    Transcribe Sinhala vocals using OpenAI Whisper with word-level timestamps.
    
    Args:
        vocals_path: Path to the vocals WAV file
        output_dir: Directory to save transcription results
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                    Larger = more accurate but slower
                    
    Returns:
        Dict with transcription data including segments with timestamps
    """
    if not os.path.exists(vocals_path):
        raise FileNotFoundError(f"Vocals file not found: {vocals_path}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📝 Transcribing Sinhala vocals...")
    print(f"   Model: whisper-{model_size}")
    print(f"   First run will download the model (~150MB for 'base')...")
    
    # Import whisper here to avoid slow import at module level
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "OpenAI Whisper is not installed. Install it with: pip install openai-whisper"
        )
    
    # Load the model
    print(f"   Loading Whisper model...")
    model = whisper.load_model(model_size)
    
    # Whisper uses ffmpeg under the hood. On Windows, if ffmpeg is not in PATH,
    # Whisper will throw a 'File not found' error. We ensure the detected ffmpeg 
    # directory is added to the system PATH for this process.
    ffmpeg_exe = get_ffmpeg_path()
    if os.path.isabs(ffmpeg_exe):
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        if ffmpeg_dir not in os.environ["PATH"]:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
            print(f"   🔧 Added FFmpeg to PATH: {ffmpeg_dir}")

    # Transcribe with Sinhala language and word timestamps
    print(f"   Transcribing... (this may take 1-3 minutes)")
    result = model.transcribe(
        vocals_path,
        language="si",                # Sinhala language code
        word_timestamps=True,         # Get word-level timing
        verbose=False
    )
    
    # Extract segments with timestamps
    segments = []
    for segment in result.get("segments", []):
        seg_data = {
            "id": segment["id"],
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"].strip(),
            "words": []
        }
        
        # Extract word-level timestamps if available
        for word in segment.get("words", []):
            seg_data["words"].append({
                "word": word["word"].strip(),
                "start": word["start"],
                "end": word["end"]
            })
        
        segments.append(seg_data)
    
    transcription = {
        "language": "si",
        "text": result.get("text", "").strip(),
        "segments": segments
    }
    
    # Save transcription to JSON
    json_path = os.path.join(output_dir, "transcription.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcription, f, ensure_ascii=False, indent=2)
    
    # Save plain text lyrics
    lyrics_path = os.path.join(output_dir, "lyrics.txt")
    with open(lyrics_path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(seg["text"] + "\n")
    
    num_segments = len(segments)
    total_words = sum(len(s["words"]) for s in segments)
    
    print(f"   ✅ Transcription complete!")
    print(f"   📄 Lines: {num_segments}")
    print(f"   📝 Words: {total_words}")
    print(f"   💾 Saved to: {json_path}")
    
    return transcription


def load_manual_lyrics(lyrics_text: str, segment_timestamps: list) -> dict:
    """
    Create transcription data from manually provided lyrics with timestamps.
    
    Args:
        lyrics_text: Multi-line string of lyrics (one line per segment)
        segment_timestamps: List of (start, end) tuples in seconds for each line
        
    Returns:
        Dict with transcription data
    """
    lines = [line.strip() for line in lyrics_text.strip().split("\n") if line.strip()]
    
    if len(lines) != len(segment_timestamps):
        raise ValueError(
            f"Number of lyrics lines ({len(lines)}) doesn't match "
            f"timestamps ({len(segment_timestamps)})"
        )
    
    segments = []
    for i, (line, (start, end)) in enumerate(zip(lines, segment_timestamps)):
        segments.append({
            "id": i,
            "start": start,
            "end": end,
            "text": line,
            "words": []  # No word-level timestamps for manual input
        })
    
    return {
        "language": "si",
        "text": "\n".join(lines),
        "segments": segments
    }


def load_lrc_file(lrc_path: str) -> dict:
    """
    Load lyrics from an LRC file format.
    
    LRC format example:
    [00:12.00]මේ ලෝකේ
    [00:15.50]ඔබ සමගින්
    
    Args:
        lrc_path: Path to the LRC file
        
    Returns:
        Dict with transcription data
    """
    import re
    
    if not os.path.exists(lrc_path):
        raise FileNotFoundError(f"LRC file not found: {lrc_path}")
    
    with open(lrc_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Parse LRC timestamps
    pattern = r'\[(\d{2}):(\d{2})\.(\d{2})\](.*)'
    matches = re.findall(pattern, content)
    
    segments = []
    for i, (minutes, seconds, centis, text) in enumerate(matches):
        start = int(minutes) * 60 + int(seconds) + int(centis) / 100
        text = text.strip()
        
        if not text:
            continue
        
        # End time is the start of the next segment (or +5s for last)
        if i + 1 < len(matches):
            next_m, next_s, next_c, _ = matches[i + 1]
            end = int(next_m) * 60 + int(next_s) + int(next_c) / 100
        else:
            end = start + 5.0
        
        segments.append({
            "id": len(segments),
            "start": start,
            "end": end,
            "text": text,
            "words": []
        })
    
    return {
        "language": "si",
        "text": "\n".join(s["text"] for s in segments),
        "segments": segments
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <vocals.wav> [model_size]")
        print("Model sizes: tiny, base, small, medium, large")
        sys.exit(1)
    
    model = sys.argv[2] if len(sys.argv) > 2 else "base"
    result = transcribe_sinhala(sys.argv[1], "./output/transcription", model)
    
    print(f"\n--- Transcription ---")
    for seg in result["segments"]:
        print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
