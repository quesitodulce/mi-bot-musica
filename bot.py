# ================================================================
#  BotsitoChichero - Bot de musica Discord
#  Motor: ytmusicapi + InnerTube ANDROID_MUSIC (sin bloqueos)
#  Bot-Hosting Edition - 24/7 sin Flask
# ================================================================
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
from ytmusicapi import YTMusic

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ytmusic = YTMusic()

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
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

    await ctx.send(f"🔍 Buscando `{search}`...")

    try:
        search_results = ytmusic.search(search, filter="songs")
        if not search_results:
            await ctx.send("No se encontraron resultados.")
            return

        track = search_results[0]
        video_id = track['videoId']
        title = track['title']
        artists = ", ".join([a['name'] for a in track['artists']]) if track['artists'] else "Desconocido"
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(video_url, download=False))
        url = data['url']

        ctx.voice_client.stop()
        player = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(player)
        await ctx.send(f"🎵 Reproduciendo: **{title}** - *{artists}*")

    except Exception as error_msg:
        await ctx.send("❌ Error al reproducir la canción.")
        print(f"Error: {error_msg}")

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 ¡Música detenida!")
    else:
        await ctx.send("No estoy en ningún canal de voz.")

if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN", "")
    bot.run(TOKEN)
