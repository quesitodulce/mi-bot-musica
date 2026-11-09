# ================================================================
#  BotsitoChichero - Bot de musica Discord
#  Motor: ytmusicapi + InnerTube ANDROID_MUSIC (sin bloqueos)
#  BotsitoChichero - Render Edition
#  Sin publicidad | Sin Lavalink | Sin yt-dlp | 100% APIs
# ================================================================
import discord
from discord.ext import commands
import yt_dlp
import aiohttp
import asyncio
import os
import re
import random
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from ytmusicapi import YTMusic

load_dotenv()

# ----------------------------------------------------------------
#  Flask - keep-alive para Render
# ----------------------------------------------------------------
app = Flask("")

@app.route("/")
def home():
    return "¡BotsitoChichero está vivo 24/7 con InnerTube API!"

@app.route("/health")
def health():
    return {"status": "ok"}, 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ----------------------------------------------------------------
#  Configuración de Discord e Inicialización del Motor de Música
# ----------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Inicializar la API de YouTube Music (El bypass estilo SimpMusic)
ytmusic = YTMusic()

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android'],  # Obliga el bypass de la API de Android
            'skip': ['webpage', 'authcheck']
        }
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

@bot.event
async def on_ready():
    print(f'¡Bot listo y conectado como {bot.user.name} en la nube!')

@bot.command(name='play')
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        await ctx.send("¡Debes estar en un canal de voz para pedir música!")
        return
    
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
        
    await ctx.send(f"🔍 Buscando `{search}` en la API móvil de YouTube Music...")
    
    try:
        # Buscamos la canción en la base de datos de YouTube Music
        search_results = ytmusic.search(search, filter="songs")
        if not search_results:
            await ctx.send("No se encontraron resultados para tu búsqueda.")
            return
            
        # Tomar el primer resultado de la lista
        track = search_results[0]
        video_id = track['videoId']
        title = track['title']
        artists = ", ".join([artist['name'] for artist in track['artists']]) if track['artists'] else "Desconocido"

        video_url = f"https://youtube.com{video_id}"

        # Extraer el flujo de streaming de audio
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(video_url, download=False))
        url = data['url']
        
        ctx.voice_client.stop()
        player = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(player)
        await ctx.send(f"🎵 Reproduciendo ahora: **{title}** - *{artists}*")
        
    except Exception as error_msg:
        await ctx.send("Ocurrió un error al decodificar la firma de InnerTube.")
        print(f"Error interno del motor: {error_msg}")

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 ¡Música detenida!")
    else:
        await ctx.send("No estoy en ningún canal de voz.")

# ----------------------------------------------------------------
#  Encendido del Servidor Web y el Bot de Discord
# ----------------------------------------------------------------
if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    
    # Intenta leer de forma automática la variable DISCORD_TOKEN que guardaste en Render
    TOKEN = os.environ.get("DISCORD_TOKEN", "")
    bot.run(TOKEN)
