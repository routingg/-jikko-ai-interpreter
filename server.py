"""Local-only Korean-to-English AI translator for 1602 LCD (6-wire parallel, RS=7,E=8,D4-D7=9..12)."""
import json
import os
import re
import threading
import time
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()
BASE = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(BASE / "static"), static_url_path="/static")
app.json.ensure_ascii = False
DEMO = os.getenv("DEMO_MODE", "0") == "1"
PORT = os.getenv("ARDUINO_PORT", "COM3")
BAUD = int(os.getenv("BAUD_RATE", "9600"))
PAGE_SECONDS = max(0.5, float(os.getenv("LCD_PAGE_SECONDS", "2.7")))
SERIAL_LOCK = threading.Lock()
# "server": this PC's Arduino via pyserial. "browser": translate only; the browser sends to LCD via Web Serial.
BROWSER_SERIAL = os.getenv("SERIAL_MODE", "server") == "browser"
RATE_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "6"))
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "300"))
if os.getenv("TRUST_PROXY") == "1":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
RATE_LOCK = threading.Lock()
recent_hits = {}
daily = {"day": "", "count": 0}


def rate_limited():
    """Per-IP sliding-window limit plus a global daily cap to bound API spend. Returns an error message or None."""
    now = time.time()
    ip = request.remote_addr or "?"
    with RATE_LOCK:
        today = time.strftime("%Y-%m-%d")
        if daily["day"] != today:
            daily["day"], daily["count"] = today, 0
        if daily["count"] >= DAILY_LIMIT:
            return "오늘 사용 가능한 번역 횟수를 모두 사용했습니다. 내일 다시 이용해 주세요."
        hits = [t for t in recent_hits.get(ip, []) if now - t < 60]
        if len(hits) >= RATE_PER_MIN:
            recent_hits[ip] = hits
            return "요청이 너무 빠릅니다. 잠시 후 다시 시도해 주세요."
        hits.append(now)
        recent_hits[ip] = hits
        daily["count"] += 1
        if len(recent_hits) > 5000:
            for k in [k for k, v in recent_hits.items() if not v or now - v[-1] >= 60]:
                del recent_hits[k]
    return None


def lcd_pages(message: str):
    """Wrap ASCII text without splitting words where practical into 16x2 pages."""
    # HD44780 basic Latin LCD: map unsupported chars to ASCII equivalents.
    import unicodedata
    clean = unicodedata.normalize("NFKD", message).encode("ascii", "ignore").decode()
    clean = re.sub(r"[^\x20-\x7e]", " ", clean)
    words = clean.split()
    lines = []
    current = ""
    for word in words:
        # Very long single words get split into 16-character pieces.
        if len(word) > 16:
            if current:
                lines.append(current)
                current = ""
            while len(word) > 16:
                lines.append(word[:16])
                word = word[16:]
            current = word
        elif not current:
            current = word
        elif len(current) + 1 + len(word) <= 16:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if not lines:
        lines = [""]
    return [[lines[i], lines[i + 1] if i + 1 < len(lines) else ""] for i in range(0, len(lines), 2)]


def send_lcd(pages):
    """Send every LCD page; do not claim hardware success without serial ACK."""
    if DEMO:
        return {"connected": False, "simulated": True, "pages_sent": 0}
    if BROWSER_SERIAL:
        return {"connected": False, "simulated": False, "browser": True, "pages_sent": 0}
    import serial
    with SERIAL_LOCK:
        with serial.Serial(PORT, BAUD, timeout=2, write_timeout=2) as board:
            time.sleep(2.2)  # UNO may reset on port open.
            board.reset_input_buffer()
            sent = 0
            for n, (a, b) in enumerate(pages):
                packet = (a + "|" + b + "\n").encode("ascii")
                board.write(packet)
                board.flush()
                reply = board.readline().decode("ascii", errors="replace").strip()
                if reply != "OK":
                    raise RuntimeError(f"LCD acknowledgment error on page {n + 1}: {reply!r}")
                sent += 1
                if n < len(pages) - 1:
                    time.sleep(PAGE_SECONDS)
            # Final page stays visible after the server returns.
            return {"connected": True, "simulated": False, "pages_sent": sent}


def llm(instructions: str, text: str, max_tokens: int = 200, as_json: bool = False):
    """One OpenAI call. With as_json, returns the parsed JSON object; otherwise the stripped text."""
    from openai import OpenAI
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Create a .env file.")
    extra = {"text": {"format": {"type": "json_object"}}} if as_json else {}
    resp = OpenAI().responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=instructions,
        # json_object format requires the word "JSON" in the input messages themselves, not only in instructions.
        input=f"Respond in JSON.\n\n{text}" if as_json else text,
        max_output_tokens=max_tokens,
        **extra,
    )
    out = resp.output_text.strip()
    if not out:
        raise RuntimeError("The AI service returned an empty response.")
    return json.loads(out) if as_json else out


