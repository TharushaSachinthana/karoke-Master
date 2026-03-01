"""
Sinhala Karaoke Maker - Web Application
========================================

Flask web interface for the karaoke maker.
Upload MP3 or paste YouTube URL → Get karaoke video!

Run with: python app.py
Open: http://localhost:5000
"""

import os
import time
import threading
import uuid
from flask import Flask, render_template, request, jsonify, send_file, url_for

from core.downloader import get_audio
from core.separator import separate_vocals
from core.transcriber import transcribe_sinhala
from core.lyrics_sync import generate_ass_subtitles, generate_lrc_from_transcription
from core.video_maker import create_karaoke_video

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload

# Store job progress
jobs = {}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


class KaraokeJob:
    """Track the progress of a karaoke generation job."""
    
    def __init__(self, job_id: str, source: str, source_type: str):
        self.job_id = job_id
        self.source = source
        self.source_type = source_type
        self.status = "queued"
        self.current_step = 0
        self.total_steps = 5
        self.step_name = "Waiting..."
        self.progress = 0
        self.error = None
        self.output_video = None
        self.output_instrumental = None
        self.output_lyrics = None
        self.start_time = time.time()
    
    def update(self, step: int, name: str):
        self.current_step = step
        self.step_name = name
        self.progress = int((step / self.total_steps) * 100)
        self.status = "processing"
    
    def complete(self, video_path: str, instrumental_path: str = None, lyrics_path: str = None):
        self.status = "complete"
        self.progress = 100
        self.step_name = "Done!"
        self.output_video = video_path
        self.output_instrumental = instrumental_path
        self.output_lyrics = lyrics_path
    
    def fail(self, error: str):
        self.status = "error"
        self.error = error
        self.step_name = f"Error: {error}"
    
    def to_dict(self):
        elapsed = time.time() - self.start_time
        return {
            "job_id": self.job_id,
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_name": self.step_name,
            "progress": self.progress,
            "error": self.error,
            "elapsed_seconds": round(elapsed, 1),
            "has_video": self.output_video is not None
        }


def process_karaoke(job: KaraokeJob, whisper_model: str = "base"):
    """Background worker to process karaoke generation."""
    try:
        work_dir = os.path.join(OUTPUT_DIR, job.job_id, "workspace")
        final_dir = os.path.join(OUTPUT_DIR, job.job_id)
        os.makedirs(work_dir, exist_ok=True)
        
        # Step 1: Get audio
        job.update(1, "📥 Downloading / processing audio...")
        audio_path = get_audio(job.source, work_dir)
        
        # Step 2: Separate vocals
        job.update(2, "🎼 Separating vocals (AI processing)...")
        separated_dir = os.path.join(work_dir, "separated")
        tracks = separate_vocals(audio_path, separated_dir)
        
        # Step 3: Transcribe
        job.update(3, "📝 Transcribing Sinhala lyrics...")
        transcription_dir = os.path.join(work_dir, "transcription")
        transcription = transcribe_sinhala(
            tracks["vocals"], transcription_dir, model_size=whisper_model
        )
        
        # Step 4: Generate subtitles
        job.update(4, "⏱️ Generating synced subtitles...")
        subtitle_path = os.path.join(work_dir, "karaoke.ass")
        generate_ass_subtitles(transcription, subtitle_path)
        
        lrc_path = os.path.join(final_dir, "lyrics.lrc")
        generate_lrc_from_transcription(transcription, lrc_path)
        
        # Step 5: Create video
        job.update(5, "🎬 Rendering karaoke video...")
        video_path = os.path.join(final_dir, "karaoke_output.mp4")
        create_karaoke_video(tracks["instrumental"], subtitle_path, video_path)
        
        # Copy instrumental
        import shutil
        inst_path = os.path.join(final_dir, "instrumental.wav")
        shutil.copy2(tracks["instrumental"], inst_path)
        
        job.complete(video_path, inst_path, lrc_path)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        job.fail(str(e))


# ─── Routes ──────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/create", methods=["POST"])
def create_karaoke():
    """Start a new karaoke generation job."""
    job_id = str(uuid.uuid4())[:8]
    whisper_model = request.form.get("whisper_model", "base")
    
    # Handle YouTube URL
    youtube_url = request.form.get("youtube_url", "").strip()
    if youtube_url:
        job = KaraokeJob(job_id, youtube_url, "youtube")
        jobs[job_id] = job
        
        thread = threading.Thread(
            target=process_karaoke, args=(job, whisper_model)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({"job_id": job_id, "status": "started"})
    
    # Handle file upload
    if "audio_file" in request.files:
        file = request.files["audio_file"]
        if file.filename:
            # Save uploaded file
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"]:
                return jsonify({"error": "Unsupported file format"}), 400
            
            upload_path = os.path.join(UPLOAD_DIR, f"{job_id}{ext}")
            file.save(upload_path)
            
            job = KaraokeJob(job_id, upload_path, "file")
            jobs[job_id] = job
            
            thread = threading.Thread(
                target=process_karaoke, args=(job, whisper_model)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify({"job_id": job_id, "status": "started"})
    
    return jsonify({"error": "No YouTube URL or audio file provided"}), 400


@app.route("/api/status/<job_id>")
def job_status(job_id):
    """Get the current status of a karaoke generation job."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job.to_dict())


@app.route("/api/download/<job_id>/<file_type>")
def download_file(job_id, file_type):
    """Download a generated file (video, instrumental, lyrics)."""
    job = jobs.get(job_id)
    if not job or job.status != "complete":
        return jsonify({"error": "File not ready"}), 404
    
    if file_type == "video" and job.output_video:
        return send_file(job.output_video, as_attachment=True, 
                        download_name="karaoke_output.mp4")
    elif file_type == "instrumental" and job.output_instrumental:
        return send_file(job.output_instrumental, as_attachment=True,
                        download_name="instrumental.wav")
    elif file_type == "lyrics" and job.output_lyrics:
        return send_file(job.output_lyrics, as_attachment=True,
                        download_name="lyrics.lrc")
    
    return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🎤 SINHALA KARAOKE MAKER")
    print("=" * 50)
    print(f"🌐 Open in browser: http://localhost:5000")
    print(f"📁 Output folder:   {OUTPUT_DIR}")
    print("=" * 50 + "\n")
    
    app.run(debug=True, host="0.0.0.0", port=5000)
