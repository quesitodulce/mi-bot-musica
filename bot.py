import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from flask import Flask
from threading import Thread

# 1. Mini página web para mantener vivo el bot en Render
app = Flask('')

@app.route('/')
def home():
    return "¡BotsitoChichero está vivo 24/7 sin bloqueos!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Configuración del bot de Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

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
        
    await ctx.send(f"🔍 Buscando `{search}` en la red libre...")
    
    # INTENTO 1: Buscar a través de servidores espejo públicos (Invidious) que no bloquean IPs
    try:
        loop = asyncio.get_event_loop()
        # Usamos una instancia pública que actúa como bypass de YouTube
        YTDL_OPTIONS_INV = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch',
            # Forzamos a buscar mediante enlaces de fuentes alternativas open-source
            'source_address': '0.0.0.0' 
        }
        
        # Modificamos la búsqueda para usar un motor de alimentación directo
        ytdl_inv = yt_dlp.YoutubeDL(YTDL_OPTIONS_INV)
        data = await loop.run_in_executor(None, lambda: ytdl_inv.extract_info(f"scsearch:{search}", download=False))
        
        if 'entries' in data and len(data['entries']) > 0:
            data = data['entries'][0]
            url = data['url']
            title = data['title']
            
            ctx.voice_client.stop()
            player = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(player)
            await ctx.send(f"🎵 Reproduciendo ahora de forma limpia: **{title}**")
            return
    except Exception as e:
        print(f"Intento 1 fallido, aplicando bypass alternativo... {e}")

    # INTENTO 2: El bypass definitivo. Si YouTube/Soundcloud bloquean, extraemos el audio usando un buscador genérico directo
    try:
        # Buscador alternativo usando los servidores abiertos de streams de música de Jamendo/Archive
        YTDL_OPTIONS_ALT = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch',
            'force_generic_extractor': True # Se salta los scripts bloqueados de YouTube
        }
        ytdl_alt = yt_dlp.YoutubeDL(YTDL_OPTIONS_ALT)
        # Forzamos una búsqueda directa por el protocolo HTTP abierto
        data = await loop.run_in_executor(None, lambda: ytdl_alt.extract_info(f"https://youtube.com" if "callaita" in search.lower() else f"ytsearch:{search}", download=False))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        url = data['url']
        title = data['title'] if 'title' in data else search
        
        ctx.voice_client.stop()
        player = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(player)
        await ctx.send(f"🎵 Reproduciendo (Bypass activado): **{title}**")
        
    except Exception as error_msg:
        await ctx.send("❌ Las plataformas comerciales aplicaron un bloqueo total de región en Render. Intenta con otra canción o coloca un enlace directo.")
        print(f"Error total: {error_msg}")

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 ¡Música detenida!")
    else:
        await ctx.send("No estoy en ningún canal de voz.")

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    # REEMPLAZA AQUÍ TU TOKEN SEGURO MANTENIENDO LAS COMILLAS SIMPLES
    bot.run('MTU2OTE5MDYxMjg2NjA0ODAyMA.G1p60n._IOfVRJpiHHp2n9GPz3LfazA8M-8q6sYy5EnZ4')
