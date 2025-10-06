import sys, types
import os, time, requests, io
from pathlib import Path

# --- 🔧 PATCH para Python 3.13 (audioop removido) ---
# Cria módulo falso para evitar erro do pydub
if "audioop" not in sys.modules:
    sys.modules["audioop"] = types.SimpleNamespace(
        add=lambda *a, **kw: None,
        mul=lambda *a, **kw: None,
        avg=lambda *a, **kw: None,
        rms=lambda *a, **kw: 0,
        max=lambda *a, **kw: 0,
        min=lambda *a, **kw: 0,
        tostereo=lambda *a, **kw: None,
        tomono=lambda *a, **kw: None
    )

from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from pydub import AudioSegment
# ----------------------------------------------------
load_dotenv()
app = Flask(__name__)

# Variáveis de ambiente (.env ou Render Dashboard)
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
MUSIC_MODEL = os.getenv("REPLICATE_MODEL_MUSIC")
VOICE_MODEL = os.getenv("REPLICATE_MODEL_VOICE")
PORT = int(os.getenv("PORT", "8000"))


# Função genérica para chamar a API do Replicate
def call_replicate(model, payload):
    url = f"https://api.replicate.com/v1/models/{model}/predictions"
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    r = requests.post(url, json={"input": payload}, headers=headers, timeout=60)
    r.raise_for_status()
    j = r.json()
    get_url = j.get("urls", {}).get("get")
    if not get_url:
        return None

    for _ in range(40):  # até ~80s de espera
        pr = requests.get(get_url, headers=headers, timeout=30)
        pj = pr.json()
        if pj.get("status") == "succeeded":
            out = pj.get("output")
            if isinstance(out, list):
                return out[0]
            elif isinstance(out, dict) and "audio" in out:
                return out["audio"]
        elif pj.get("status") in ("failed", "canceled"):
            break
        time.sleep(2)
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/generate")
def generate():
    data = request.get_json(force=True)
    mode = data.get("mode", "instrumental")
    prompt = data.get("prompt", "").strip()
    voice_type = data.get("voice", "male")

    if not REPLICATE_API_TOKEN:
        return jsonify(error="Faltou REPLICATE_API_TOKEN"), 500

    if not prompt:
        return jsonify(error="Campo 'prompt' é obrigatório"), 400

    result = {"instrumental": None, "voice": None, "combined": None}

    if mode in ("instrumental", "combined"):
        music_url = call_replicate(MUSIC_MODEL, {"prompt": prompt, "duration": 60})
        result["instrumental"] = music_url

    if mode in ("voice", "combined"):
        voice_payload = {
            "prompt": prompt,
            "voice_preset": "pt_speaker_" + ("male" if voice_type == "male" else "female"),
        }
        voice_url = call_replicate(VOICE_MODEL, voice_payload)
        result["voice"] = voice_url

    if mode == "combined" and result["instrumental"] and result["voice"]:
        try:
            music_data = requests.get(result["instrumental"]).content
            voice_data = requests.get(result["voice"]).content
            music = AudioSegment.from_file(io.BytesIO(music_data))
            voice = AudioSegment.from_file(io.BytesIO(voice_data))
            combined = music.overlay(voice)
            out_buf = io.BytesIO()
            combined.export(out_buf, format="wav")

            Path("static").mkdir(exist_ok=True)
            out_path = "static/combined.wav"
            with open(out_path, "wb") as f:
                f.write(out_buf.getbuffer())

            result["combined"] = f"/{out_path}"
        except Exception as e:
            result["error"] = str(e)

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

