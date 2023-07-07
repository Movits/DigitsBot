import os  # Import the OS module for file handling
import discord  # Import Discord.py library
from googleapiclient.discovery import build  # Import the Google API client
from discord.ext import commands  # Import the commands extension for Discord.py
import yt_dlp  # Import the yt-dlp library for downloading YouTube videos
import asyncio  # Import the asyncio library for asynchronous programming
from dotenv import load_dotenv

# Load tokens and API keys from environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Set up the bot with default intents and the desired command prefix
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Set up the YouTube API client with the provided API key
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Options to be used by YoutubeDL to download the audio
YDL_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'nooverwrites': True,
    'noplaylist': True,
}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

async def get_voice_client(ctx):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()
    return voice_client

async def download_audio(ctx, url):
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', None)
        video_id = info.get('id', None)
        filename = f"downloads/{video_id}.mp3"

        if not os.path.exists(filename):
            ydl.download([url])

    return filename

async def play_audio(ctx, url):
    voice_client = await get_voice_client(ctx)

    if voice_client.is_playing():
        voice_client.stop()

    audio_file = await download_audio(ctx, url)

    def after_playing(error):
        coro = voice_client.disconnect()
        fut = asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)
        try:
            fut.result()
        except:
            pass

    voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=audio_file), after=after_playing)

@bot.command(name='play')
async def play(ctx, *, search_query):
    search_response = youtube.search().list(q=search_query, part='id,snippet', maxResults=4, type='video').execute()

    video_list = ''
    for i, item in enumerate(search_response['items'], start=1):
        video_list += f"{i}. {item['snippet']['title']}\n"

    await ctx.send('Here are the top results:\n' + video_list + '\nPlease choose a video by replying with the number (1-4).')

    def check(msg):
        return msg.author == ctx.author and msg.content.isdigit() and 1 <= int(msg.content) <= 4

    try:
        user_choice = await bot.wait_for('message', check=check, timeout=30)

        chosen_index = int(user_choice.content) - 1
        chosen_video_url = f"https://www.youtube.com/watch?v={search_response['items'][chosen_index]['id']['videoId']}"

        await play_audio(ctx, chosen_video_url)

    except asyncio.TimeoutError:
        await ctx.send('No response received. Please try again.')

@bot.command(name="stop", help="Stops the currently playing audio and disconnects the bot from the voice channel.")
async def stop(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client is not None:
        voice_client.stop()
        await voice_client.disconnect()
        await ctx.send("Stopped playing and disconnected from the voice channel.")
    else:
        await ctx.send("I'm not connected to a voice channel.")

bot.run(DISCORD_BOT_TOKEN)