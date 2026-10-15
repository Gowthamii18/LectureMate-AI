# LectureMate AI — Smart Interactive Lecture Companion

A student-project prototype for the project **Smart Interactive Lecture Companion and Automated Notes Generator using Multi-Modal Collaboration**.

## Features mapped to the six project objectives

1. **Audio-to-text:** upload an audio recording and ask Gemini to transcribe it.
2. **Lecture material extraction:** retrieve available YouTube captions; paste transcript text from slides/lecture material where needed.
3. **Speech + slide/text combination:** the transcript editor can combine speech text with copied slide text before note generation.
4. **Automated notes:** generate organized notes, definitions, formulas/examples when present, quick revision and five Q&As.
5. **Recorded + live lectures:** recorded YouTube/audio inputs and browser microphone transcription.
6. **Multilingual notes:** English, Telugu, Hindi, Tamil, Kannada and Malayalam output options.

## Important scope note

This is an MVP demonstration, not a claim of perfect accuracy. YouTube transcript retrieval works only when captions are accessible. Live speech recognition depends on browser support and may use the browser vendor's service. Uploaded audio uses the configured Gemini model. Slide/image OCR and automatic PDF export are future enhancements; for this demo, copy slide text into the transcript box to combine sources. Always verify names, formulas and figures.

## Run on Windows

1. Install Python 3.10+ from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Extract this ZIP, then open the extracted folder in VS Code.
3. Open VS Code Terminal (**Terminal → New Terminal**) and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

4. Get a Gemini API key from Google AI Studio: https://aistudio.google.com/apikey
5. Open `.env` in VS Code and replace `PASTE_YOUR_API_KEY_HERE` with your key. Do not share the key or upload `.env` to GitHub.
6. Run:

```powershell
python app.py
```

7. Open http://127.0.0.1:5000 in Chrome.

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

## Public access / deployment

To make it accessible to anyone, deploy the app to a Python host such as Render. Create a Web Service from the project repository, use build command `pip install -r requirements.txt`, start command `gunicorn app:app` (add `gunicorn` to requirements first), and set `GEMINI_API_KEY` as a secret environment variable in the host dashboard. Use HTTPS and never put API keys in frontend JavaScript. Free hosting can sleep or have usage limits. Do not upload private lecture recordings without permission.

## Demo plan (3–5 minutes)

1. Open the homepage and explain Recorded vs Live modes.
2. Paste a YouTube link that has captions, click **Get transcript**.
3. Add module/subject and choose language, then generate notes.
4. Show headings, definitions, formulas if present, revision Q&As.
5. Show the Live tab and microphone flow, or paste a prepared transcript if microphone recognition is unavailable.
6. Download the notes as Markdown.

## Suggested future enhancements for higher project weightage

- Upload lecture slides (PDF/PPT/images) and use OCR / vision extraction.
- Timestamped notes with links back to the lecture moment.
- Search across modules and save notes by subject/unit.
- Export as PDF/DOCX, flashcards, quizzes and exam-style questions.
- Speaker identification, glossary of technical terms, and confidence/uncertain-word flags.
- Latency measurement: record time-to-transcript, time-to-notes, input duration, and calculate real-time factor (processing time ÷ audio duration).
- User accounts, cloud database, and consent-aware recording controls.

## Architecture

Browser UI → Flask API → YouTube captions / Gemini transcription → transcript editor → Gemini note generation → copy/download.

For the current prototype, multimodal collaboration is represented by combining audio transcript with slide text in the editable transcript. Full automatic slide extraction should be implemented as a clearly documented next milestone.
