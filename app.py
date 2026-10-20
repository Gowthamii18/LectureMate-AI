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
    import os
    import json
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
    from urllib.error import HTTPError, URLError

    url = (request.json or {}).get("url", "").strip()
    video_id = extract_video_id(url)

    if not video_id:
        return jsonify({"error": "Please enter a valid YouTube video URL."}), 400

    api_key = os.environ.get("YOUTUBE_TRANSCRIPT_API_KEY")
    if not api_key:
        return jsonify({"error": "YouTube transcript API key is not configured in Render."}), 500

    try:
        api_url = (
            "https://getyoutubetranscript.com/api/v1/transcript?"
            + urlencode({"v": video_id, "language": "en"})
        )

        req = Request(
            api_url,
            headers={"x-api-key": api_key},
            method="GET",
        )

        with urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        data = result.get("data", {})
        transcript = data.get("transcript", "")

        if not transcript.strip():
            return jsonify({"error": "No transcript was returned for this video."}), 400

        return jsonify({
            "transcript": transcript,
            "video_id": video_id
        })
        
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        return jsonify({
            "error": f"Transcript API HTTP {exc.code}: {details[:500]}"
        }), 502
        
    except (URLError, TimeoutError) as exc:
        return jsonify({
            "error": f"Could not connect to transcript service: {exc}"
        }), 502
    except Exception as exc:
        return jsonify({"error": f"Transcript retrieval failed: {exc}"}), 502
        
    
    url = (request.json or {}).get("url", "").strip()
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"error": "Please enter a valid YouTube video URL."}), 400
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi().fetch(video_id)
        text = " ".join(getattr(item, "text", str(item)) for item in transcript)
        if not text.strip():
            raise RuntimeError("No transcript text was returned.")
        return jsonify({"transcript": text, "video_id": video_id})
    except Exception as exc:
        return jsonify({"error": "Could not retrieve captions for this video. The video may not have captions, or YouTube may restrict access. Try uploading its audio or paste a transcript. Details: " + str(exc)[:250]}), 400

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