def translate(text: str, style: str):
    if DEMO:
        demo = {"안녕하세요": "Hello!", "화장실이 어디인가요": "Where is the restroom?", "물 한 잔 주세요": "May I have some water?"}
        return demo.get(text.strip().rstrip(".!?。"), "Hello! This is a demo translation.")
    prompt_style = {"easy": "very simple everyday English", "polite": "polite and natural English", "standard": "natural conversational English"}.get(style, "natural conversational English")
    return llm(
        "You translate Korean to English. Translate faithfully into " + prompt_style + ". "
        "Return ONLY the English translation; no explanations, no markdown, no labels. "
        "Avoid unnecessary length, but preserve the meaning."
    , text)


def assistant_answer(question: str):
    """Kid-friendly assistant. Returns (korean answer for the web page, short English answer for the LCD)."""
    if DEMO:
        return "안녕! 나는 직코 AI 비서야. 무엇이든 물어봐!", "Hi! I am your AI helper. Ask me!"
    data = llm(
        "You are a friendly, safe AI helper for elementary school children in Korea. "
        "Answer the question truthfully in simple words. You cannot look up live data such as today's weather, "
        "news or time: say so briefly instead of guessing. Reply with a JSON object with exactly two string fields: "
        '"ko" (1-2 short Korean sentences) and "en" (the same answer in plain ASCII English, at most 60 characters, '
        "no emoji, no markdown).",
        question, max_tokens=300, as_json=True)
    ko, en = str(data.get("ko", "")).strip(), str(data.get("en", "")).strip()
    if not ko or not en:
        raise RuntimeError("The assistant returned an incomplete answer.")
    return ko, en[:120]


def guess_song(lyrics: str):
    """Guess a song from sung lyrics. Returns a dict with Korean/English title and artist, or found=False."""
    if DEMO:
        return {"found": True, "title_ko": "버터", "artist_ko": "방탄소년단", "title_en": "Butter", "artist_en": "BTS"}
    data = llm(
        "The user sang a few lyrics of a song and a speech recognizer transcribed them, so the text may contain "
        "recognition errors. Identify the song only if you are reasonably sure; never invent one. Reply with a JSON "
        'object: {"found": boolean, "title_ko": string, "artist_ko": string, "title_en": string, "artist_en": string}. '
        "title_en and artist_en must be plain ASCII (official English or romanized names). If not sure, set found to "
        "false and leave the other fields empty.",
        lyrics, max_tokens=200, as_json=True)
    keys = ("title_ko", "artist_ko", "title_en", "artist_en")
    out = {k: str(data.get(k, "")).strip() for k in keys}
    out["found"] = bool(data.get("found")) and bool(out["title_en"])
    return out


@app.get("/")
def index():
    return send_from_directory(str(BASE / "static"), "index.html")


@app.get("/api/status")
def status():
    return jsonify({"demo": DEMO, "browser": BROWSER_SERIAL and not DEMO, "port": "simulation" if DEMO else PORT})


def run_feature(compute):
    """Shared request flow: validate text, rate-limit, compute (result dict, LCD text), send to the LCD."""
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text or len(text) > 300:
        return jsonify({"error": "Enter between 1 and 300 characters."}), 400
    if not DEMO:
        limited = rate_limited()
        if limited:
            return jsonify({"error": limited}), 429
    result, pages = {}, []
    try:
        result, lcd_text = compute(text, data)
        pages = lcd_pages(lcd_text)
        hardware = send_lcd(pages)
        return jsonify({**result, "pages": pages, "hardware": hardware})
    except Exception as exc:
        # The AI step may have succeeded but serial may have failed; report accurately.
        return jsonify({"error": str(exc), "pages": pages, **result}), 502


@app.post("/api/translate")
def api_translate():
    def compute(text, data):
        english = translate(text, str(data.get("style", "standard")))
        return {"korean": text, "english": english}, english
    return run_feature(compute)


@app.post("/api/assistant")
def api_assistant():
    def compute(text, data):
        ko, en = assistant_answer(text)
        return {"question": text, "answer_ko": ko, "answer_en": en}, en
    return run_feature(compute)


@app.post("/api/song")
def api_song():
    def compute(text, data):
        song = guess_song(text)
        if song["found"]:
            lcd_text = f"{song['title_en']} - {song['artist_en']}" if song["artist_en"] else song["title_en"]
        else:
            lcd_text = "I am not sure. Sing more lyrics!"
        return {"lyrics": text, **song}, lcd_text
    return run_feature(compute)


@app.post("/api/lcd-test")
def lcd_test():
    pages = [["JIKKO SHIELD", "LCD IS READY"]]
    try:
        hardware = send_lcd(pages)
        return jsonify({"pages": pages, "hardware": hardware})
    except Exception as exc:
        return jsonify({"error": str(exc), "pages": pages}), 502


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"Running at http://{host}:{port} (demo={DEMO}, serial={PORT})")
    app.run(host=host, port=port, debug=False, threaded=True)
