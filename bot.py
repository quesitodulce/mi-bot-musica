import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from flask import Flask
from threading import Thread

# 1. Crear una mini página web interna para mantener el bot despierto en Render
app = Flask('')

@app.route('/')
def home():
    return "¡BotsitoChichero está vivo 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Configuración normal del bot de Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'extract_flat': False,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_warnings': True,
    'referer': 'https://youtube.com',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -headers "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

@bot.event
async def on_ready():
    print(f'¡Bot listo y conectado como {bot.user.name}!')

@bot.command(name='play')
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        await ctx.send("¡Debes estar en un canal de voz para pedir música!")
        return
    
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
        
    await ctx.send(f"🔍 Buscando `{search}` en SoundCloud...")
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
        
        # CORREGIDO DEFINITIVAMENTE: Extraer el primer elemento [0] de la lista de resultados
        if 'entries' in data:
            if len(data['entries']) > 0:
                data = data['entries'][0]
            else:
                await ctx.send("No se encontraron resultados en SoundCloud.")
                return
                
        url = data['url']
        title = data['title']
        
        ctx.voice_client.stop()
        player = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(player)
        await ctx.send(f"🎵 Reproduciendo ahora desde SoundCloud: **{title}**")
        
    except Exception as error_msg:
        await ctx.send("Ocurrió un error al intentar reproducir la canción.")
        print(f"Error interno: {error_msg}")

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 ¡Música detenida!")
    else:
        await ctx.send("No estoy en ningún canal de voz.")

# 3. Encender la web y el bot al mismo tiempo de forma correcta
if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    # REEMPLAZA AQUÍ TU TOKEN SEGURO MANTENIENDO LAS COMILLAS SIMPLES
    bot.run('MTU2OTE5MDYxMjg2NjA0ODAyMA.G1p60n._IOfVRJpiHHp2n9GPz3LfazA8M-8q6sYy5EnZ4')
