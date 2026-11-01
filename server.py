"""Local-only Korean-to-English AI translator for 1602 LCD (6-wire parallel, RS=7,E=8,D4-D7=9..12)."""
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


def translate(text: str, style: str):
    if DEMO:
        demo = {"안녕하세요": "Hello!", "화장실이 어디인가요": "Where is the restroom?", "물 한 잔 주세요": "May I have some water?"}
        return demo.get(text.strip().rstrip(".!?。"), "Hello! This is a demo translation.")
    from openai import OpenAI
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Create a .env file.")
    prompt_style = {"easy": "very simple everyday English", "polite": "polite and natural English", "standard": "natural conversational English"}.get(style, "natural conversational English")
    client = OpenAI()
    resp = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You translate Korean to English. Translate faithfully into " + prompt_style + ". "
            "Return ONLY the English translation; no explanations, no markdown, no labels. "
            "Avoid unnecessary length, but preserve the meaning."
        ),
        input=text,
        max_output_tokens=200,
    )
    result = resp.output_text.strip()
    if not result:
        raise RuntimeError("The translation service returned an empty response.")
    return result


@app.get("/")
def index():
    return send_from_directory(str(BASE / "static"), "index.html")


@app.get("/api/status")
def status():
    return jsonify({"demo": DEMO, "browser": BROWSER_SERIAL and not DEMO, "port": "simulation" if DEMO else PORT})


@app.post("/api/translate")
def api_translate():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    style = str(data.get("style", "standard"))
    if not text or len(text) > 300:
        return jsonify({"error": "Enter between 1 and 300 characters."}), 400
    if not DEMO:
        limited = rate_limited()
        if limited:
            return jsonify({"error": limited}), 429
    try:
        english = translate(text, style)
        pages = lcd_pages(english)
        hardware = send_lcd(pages)
        return jsonify({"korean": text, "english": english, "pages": pages, "hardware": hardware})
    except Exception as exc:
        # Translation may have succeeded but serial may have failed; report accurately.
        return jsonify({"error": str(exc), "english": locals().get("english", ""), "pages": locals().get("pages", [])}), 502


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
