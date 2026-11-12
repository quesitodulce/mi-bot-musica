import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import wavelink
import asyncio
from dotenv import load_dotenv

load_dotenv()

# ================================================================
# Servidor HTTP web integrado (Indispensable para Render)
# ================================================================
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot activo 24/7")

def run_web():
    port = int(os.environ.get("PORT", 3000))
    HTTPServer(("0.0.0.0", port), PingHandler).serve_forever()

threading.Thread(target=run_web, daemon=True).start()


# ================================================================
# Configuración del Bot
# ================================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

LAVALINK_NODES = [
    {"uri": "https://lavalinkv4.serenetia.com:443", "password": "https://dsc.gg/ajidevserver"},
    {"uri": "http://lavalinkv4.serenetia.com:80",   "password": "https://dsc.gg/ajidevserver"},
    {"uri": "https://lavalink.serenetia.com:443",   "password": "https://dsc.gg/ajidevserver"},
    {"uri": "http://lavalinkv4.serenetia.com:80",     "password": "https://dsc.gg/ajidevserver"},
]

# Colores del embed según la fuente
SOURCE_COLORS = {
    "SoundCloud":    0xff5500,
    "YouTube Music": 0xff0000,
    "YouTube":       0xff0000,
}


# ----------------------------------------------------------------
# Barra de progreso y formato de tiempo
# ----------------------------------------------------------------
def progress_bar(position_ms: int, length_ms: int, size: int = 15) -> str:
    if not length_ms:
        return "░" * size
    filled = int((position_ms / length_ms) * size)
    filled = max(0, min(size, filled))
    bar = "█" * filled + "░" * (size - filled)
    return bar


def fmt_time(ms: int) -> str:
    s = int(ms / 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ----------------------------------------------------------------
# Embed principal
# ----------------------------------------------------------------
def build_embed(track: wavelink.Playable, source: str,
                position_ms: int = 0, volume: int = 100,
                loop_mode: str = "off") -> discord.Embed:

    color = SOURCE_COLORS.get(source, 0x1db954)

    loop_icons = {"off": "▶", "one": "🔂", "all": "🔁"}
    loop_label = {"off": "Sin bucle", "one": "Repite canción", "all": "Repite cola"}

    dur_ms = track.length or 0
    bar = progress_bar(position_ms, dur_ms)
    pos_str = fmt_time(position_ms)
    dur_str = fmt_time(dur_ms)

    vol_icon = "🔇" if volume == 0 else "🔈" if volume < 30 else "🔉" if volume < 70 else "🔊"

    embed = discord.Embed(color=color)
    embed.set_author(name="Reproduciendo ahora")

    embed.description = (
        "**" + track.title + "**\n"
        "*" + (track.author or "Desconocido") + "*\n\n"
        "`" + bar + "`\n"
        "`" + pos_str + "` ─────────── `" + dur_str + "`"
    )

    embed.add_field(name=vol_icon + " Volumen", value="`" + str(volume) + "%`", inline=True)
    embed.add_field(name=loop_icons[loop_mode] + " Modo", value="`" + loop_label[loop_mode] + "`", inline=True)
    embed.add_field(name="Fuente", value="`" + source + "`", inline=True)

    if track.artwork:
        embed.set_thumbnail(url=track.artwork)

    embed.set_footer(text="Usa los botones de abajo para controlar la música  •  !help para ver comandos")
    return embed


def build_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎵 Comandos de BotsitoChichero",
        description="Todos los comandos empiezan con `!`\nTambién puedes usar los **botones** del reproductor.",
        color=0x1db954
    )
    embed.add_field(
        name="▶️  Reproducción",
        value=(
            "`!play <canción>` — Busca y reproduce\n"
            "`!p <canción>` — Atajo de play\n"
            "`!skip` / `!s` — Salta la canción actual\n"
            "`!pause` — Pausa\n"
            "`!resume` — Reanuda\n"
            "`!stop` — Detiene y desconecta"
        ),
        inline=False
    )
    embed.add_field(
        name="📋  Cola",
        value=(
            "`!queue` / `!q` — Ver canciones en cola\n"
            "`!play` mientras suena algo — Agrega a la cola"
        ),
        inline=False
    )
    embed.add_field(
        name="🔊  Audio",
        value=(
            "`!volume <0-100>` / `!vol` — Ajusta el volumen\n"
            "O usa los botones del reproductor"
        ),
        inline=False
    )
    embed.set_footer(text="BotsitoChichero • Bot de música para Discord")
    return embed


