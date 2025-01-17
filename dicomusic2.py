import discord
from discord.ext import commands
import yt_dlp as youtube_dl

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True  # Guilds (서버) 관련 이벤트 수신
intents.voice_states = True  # 음성 채널 상태 관련 이벤트 수신
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("봇이 온라인 상태입니다!")

@bot.command()
async def 입장(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        try:
            await channel.connect()
            await ctx.send(f"{channel}에 입장했습니다!")
            print(f"{channel}에 입장했습니다.")  # 디버깅 로그
        except Exception as e:
            await ctx.send("입장 중 오류가 발생했습니다.")
            print(f"입장 오류: {e}")
    else:
        await ctx.send("먼저 음성 채널에 접속해 주세요.")

@bot.command()
async def 퇴장(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("음성 채널에서 퇴장했습니다.")
        print("봇이 음성 채널에서 퇴장했습니다.")  # 디버깅 로그
    else:
        await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다.")

@bot.command()
async def 재생(ctx, url: str):
    if not ctx.voice_client:  # 봇이 음성 채널에 없으면 입장
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
        else:
            await ctx.send("먼저 음성 채널에 접속해 주세요.")
            return

    voice_client = ctx.voice_client

    # 유튜브에서 오디오 스트리밍
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'nocheckcertificate': True,
        'proxy': None,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            print("Audio URL:", audio_url)  # 디버깅: 오디오 URL 출력

        voice_client.play(
            discord.FFmpegPCMAudio(
                audio_url,
                executable="ffmpeg",  # 필요한 경우 전체 경로로 설정
                options="-loglevel panic"
            ),
            after=lambda e: print(f"Error: {e}" if e else "Playback finished.")
        )
        voice_client.source = discord.PCMVolumeTransformer(voice_client.source)
        voice_client.source.volume = 1.0  # 최대 볼륨
        await ctx.send(f"재생 중: {info['title']}")

    except Exception as e:
        print(f"오류 발생: {e}")
        await ctx.send(f"재생 중 오류가 발생했습니다: {e}")

bot.run('MTMyNTM2OTM4MzY0MzY0Mzk2NQ.GANHE8.Z6qH6Ah7fkpqRH5MQK6XXLowkgNWkSf-BG0q2I')
