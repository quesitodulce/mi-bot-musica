
# ================================================================
#  BotsitoChichero - Bot de musica Discord
#  Motor: ytmusicapi + InnerTube ANDROID_MUSIC (sin bloqueos)
#  BotsitoChichero - Render Edition
#  Motor: ytmusicapi + InnerTube ANDROID_MUSIC
#  Sin publicidad | Sin Lavalink | Sin yt-dlp | 100% APIs
# ================================================================
import aiohttp
import asyncio
import os
import re
import random
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
TOKEN = os.environ.get("DISCORD_TOKEN", "")
# ----------------------------------------------------------------
#  Flask - keep-alive para Render
# ----------------------------------------------------------------
app = Flask("")
@app.route("/")
def home():
    return "BotsitoChichero esta vivo!"
@app.route("/health")
def health():
    return {"status": "ok"}, 200
def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
# ----------------------------------------------------------------
#  InnerTube - cliente ANDROID_MUSIC
#  El mismo endpoint que usa la app de YouTube Music en Android.
#  Mucho menos filtrado que el cliente web.
