BotsitoChichero - Bot de música para Discord
Usa Lavalink (como lo hacen los bots profesionales) para evitar bloqueos de YouTube.
Arquitectura:
  - Tu bot (Python/Render) <──wavelink──> Nodo Lavalink (servidor externo con IP limpia)
  - El nodo Lavalink descarga/transmite el audio. YouTube no ve la IP de Render.
"""
import discord
from discord.ext import commands
import wavelink
import asyncio
import os
from flask import Flask
from threading import Thread
# ─── Servidor web para mantener vivo en Render ────────────────────────────────
app = Flask('')
@app.route('/')
def home():
    return "BotsitoChichero está vivo 🎵"
def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
# ─── Nodos Lavalink públicos ───────────────────────────────────────────────────
# Si uno falla, el bot intentará con el siguiente automáticamente.
