import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from collections import deque
import asyncio
import os
from dico_token import Token

# Intents setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# YTDL options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'cookies_from_browser': 'chrome',  # 이 부분을 추가!
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.2):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')

    @classmethod
    async def from_url(cls, url, *, loop, stream=False):
        ydl_opts = ytdl_format_options.copy()
        ydl_opts['cookiefile'] = 'cookies.txt'  # 쿠키 파일 경로 추가
        
        ydl = youtube_dl.YoutubeDL(ytdl_format_options)
        info = ydl.extract_info(url, download=False)
        url2 = info['url']
        title = info.get('title')
        fmt = discord.FFmpegPCMAudio(url2, **ffmpeg_options)
        return cls(fmt, data=info)

class MusicPlayer:
    def __init__(self):
        self.queue = deque()
        self.current_song = None

    async def play_next(self, ctx):
        if self.queue:
            self.current_song = self.queue.popleft()
            ctx.voice_client.play(self.current_song, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), bot.loop))
            await ctx.send(f"현재 재생 중: {self.current_song.title}")
        else:
            self.current_song = None
            await ctx.send("플레이리스트가 비어 있습니다.")

music_player = MusicPlayer()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(name='명령어')
async def command_list(ctx):
    embed = discord.Embed(title="명령어 목록", description='', color=discord.Color.purple())
    embed.add_field(name='/입장', value='봇을 음성 채널에 입장시킵니다.', inline=False)
    embed.add_field(name='/퇴장', value='봇을 음성 채널에서 퇴장시킵니다.', inline=True)
    embed.add_field(name='/재생 유튜브 URL', value='유튜브 URL을 입력하여 음악을 재생하거나 플레이리스트에 등록합니다.', inline=False)
    embed.add_field(name='/일시정지', value='음악을 일시 정지합니다.', inline=False)
    embed.add_field(name='/재개', value='음악을 다시 재생합니다.', inline=False)
    embed.add_field(name='/다음', value='현재 재생 중인 음악을 중지하고 다음 음악을 재생합니다.', inline=False)
    embed.add_field(name='/플리', value='현재 플레이리스트에 등록된 음악 목록을 보여줍니다.', inline=False)
    await ctx.send(embed=embed)

@bot.command(aliases=['입장'])
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f"{channel} 채널에 입장했습니다!")
    else:
        await ctx.send("먼저 음성 채널에 접속해 주세요.")

@bot.command(aliases=['퇴장'])
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("봇이 음성 채널에서 퇴장했습니다.")
    else:
        await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다.")

async def play_next(ctx):
    """다음 곡을 재생"""
    if music_player.queue:
        next_song = music_player.queue.popleft()
        ctx.voice_client.play(next_song, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f"현재 재생 중: {next_song.title}")


@bot.command(aliases=["다음"])
async def skip(ctx):
    """현재 노래를 중단하고 다음 노래를 재생"""
    if not ctx.voice_client:
        await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다.")
        return

    if not music_player.queue:
        await ctx.send("플레이리스트에 재생할 노래가 없습니다.")
        return

    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()  # 현재 노래를 중단

    # 다음 노래 가져오기
    next_song = music_player.queue.popleft()

    # 다음 노래 재생
    ctx.voice_client.play(next_song, after=lambda e: asyncio.run_coroutine_threadsafe(music_player.play_next(ctx), bot.loop))
    await ctx.send(f"지금 재생 중: {next_song.title}")



@bot.command(name="재생")
async def play(ctx, *, url):
    """노래를 재생하고, 첫 번째 곡을 플레이리스트에 추가"""
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("먼저 음성 채널에 접속해 주세요.")
            return

    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        music_player.queue.append(player)

        if not ctx.voice_client.is_playing():
            await play_next(ctx)
        else:
            await ctx.send(f'플레이리스트에 "{player.title}"이(가) 추가되었습니다.')


@bot.command(name='플리')
async def playlist(ctx):
    if not music_player.queue:
        await ctx.send("플레이리스트가 비어 있습니다.")
        return

    playlist_info = "현재 플레이리스트:\n"
    for i, song in enumerate(music_player.queue, 1):
        playlist_info += f"{i}. {song.title}\n"
    await ctx.send(playlist_info)

@bot.command(name='일시정지')
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("음악이 일시 정지되었습니다.")
    else:
        await ctx.send("현재 음악이 재생되고 있지 않습니다.")

@bot.command(name='재개')
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("음악이 다시 재생됩니다.")
    else:
        await ctx.send("음악이 일시 정지 중이지 않거나 이미 재생 중입니다.")

bot.run(Token)