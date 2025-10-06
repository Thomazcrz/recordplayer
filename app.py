from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from pydub import AudioSegment
import os, time, requests, io, sys
from pathlib import Path

# --- 🔧 PATCH para Python 3.13 (audioop removido) ---
# Garante compatibilidade com pydub
try:
    import pyaudioop
    sys.modules["audioop"] = pyaudioop
except ImportError:
    sys.modules["audioop"] = None
# ---------------------------------------------------

load_dotenv()
app = Flask(__name__)

# 🔑 Variáveis de ambiente (Render Dashboard -> Environment)
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
MUSIC_MODEL = os.getenv("REPLICATE_MODEL_MUSIC")
VOICE_MODEL = os.getenv("REPLICATE_MODEL_VOICE")
PORT = int(os.getenv("PORT", "8000"))

# 🎛 Função genérica para chamar a API do Replicate
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

    # ⏳ Aguarda até 80 segundos a geração
    for _ in range(40):
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


# 🏠 Página inicial (interface HTML)
@app.route("/")
def index():
    return render_template("index.html")


# 🎵 Endpoint principal - geração de música/voz
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

    # 🎹 Gera instrumental
    if mode in ("instrumental", "combined"):
        music_url = call_replicate(MUSIC_MODEL, {"prompt": prompt, "duration": 60})
        result["instrumental"] = music_url

    # 🎤 Gera voz
    if mode in ("voice", "combined"):
        voice_payload = {
            "prompt": prompt,
            "voice_preset": "pt_speaker_" + ("male" if voice_type == "male" else "female"),
        }
        voice_url = call_replicate(VOICE_MODEL, voice_payload)
        result["voice"] = voice_url

    # 🎧 Combina instrumental + voz
    if mode == "combined" and result["instrumental"] and result["voice"]:
        try:
            music_data = requests.get(result["instrumental"]).content
            voice_data = requests.get(result["voice"]).content

            music = AudioSegment.from_file(io.BytesIO(music_data))
            voice = AudioSegment.from_file(io.BytesIO(voice_data))
            combined = music.overlay(voice)

            # Exporta o áudio final em WAV e MP3
            Path("static").mkdir(exist_ok=True)
            out_wav = "static/combined.wav"
            out_mp3 = "static/combined.mp3"

            combined.export(out_wav, format="wav")
            combined.export(out_mp3, format="mp3")

            result["combined"] = {
                "wav": f"/{out_wav}",
                "mp3": f"/{out_mp3}"
            }

        except Exception as e:
            result["error"] = str(e)

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