# ----------------------------------------------------------------
# Panel de control completo (Botones)
# ----------------------------------------------------------------
class PlayerView(discord.ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.current:
            await self.player.seek(0)
            await interaction.response.send_message("⏮️ Reiniciando canción...", ephemeral=True, delete_after=3)
        else:
            await interaction.response.send_message("No hay nada reproduciéndose.", ephemeral=True)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.paused:
            await self.player.pause(False)
            button.emoji = "⏸️"
            button.style = discord.ButtonStyle.primary
        else:
            await self.player.pause(True)
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.success
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.stop()
        await interaction.response.send_message("⏭️ Saltando...", ephemeral=True, delete_after=2)

    @discord.ui.button(emoji="🔁", label="Bucle", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        current = getattr(self.player, "loop_mode", "off")
        modes = ["off", "one", "all"]
        icons = ["🔁", "🔂", "🔀"]
        labels = ["Bucle", "x1", "Todo"]
        idx = (modes.index(current) + 1) % 3
        self.player.loop_mode = modes[idx]

        if modes[idx] == "one":
            self.player.queue.mode = wavelink.QueueMode.loop
        elif modes[idx] == "all":
            self.player.queue.mode = wavelink.QueueMode.loop_all
        else:
            self.player.queue.mode = wavelink.QueueMode.normal

        button.emoji = icons[idx]
        button.label = labels[idx]

        if self.player.current:
            source = getattr(self.player, "last_source", "")
            embed = build_embed(self.player.current, source, self.player.position,
                                self.player.volume, modes[idx])
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.queue.clear()
        await self.player.stop()
        await self.player.disconnect()
        self.stop()
        embed = discord.Embed(
            description="⏹️  Música detenida. ¡Hasta pronto!",
            color=0x555555
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(emoji="📋", label="Ver cola", style=discord.ButtonStyle.secondary, row=1)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = self.player.queue
        if not queue:
            await interaction.response.send_message("📋 La cola está vacía.", ephemeral=True)
            return
        lines = [
            "`" + str(i+1) + ".` **" + t.title + "** — " + (t.author or "?")
            for i, t in enumerate(list(queue)[:10])
        ]
        total = len(queue)
        footer = ("\n*... y " + str(total - 10) + " más*") if total > 10 else ""
        await interaction.response.send_message(
            "📋 **Cola (" + str(total) + " canciones):**\n" + "\n".join(lines) + footer,
            ephemeral=True
        )

    @discord.ui.button(emoji="🔀", label="Shuffle", style=discord.ButtonStyle.secondary, row=1)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.queue:
            self.player.queue.shuffle()
            await interaction.response.send_message("🔀 ¡Cola mezclada!", ephemeral=True, delete_after=3)
        else:
            await interaction.response.send_message("La cola está vacía.", ephemeral=True)

    @discord.ui.button(emoji="❓", label="Ayuda", style=discord.ButtonStyle.secondary, row=1)
    async def help_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=build_help_embed(), ephemeral=True)

    @discord.ui.button(emoji="🔉", label="-10%", style=discord.ButtonStyle.primary, row=2)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_vol = max(0, self.player.volume - 10)
        await self.player.set_volume(new_vol)
        for item in self.children:
            if getattr(item, "label", "") == "Vol":
                item.label = "Vol: " + str(new_vol) + "%"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Vol: 100%", style=discord.ButtonStyle.secondary, disabled=True, row=2)
    async def vol_display(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(emoji="🔊", label="+10%", style=discord.ButtonStyle.primary, row=2)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_vol = min(100, self.player.volume + 10)
        await self.player.set_volume(new_vol)
        for item in self.children:
            if getattr(item, "label", "") and "Vol:" in str(getattr(item, "label", "")):
                item.label = "Vol: " + str(new_vol) + "%"
        await interaction.response.edit_message(view=self)


# ----------------------------------------------------------------
# Eventos
# ----------------------------------------------------------------
@bot.event
async def on_ready():
    print("Bot listo: " + bot.user.name)
    nodes = [wavelink.Node(uri=n["uri"], password=n["password"]) for n in LAVALINK_NODES]
    try:
        await wavelink.Pool.connect(nodes=nodes, client=bot, cache_capacity=100)
    except Exception as e:
        print("Error Lavalink: " + str(e))


@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print("[Lavalink] Conectado: " + payload.node.uri)


@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackStartEventPayload):
    player: wavelink.Player = payload.player
    track: wavelink.Playable = payload.track

    if not hasattr(player, "text_channel") or not player.text_channel:
        return

    if hasattr(player, "now_playing_msg") and player.now_playing_msg:
        try:
            await player.now_playing_msg.delete()
        except Exception:
            pass

    source = getattr(player, "last_source", "")
    loop_mode = getattr(player, "loop_mode", "off")
    embed = build_embed(track, source, 0, player.volume, loop_mode)
    view = PlayerView(player)
    player.now_playing_msg = await player.text_channel.send(embed=embed, view=view)


@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    player: wavelink.Player = payload.player
    if not player.queue and not player.playing:
        if hasattr(player, "text_channel") and player.text_channel:
            await player.text_channel.send(
                "✅ Cola terminada. Me desconecto en **3 minutos** si no pones más música.", delete_after=30
            )
        await asyncio.sleep(180)
        if not player.playing and player.connected:
            await player.disconnect()


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return
    guild = member.guild
    voice_client = guild.voice_client
    if not voice_client:
        return
    channel = voice_client.channel
    members_in_channel = [m for m in channel.members if not m.bot]
    if len(members_in_channel) == 0:
        await asyncio.sleep(30)
        channel = voice_client.channel
        members_in_channel = [m for m in channel.members if not m.bot]
        if len(members_in_channel) == 0:
            await voice_client.disconnect()


# ----------------------------------------------------------------
# Comandos
# ----------------------------------------------------------------
@bot.command(name="play", aliases=["p"])
async def play(ctx: commands.Context, *, query: str):
    if not ctx.author.voice:
        await ctx.send("🎤 Entra a un canal de voz primero.")
        return

    if not wavelink.Pool.nodes:
        await ctx.send("❌ Lavalink no conectado.")
        return

    channel = ctx.author.voice.channel

    if not ctx.voice_client:
        try:
            wavelink.Pool.get_node()
        except Exception:
            await ctx.send("❌ Lavalink no está conectado. Revisa la consola del hosting.")
            return
        player: wavelink.Player = await channel.connect(cls=wavelink.Player)
        player.text_channel = ctx.channel
        player.now_playing_msg = None
        player.last_source = ""
        player.loop_mode = "off"
    else:
        player: wavelink.Player = ctx.voice_client
        if player.channel != channel:
            await player.move_to(channel)

    msg = await ctx.send("🔍 Buscando **" + query + "**...")

    tracks = None
    source_used = ""
    for source, label in [
        (wavelink.TrackSource.SoundCloud,    "SoundCloud"),
        (wavelink.TrackSource.YouTubeMusic, "YouTube Music"),
        (wavelink.TrackSource.YouTube,       "YouTube"),
    ]:
        try:
            result = await wavelink.Playable.search(query, source=source)
            if result:
                tracks = result
                source_used = label
                break
        except Exception as e:
            print("[" + label + "] " + str(e)[:80])

    try:
        await msg.delete()
    except Exception:
        pass

    if not tracks:
        await ctx.send("❌ No se encontró la canción.")
        return

    track = tracks[0] if isinstance(tracks, list) else tracks
    player.last_source = source_used

    if player.playing or player.paused:
        player.queue.put(track)
        await ctx.send(
            "📋 En cola `#" + str(len(player.queue)) + "`: **" +
            track.title + "** [" + source_used + "]",
            delete_after=10
        )
    else:
        await player.play(track)


@bot.command(name="skip", aliases=["s"])
async def skip(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.playing:
        await ctx.voice_client.stop()
        await ctx.send("⏭️ Saltada.", delete_after=5)


@bot.command(name="stop")
async def stop(ctx: commands.Context):
    if ctx.voice_client:
        ctx.voice_client.queue.clear()
        await ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Detenido.")


@bot.command(name="pause")
async def pause(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.playing:
        await ctx.voice_client.pause(True)
        await ctx.send("⏸️ Pausado.", delete_after=5)


@bot.command(name="resume")
async def resume(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.paused:
        await ctx.voice_client.pause(False)
        await ctx.send("▶️ Reanudando.", delete_after=5)


@bot.command(name="queue", aliases=["q"])
async def show_queue(ctx: commands.Context):
    if not ctx.voice_client:
        return
    queue = ctx.voice_client.queue
    if not queue:
        await ctx.send("📋 Cola vacía.")
        return
    lines = ["`" + str(i+1) + ".` **" + t.title + "** — " + (t.author or "?")
             for i, t in enumerate(list(queue)[:10])]
    await ctx.send("📋 **Cola:**\n" + "\n".join(lines))


@bot.command(name="help", aliases=["h", "ayuda"])
async def help_cmd(ctx: commands.Context):
    """Muestra todos los comandos del bot."""
    await ctx.send(embed=build_help_embed())


@bot.command(name="volume", aliases=["vol"])
async def volume(ctx: commands.Context, vol: int):
    if not ctx.voice_client:
        return
    vol = max(0, min(100, vol))
    await ctx.voice_client.set_volume(vol)
    await ctx.send("🔊 Volumen: `" + str(vol) + "%`", delete_after=5)


if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN", "")
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN no configurado")
    bot.run(TOKEN)
