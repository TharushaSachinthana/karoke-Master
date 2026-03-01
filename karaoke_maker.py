"""
Sinhala Karaoke Maker - Main Pipeline
=====================================

End-to-end pipeline that takes a YouTube URL or MP3 file
and produces a karaoke video with synced Sinhala lyrics.

Usage:
    python karaoke_maker.py <youtube_url_or_mp3_path> [whisper_model_size]
    
Examples:
    python karaoke_maker.py "https://www.youtube.com/watch?v=XXXXX"
    python karaoke_maker.py "my_song.mp3"
    python karaoke_maker.py "my_song.mp3" medium
"""

import os
import sys
import time
import shutil

from core.downloader import get_audio
from core.separator import separate_vocals
from core.transcriber import transcribe_sinhala
from core.lyrics_sync import generate_ass_subtitles, generate_lrc_from_transcription
from core.video_maker import create_karaoke_video


def run_pipeline(source: str, output_name: str = None, 
                 whisper_model: str = "base",
                 keep_intermediate: bool = True) -> str:
    """
    Run the complete karaoke maker pipeline.
    
    Args:
        source: YouTube URL or path to audio file
        output_name: Name for the output video (without extension)
        whisper_model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        keep_intermediate: Whether to keep intermediate files (vocals, etc.)
        
    Returns:
        Path to the generated karaoke MP4 video
    """
    start_time = time.time()
    
    # Setup directories
    base_dir = os.path.dirname(os.path.abspath(__file__))
    work_dir = os.path.join(base_dir, "output", "workspace")
    output_dir = os.path.join(base_dir, "output")
    
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    if not output_name:
        output_name = "karaoke_output"
    
    print("=" * 60)
    print("🎤 SINHALA KARAOKE MAKER")
    print("=" * 60)
    print(f"📂 Source: {source}")
    print(f"🧠 Whisper Model: {whisper_model}")
    print(f"📁 Output: {output_dir}")
    print("=" * 60)
    
    # ================================================
    # STEP 1: Download / Process Audio
    # ================================================
    print("\n" + "─" * 40)
    print("STEP 1/5: Audio Input")
    print("─" * 40)
    
    audio_path = get_audio(source, work_dir)
    
    step1_time = time.time()
    print(f"   ⏱️ Time: {step1_time - start_time:.1f}s")
    
    # ================================================
    # STEP 2: Separate Vocals from Instrumental
    # ================================================
    print("\n" + "─" * 40)
    print("STEP 2/5: Vocal Separation (Demucs)")
    print("─" * 40)
    
    separated_dir = os.path.join(work_dir, "separated")
    tracks = separate_vocals(audio_path, separated_dir)
    
    step2_time = time.time()
    print(f"   ⏱️ Time: {step2_time - step1_time:.1f}s")
    
    # ================================================
    # STEP 3: Transcribe Sinhala Lyrics
    # ================================================
    print("\n" + "─" * 40)
    print("STEP 3/5: Sinhala Transcription (Whisper)")
    print("─" * 40)
    
    transcription_dir = os.path.join(work_dir, "transcription")
    transcription = transcribe_sinhala(
        tracks["vocals"], 
        transcription_dir, 
        model_size=whisper_model
    )
    
    step3_time = time.time()
    print(f"   ⏱️ Time: {step3_time - step2_time:.1f}s")
    
    # ================================================
    # STEP 4: Generate Subtitles
    # ================================================
    print("\n" + "─" * 40)
    print("STEP 4/5: Generating Karaoke Subtitles")
    print("─" * 40)
    
    subtitle_path = os.path.join(work_dir, "karaoke.ass")
    generate_ass_subtitles(transcription, subtitle_path)
    
    # Also save LRC file
    lrc_path = os.path.join(output_dir, f"{output_name}.lrc")
    generate_lrc_from_transcription(transcription, lrc_path)
    
    step4_time = time.time()
    print(f"   ⏱️ Time: {step4_time - step3_time:.1f}s")
    
    # ================================================
    # STEP 5: Generate Karaoke Video
    # ================================================
    print("\n" + "─" * 40)
    print("STEP 5/5: Rendering Karaoke Video")
    print("─" * 40)
    
    video_path = os.path.join(output_dir, f"{output_name}.mp4")
    create_karaoke_video(
        tracks["instrumental"],
        subtitle_path,
        video_path
    )
    
    step5_time = time.time()
    print(f"   ⏱️ Time: {step5_time - step4_time:.1f}s")
    
    # ================================================
    # DONE!
    # ================================================
    total_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("🎉 KARAOKE VIDEO READY!")
    print("=" * 60)
    print(f"   🎬 Video:     {video_path}")
    print(f"   📝 Lyrics:    {lrc_path}")
    print(f"   🎵 Music:     {tracks['instrumental']}")
    print(f"   ⏱️ Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print("=" * 60)
    
    # Copy instrumental to output dir for easy access
    inst_output = os.path.join(output_dir, f"{output_name}_instrumental.wav")
    shutil.copy2(tracks["instrumental"], inst_output)
    
    return video_path


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    source = sys.argv[1]
    whisper_model = sys.argv[2] if len(sys.argv) > 2 else "base"
    
    # Generate output name from source
    if "youtube" in source or "youtu.be" in source:
        output_name = "karaoke_output"
    else:
        output_name = os.path.splitext(os.path.basename(source))[0] + "_karaoke"
    
    try:
        video_path = run_pipeline(source, output_name, whisper_model)
        print(f"\n✅ Open the video file to preview your karaoke:")
        print(f"   {video_path}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
