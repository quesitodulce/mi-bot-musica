# BotsitoChichero - Bot de musica para Discord
# Usa Lavalink para evitar bloqueos de YouTube en Render.
# Arquitectura: Tu bot (Render) --wavelink--> Nodo Lavalink (IP limpia) --> YouTube/SC

import discord
from discord.ext import commands
import wavelink
import asyncio
import os
from flask import Flask
from threading import Thread

# --- Servidor web para mantener vivo en Render ---
app = Flask('')

@app.route('/')
def home():
    return "BotsitoChichero esta vivo!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Nodos Lavalink publicos ---
# Si uno falla, el bot intenta con el siguiente automaticamente.
# Actualiza la lista desde: https://lavalink.darrennathanael.com/
LAVALINK_NODES = [
    {
        "identifier": "Node-1",
        "uri": "https://lavalink.jirayu.net:13592",
        "password": "youshallnotpass",
    },
    {
        "identifier": "Node-2",
        "uri": "http://lavalink.oops.wtf:7000",
        "password": "op!",
    },
    {
        "identifier": "Node-3",
        "uri": "https://lavalink-v4.techpowerb.xyz:443",
        "password": "techpower",
    },
]

# --- Clase principal del bot ---
class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Conecta a los nodos Lavalink al iniciar."""
        nodes = []
        for n in LAVALINK_NODES:
            uri = os.environ.get(
                "LAVA_{}_URI".format(n["identifier"].upper().replace("-", "_")),
                n["uri"]
            )
            pwd = os.environ.get(
                "LAVA_{}_PASS".format(n["identifier"].upper().replace("-", "_")),
                n["password"]
            )
            nodes.append(wavelink.Node(identifier=n["identifier"], uri=uri, password=pwd))

        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

    async def on_ready(self):
        print("Bot listo: {} (ID: {})".format(self.user, self.user.id))

bot = MusicBot()

# --- Eventos Lavalink ---

@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print("Nodo Lavalink [{}] conectado y listo.".format(payload.node.identifier))

@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackStartEventPayload):
    """Manda un embed cuando empieza una cancion."""
    player: wavelink.Player = payload.player
    track: wavelink.Playable = payload.track

    if hasattr(player, "text_channel") and player.text_channel:
        embed = discord.Embed(
            title="Reproduciendo ahora",
            description="**{}**".format(track.title),
            color=discord.Color.green()
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        if track.author:
            embed.add_field(name="Artista", value=track.author, inline=True)
        if track.length:
            mins, secs = divmod(track.length // 1000, 60)
            embed.add_field(name="Duracion", value="{}:{:02d}".format(mins, secs), inline=True)
        await player.text_channel.send(embed=embed)

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    """Reproduce la siguiente cancion de la cola automaticamente."""
    player: wavelink.Player = payload.player
    if not player.queue.is_empty:
        next_track = player.queue.get()
        await player.play(next_track)
    else:
        if hasattr(player, "text_channel") and player.text_channel:
            await player.text_channel.send("Cola terminada. Pide mas canciones con !play")

# --- Comando: !play ---
@bot.command(name="play", aliases=["p"])
async def play(ctx: commands.Context, *, query: str):
    """Reproduce una cancion por nombre o link directo."""
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("Debes estar en un canal de voz!")

    player: wavelink.Player = ctx.voice_client

    # Conectar al canal de voz si no esta conectado
    if not player:
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        except Exception as e:
            return await ctx.send("No pude conectarme al canal: {}".format(e))

    # Guardar canal de texto para mensajes automaticos
    player.text_channel = ctx.channel
    player.autoplay = wavelink.AutoPlayMode.disabled

    msg = await ctx.send("Buscando `{}`...".format(query))

    tracks = None

    # Intento 1: YouTube Music
    try:
        tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTubeMusic)
    except Exception:
        pass

    # Intento 2: YouTube normal
    if not tracks:
        try:
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
        except Exception:
            pass

    # Intento 3: SoundCloud
    if not tracks:
        try:
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)
        except Exception:
            pass

    if not tracks:
        return await msg.edit(content="No encontre ninguna cancion con esa busqueda.")

    # Manejar playlist vs cancion individual
    if isinstance(tracks, wavelink.Playlist):
        added = await player.queue.put_wait(tracks)
        await msg.edit(content="Playlist **{}** agregada ({} canciones).".format(tracks.name, added))
    else:
        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)

        if player.playing:
            await msg.edit(content="**{}** agregado a la cola (posicion #{}).".format(track.title, player.queue.count))
        else:
            await msg.delete()

    # Empezar a reproducir si no esta reproduciendo
    if not player.playing:
        await player.play(player.queue.get())


# --- Comando: !queue ---
@bot.command(name="queue", aliases=["q", "cola"])
async def queue(ctx: commands.Context):
    """Muestra la cola de canciones."""
    player: wavelink.Player = ctx.voice_client
    if not player or not player.playing:
        return await ctx.send("No hay nada reproduciendose.")

    embed = discord.Embed(title="Cola de reproduccion", color=discord.Color.blue())

    if player.current:
        embed.add_field(
            name="Ahora",
            value="**{}**".format(player.current.title),
            inline=False
        )

    if player.queue.is_empty:
        embed.add_field(name="Cola", value="Vacia - usa !play para agregar mas.", inline=False)
    else:
        lista = []
        for i, track in enumerate(player.queue[:10], 1):
            lista.append("{}. {}".format(i, track.title))
        if len(player.queue) > 10:
            lista.append("... y {} mas".format(len(player.queue) - 10))
        embed.add_field(
            name="Cola ({} canciones)".format(player.queue.count),
            value="\n".join(lista),
            inline=False
        )

    await ctx.send(embed=embed)


# --- Comando: !skip ---
@bot.command(name="skip", aliases=["s", "next"])
async def skip(ctx: commands.Context):
    """Salta la cancion actual."""
    player: wavelink.Player = ctx.voice_client
    if not player or not player.playing:
        return await ctx.send("No hay nada reproduciendose.")
    await player.skip()
    await ctx.send("Cancion saltada.")


# --- Comando: !pause ---
@bot.command(name="pause")
async def pause(ctx: commands.Context):
    """Pausa la musica."""
    player: wavelink.Player = ctx.voice_client
    if player and player.playing:
        await player.pause(True)
        await ctx.send("Musica pausada. Usa !resume para continuar.")


# --- Comando: !resume ---
@bot.command(name="resume")
async def resume(ctx: commands.Context):
    """Continua la musica pausada."""
    player: wavelink.Player = ctx.voice_client
    if player and player.paused:
        await player.pause(False)
        await ctx.send("Musica reanudada!")


# --- Comando: !volume ---
@bot.command(name="volume", aliases=["vol"])
async def volume(ctx: commands.Context, vol: int):
    """Cambia el volumen (1-100)."""
    player: wavelink.Player = ctx.voice_client
    if not player:
        return await ctx.send("No estoy en ningun canal de voz.")
    vol = max(1, min(100, vol))
    await player.set_volume(vol)
    await ctx.send("Volumen: **{}%**".format(vol))


# --- Comando: !stop ---
@bot.command(name="stop", aliases=["dc", "leave"])
async def stop(ctx: commands.Context):
    """Detiene la musica y desconecta al bot."""
    player: wavelink.Player = ctx.voice_client
    if player:
        player.queue.clear()
        await player.disconnect()
        await ctx.send("Musica detenida, hasta luego!")
    else:
        await ctx.send("No estoy en ningun canal de voz.")


# --- Comando: !nowplaying ---
@bot.command(name="nowplaying", aliases=["np"])
async def nowplaying(ctx: commands.Context):
    """Muestra la cancion que se esta reproduciendo."""
    player: wavelink.Player = ctx.voice_client
    if not player or not player.current:
        return await ctx.send("No hay nada reproduciendose.")

    track = player.current
    embed = discord.Embed(
        title="Reproduciendo ahora",
        description="**{}**".format(track.title),
        color=discord.Color.green()
    )
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    if track.author:
        embed.add_field(name="Artista", value=track.author, inline=True)
    if track.length:
        mins, secs = divmod(track.length // 1000, 60)
        embed.add_field(name="Duracion", value="{}:{:02d}".format(mins, secs), inline=True)
    await ctx.send(embed=embed)


# --- Inicio ---
if __name__ == "__main__":
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

    token = os.environ.get("DISCORD_TOKEN", "TU_TOKEN_AQUI")
    bot.run(token)
