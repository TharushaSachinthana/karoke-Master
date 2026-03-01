"""
lyrics_sync.py - Generate ASS subtitle files for karaoke-style lyrics display
Creates timed subtitles with Sinhala text and karaoke highlighting effects
"""

import os


def generate_ass_subtitles(transcription: dict, output_path: str, 
                           font_name: str = "Noto Sans Sinhala",
                           font_size: int = 48,
                           primary_color: str = "&H00FFFFFF",      # White
                           highlight_color: str = "&H0000FFFF",    # Yellow
                           outline_color: str = "&H00000000",      # Black outline
                           video_width: int = 1920,
                           video_height: int = 1080) -> str:
    """
    Generate an ASS subtitle file with karaoke-style lyrics.
    
    Args:
        transcription: Transcription dict with segments and timestamps
        output_path: Path to save the ASS file
        font_name: Font to use for Sinhala text
        font_size: Font size
        primary_color: Default text color (ASS format &HAABBGGRR)
        highlight_color: Highlighted/active text color
        outline_color: Text outline color
        video_width: Video width in pixels
        video_height: Video height in pixels
        
    Returns:
        Path to the generated ASS file
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    print(f"⏱️ Generating karaoke subtitles...")
    
    # ASS header
    ass_content = f"""[Script Info]
Title: Sinhala Karaoke
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{font_name},{font_size},{primary_color},{highlight_color},{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,30,30,60,1
Style: Title,{font_name},{int(font_size * 0.6)},&H00AAAAAA,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,8,30,30,30,1
Style: ActiveLine,{font_name},{int(font_size * 1.1)},{highlight_color},&H00FFFFFF,{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,30,30,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    segments = transcription.get("segments", [])
    
    if not segments:
        print("   ⚠️ No segments found in transcription!")
        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(ass_content)
        return output_path
    
    # Generate dialogue lines for each segment
    for i, segment in enumerate(segments):
        start_time = format_ass_time(segment["start"])
        end_time = format_ass_time(segment["end"])
        text = segment["text"]
        
        if not text:
            continue
        
        # If we have word-level timestamps, create karaoke effect
        words = segment.get("words", [])
        if words:
            # Build karaoke text with \k timing tags
            karaoke_text = ""
            for j, word in enumerate(words):
                # Duration in centiseconds
                if j + 1 < len(words):
                    duration = int((words[j + 1]["start"] - word["start"]) * 100)
                else:
                    duration = int((segment["end"] - word["start"]) * 100)
                
                duration = max(duration, 10)  # Minimum 0.1 second
                karaoke_text += f"{{\\kf{duration}}}{word['word']} "
            
            ass_content += (
                f"Dialogue: 0,{start_time},{end_time},Karaoke,,0,0,0,,"
                f"{karaoke_text.strip()}\n"
            )
        else:
            # Simple timed display without word-level highlighting
            # Show current line in highlight color
            ass_content += (
                f"Dialogue: 0,{start_time},{end_time},ActiveLine,,0,0,0,,"
                f"{text}\n"
            )
        
        # Show next line preview (dimmed, above current line)
        if i + 1 < len(segments):
            next_text = segments[i + 1]["text"]
            if next_text:
                ass_content += (
                    f"Dialogue: 0,{start_time},{end_time},Title,,0,0,0,,"
                    f"{next_text}\n"
                )
    
    # Write the ASS file
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write(ass_content)
    
    print(f"   ✅ Subtitles saved: {output_path}")
    print(f"   📝 Total lines: {len(segments)}")
    
    return output_path


def format_ass_time(seconds: float) -> str:
    """
    Convert seconds to ASS timestamp format (H:MM:SS.CC).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string like "0:01:23.45"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def generate_lrc_from_transcription(transcription: dict, output_path: str) -> str:
    """
    Generate an LRC lyrics file from transcription data.
    
    Args:
        transcription: Transcription dict with segments
        output_path: Path to save the LRC file
        
    Returns:
        Path to the generated LRC file
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    lines = []
    for segment in transcription.get("segments", []):
        start = segment["start"]
        minutes = int(start // 60)
        seconds = start % 60
        text = segment["text"]
        
        if text:
            lines.append(f"[{minutes:02d}:{seconds:05.2f}]{text}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    
    print(f"   ✅ LRC file saved: {output_path}")
    return output_path


if __name__ == "__main__":
    # Test with sample data
    sample_transcription = {
        "language": "si",
        "segments": [
            {"id": 0, "start": 5.0, "end": 10.0, "text": "මේ ලෝකේ ඔබ සමගින්", "words": []},
            {"id": 1, "start": 10.0, "end": 15.0, "text": "සැමදා ඔබ ලඟින්", "words": []},
            {"id": 2, "start": 15.0, "end": 20.0, "text": "ආදරේ මේ හදේ", "words": []},
        ]
    }
    
    generate_ass_subtitles(sample_transcription, "./output/test_karaoke.ass")
    generate_lrc_from_transcription(sample_transcription, "./output/test_lyrics.lrc")
    print("\n✅ Test subtitles generated!")
