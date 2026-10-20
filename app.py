import os, re, base64, requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def gemini_generate(prompt, audio=None, mime_type=None):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    parts = [{"text": prompt}]
    if audio:
        parts.insert(0, {"inline_data": {"mime_type": mime_type or "audio/mpeg",
                                         "data": base64.b64encode(audio).decode("utf-8")}})
    response = requests.post(url, json={"contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.2}}, timeout=180)
    if not response.ok:
        raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text[:500]}")
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError("The AI model returned no text. Try again with a shorter recording.")

def extract_video_id(url):
    patterns = [r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
                r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
                r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
                r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.route("/")
def home():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "ai_configured": bool(GEMINI_API_KEY)})
    


@app.post("/api/youtube-transcript")
def youtube_transcript():
    import time

    payload = request.get_json(silent=True) or {}
    video_id = extract_video_id(str(payload.get("url", "")).strip())

    if not video_id:
        return jsonify({"error": "Please enter a valid YouTube URL."}), 400

    api_key = os.getenv("YOUTUBE_TRANSCRIPT_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Add YOUTUBE_TRANSCRIPT_API_KEY in Render Environment."}), 500

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            "https://www.youtubetranscript.dev/api/v2/transcribe",
            headers=headers,
            json={
                "video": video_id,
                "mode": "auto",
                "language": "en",
                "format": {"timestamp": False, "paragraphs": False},
            },
            timeout=45,
        )

        if response.status_code == 401:
            return jsonify({
                "error": "API key rejected (401). Verify the key on YouTubeTranscript.dev's API Keys page and update it in Render."
            }), 502

        if response.status_code == 402:
            return jsonify({
                "error": "Transcript API credits are insufficient. Check your provider account."
            }), 502

        if response.status_code not in (200, 202):
            return jsonify({
                "error": f"Transcript provider HTTP {response.status_code}: {response.text[:250]}"
            }), 502

        result = response.json()
        status = result.get("status", "")
        data = result.get("data") or {}
        transcript = ((data.get("transcript") or {}).get("text") or "").strip()

        if status == "completed" and transcript:
            return jsonify({"transcript": transcript, "video_id": video_id})

        job_id = result.get("job_id")
        if status == "processing" and job_id:
            for _ in range(8):
                time.sleep(2)
                job_response = requests.get(
                    f"https://www.youtubetranscript.dev/api/v2/jobs/{job_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=20,
                )
                if job_response.status_code not in (200, 202):
                    break

                job = job_response.json()
                job_data = job.get("data") or {}
                transcript = ((job_data.get("transcript") or {}).get("text") or "").strip()

                if job.get("status") == "completed" and transcript:
                    return jsonify({"transcript": transcript, "video_id": video_id})

                if job.get("status") in ("failed", "requires_asr_confirmation"):
                    return jsonify({
                        "error": job.get("error") or "The provider could not transcribe this video."
                    }), 502

            return jsonify({
                "error": "Transcription is still processing. Please wait and try the URL again."
            }), 202

        return jsonify({
            "error": result.get("error") or "No transcript returned. Check the video's captions and API credits."
        }), 502

    except requests.Timeout:
        return jsonify({"error": "Transcript provider timed out. Please retry."}), 504
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not contact transcript provider: {exc}"}), 502
    except ValueError:
        return jsonify({"error": "Transcript provider returned invalid JSON."}), 502


@app.post("/api/transcribe-audio")
def transcribe_audio():
    file = request.files.get("audio")
    if not file:
        return jsonify({"error": "Choose an audio file first."}), 400
    raw = file.read()
    if not raw:
        return jsonify({"error": "The uploaded file is empty."}), 400
    if len(raw) > 18 * 1024 * 1024:
        return jsonify({"error": "For this demo, use an audio file smaller than 18 MB."}), 400
    mime = file.mimetype or "audio/mpeg"
    prompt = """Transcribe the supplied lecture audio as accurately as possible. Preserve technical terms, names, numbers and formulas. Use paragraph breaks. If a word is unclear, mark it [unclear] instead of guessing. Return only the transcript."""
    try:
        text = gemini_generate(prompt, audio=raw, mime_type=mime)
        return jsonify({"transcript": text})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

@app.post("/api/generate-notes")
def generate_notes():
    payload = request.json or {}
    transcript = payload.get("transcript", "").strip()
    language = payload.get("language", "English")
    detail = payload.get("detail", "Detailed")
    subject = payload.get("subject", "").strip() or "Lecture"
    if len(transcript) < 20:
        return jsonify({"error": "Please provide a longer transcript before generating notes."}), 400
    prompt = f"""
You are a careful university lecture note-taking assistant.
Create {detail.lower()} study notes from the lecture transcript below.
Subject/module: {subject}
Output language: {language}

Requirements:
- Do not invent facts, formulas, examples, or claims absent from the transcript.
- Keep important technical terms and equations; preserve numbers carefully.
- If the transcript is unclear or contradictory, label it "Please verify" rather than guessing.
- Organize using Markdown headings and bullet points.
- Include: Title, short overview, learning points, detailed notes, definitions/key terms,
  formulas/examples (only if present), and a final quick-revision summary.
- Add 5 revision questions with answers based only on the transcript.
- If the source lacks information for a section, say "Not explicitly covered in the transcript".
- Make the notes useful for an engineering student preparing for an exam.

TRANSCRIPT:
{transcript[:80000]}
"""
    try:
        notes = gemini_generate(prompt)
        return jsonify({"notes": notes})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
