# 🎤 Sinhala Karaoke Master

An automated, AI-powered pipeline to generate high-quality Sinhala karaoke videos from any YouTube link or local audio file.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-green.svg)
![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)

## 🚀 Features

- **YouTube Integration**: Paste a YouTube link and let the magic happen.
- **Local File Support**: Upload your own MP3/WAV files for processing.
- **AI Vocal Separation**: Uses state-of-the-art AI (Demucs) to extract high-quality instrumental tracks.
- **Sinhala Transcription**: Automatically transcribes lyrics using OpenAI's Whisper.
- **Synced Subtitles**: Generates perfectly timed `.ass` and `.lrc` lyrics.
- **Automated Video Rendering**: Outputs a ready-to-use MP4 karaoke video with a background.

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Audio Processing**: Demucs (Vocal/Instrumental separation)
- **Transcription**: OpenAI Whisper (Speech-to-text)
- **Download**: yt-dlp
- **Subtitle Management**: pysubs2
- **Video Processing**: FFmpeg (via custom core logic)

## 📂 Project Structure

```text
karoke-Master/
├── core/               # Main logic for audio/video processing
├── static/             # Frontend assets (CSS, JS, Images)
├── templates/          # HTML templates
├── uploads/            # Temporary storage for uploaded files
├── output/             # Generated karaoke contents
├── app.py              # Flask entry point
└── requirements.txt    # Python dependencies
```

## ⚙️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/TharushaSachinthana/karoke-Master.git
   cd karoke-Master
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**:
   Ensure FFmpeg is installed on your system and added to your PATH.

## 🏃 Launching the App

Run the Flask application:

```bash
python app.py
```

Access the interface at: `http://localhost:5000`

## 🔒 License

Distributed under the MIT License. See `LICENSE` for more information.

---
Created by [Tharusha Sachinthana](https://github.com/TharushaSachinthana)
