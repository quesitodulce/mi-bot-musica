import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from flask import Flask
from threading import Thread

# 1. Mini página web interna para Render
app = Flask('')

@app.route('/')
def home():
    return "¡BotsitoChichero está vivo 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Configuración del bot de Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuración optimizada para evadir el bloqueo de "Sign in to confirm you're not a bot"
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_warnings': True,
    # Forzar el uso del cliente de Android de YouTube, el cual no pide captchas en servidores en la nube
    'extractor_args': {
        'youtube': {
            'player_client': ['android'],
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
    print(f'¡Bot listo y conectado como {bot.user.name}!')

@bot.command(name='play')
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        await ctx.send("¡Debes estar en un canal de voz para pedir música!")
        return
    
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
        
    await ctx.send(f"🔍 Buscando `{search}` de forma segura...")
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
        
        if 'entries' in data:
            if len(data['entries']) > 0:
                data = data['entries'][0]
            else:
                await ctx.send("No se encontraron resultados.")
                return
                
        url = data['url']
        title = data['title']
        
        ctx.voice_client.stop()
        player = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(player)
        await ctx.send(f"🎵 Reproduciendo ahora: **{title}**")
        
    except Exception as error_msg:
        await ctx.send("YouTube bloqueó la petición. Reintentando con motor alternativo...")
        print(f"Error detectado: {error_msg}")
        
        # RESPALDO: Si falla el cliente de Android, busca directo con un extractor genérico alternativo
        try:
            ALT_OPTIONS = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'default_search': 'scsearch', # Cambia a SoundCloud de respaldo automático
            }
            alt_ytdl = yt_dlp.YoutubeDL(ALT_OPTIONS)
            data = await loop.run_in_executor(None, lambda: alt_ytdl.extract_info(search, download=False))
            if 'entries' in data:
                data = data['entries'][0]
            url = data['url']
            title = data['title']
            
            ctx.voice_client.stop()
            player = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(player)
            await ctx.send(f"🎵 Reproduciendo desde motor alternativo: **{title}**")
        except Exception as alt_error:
            await ctx.send("Ambas plataformas bloquearon la canción por derechos de autor.")
            print(f"Error en respaldo: {alt_error}")

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
