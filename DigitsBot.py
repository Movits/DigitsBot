import os # Import the OS module for file handling
import discord # Import Discord.py library
from googleapiclient.discovery import build # Import the Google API client
from discord.ext import commands # Import the commands extension for Discord.py
import yt_dlp # Import the yt-dlp library for downloading YouTube videos
import asyncio # Import the asyncio library for asynchronous programming
from discord.utils import get # Import the 'get' utility from Discord.py
from discord import FFmpegPCMAudio # Import the FFmpegPCMAudio class for playing audio
from yt_dlp import YoutubeDL # Import the YoutubeDL class from yt-dlp
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

voice_client = None # Initialize a variable to store the bot's voice clients

# Options to be used by YoutubeDL to download the audio
YDL_OPTS = {
    'format': 'bestaudio/best',  # Audio quality
    'postprocessors': [{  # Audio processing options
    'key': 'FFmpegExtractAudio',  # Extract audio from video using FFmpeg
    'preferredcodec': 'mp3',  # Preferred audio codec
    'preferredquality': '192',  # Preferred audio quality
    }],
    'outtmpl': 'downloads/%(id)s.%(ext)s',  # Output file name format
    'restrictfilenames': True,  # Restrict file names to ASCII characters only
    'nocheckcertificate': True,  # Don't check SSL certificates
    'ignoreerrors': False,  # Don't ignore download errors
    'logtostderr': False,  # Don't log to standard error
    'quiet': True,  # Suppress console output
    'no_warnings': True,  # Suppress warnings
    'default_search': 'auto',  # Search for the best matching video
    'source_address': '0.0.0.0',  # Set the source address to 0.0.0.0
    'nooverwrites': True,  # Don't overwrite existing files
    'noplaylist': True,  # Don't download playlists
    'merge_output_format': 'mp3',  # Merge audio and video into an MP3 file
}

# Event to run when the bot is connected to Discord
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

# Function to join the voice channel the user is in
async def join_voice_channel(ctx):
    channel = ctx.author.voice.channel # Get the voice channel the user is in
    if ctx.voice_client is None: # If the bot isn't already in a voice channel
        await channel.connect() # Connect to the user's voice channel
    elif ctx.voice_client.channel != channel: # If the bot is in a different voice channel
        await ctx.voice_client.move_to(channel) # Move the bot to the user's voice channel

async def download_audio(ctx, url):
    # Create a YoutubeDL object with the specified options
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        # Extract information about the video at the given URL
        info = ydl.extract_info(url, download=False)
        # Get the video title and ID from the information
        title = info.get('title', None)
        video_id = info.get('id', None)
        # Construct the output file name from the title and ID
        filename = f"downloads/{title}-{video_id}.mp3"

        # Check if the file already exists
        if not os.path.exists(filename):
            # Download the audio from the given URL and save it to the output file
            ydl.download([url])

    # Return the filename of the downloaded audio file
    return filename

# Function to rename the downloaded audio file
def my_hook(d):
    if d['status'] == 'finished': # If the download is finished
        file_path = d['filename'] # Get the downloaded file's path
        file_ext = os.path.splitext(file_path)[1] # Get the file extension
        if file_ext.lower() == '.mp3': # If the file extension is '.mp3'
            new_file_path = os.path.splitext(file_path)[0] + '.1' + file_ext # Create a new file path with '.1' added to the name
            os.rename(file_path, new_file_path) # Rename the file with the new file path
            print(f'Renamed {file_path} to {new_file_path}') # Print the renaming information

async def disconnect_after_playback(voice_client):
    while voice_client.is_playing() or voice_client.is_paused():
        await asyncio.sleep(1)
    await voice_client.disconnect()

async def play_audio(ctx, url):
    global voice_client

    # Connect to the voice channel if not connected
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()

    # Stop any ongoing playback
    if voice_client.is_playing():
        voice_client.stop()

    # Download the audio
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'outtmpl': 'downloads/%(id)s.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Get the video info
        info = ydl.extract_info(url, download=False)

        # Get the audio file's file name and extension
        audio_file = os.path.join('downloads', f"{info['id']}.mp3")

        # Check if the audio file exists, if not, download it
        if not os.path.exists(audio_file):
            ydl.download([url])

    # Play the audio
    voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=audio_file))

    # Disconnect after playback
    await ctx.bot.loop.create_task(disconnect_after_playback(voice_client))

# Command to search for and play a video's audio from YouTube
@bot.command(name='play')
async def play(ctx, *, search_query):
    # Search YouTube for the specified query
    search_response = youtube.search().list(q=search_query, part='id,snippet', maxResults=4, type='video').execute()

    # Generate a list of search results
    video_list = ''
    for i, item in enumerate(search_response['items'], start=1):
        video_list += f"{i}. {item['snippet']['title']}\n"

     # Send the list of search results to the user
    await ctx.send('Here are the top results:\n' + video_list + '\nPlease choose a video by replying with the number (1-4).')

    # Function to check if the user's response is valid
    def check(msg):
        return msg.author == ctx.author and msg.content.isdigit() and 1 <= int(msg.content) <= 4

    try:
        # Wait for the user to choose a video from the list
        user_choice = await bot.wait_for('message', check=check, timeout=30)

        # Get the chosen video's URL
        chosen_index = int(user_choice.content) - 1
        chosen_video_url = f"https://www.youtube.com/watch?v={search_response['items'][chosen_index]['id']['videoId']}"

        # Join the user's voice channel
        await join_voice_channel(ctx)

        # Play the selected video's audio in the voice channel
        await play_audio(ctx, chosen_video_url)

    except asyncio.TimeoutError:
        # If the user didn't respond in time, send an error message
        await ctx.send('No response received. Please try again.')

# Command to stop playing audio and disconnect from the voice channel
@bot.command(name="stop", help="Stops the currently playing audio and disconnects the bot from the voice channel.")
async def stop(ctx):
    voice_client = ctx.guild.voice_client # Get the current voice client for the guild
    if voice_client is not None: # If the bot is connected to a voice channel
        voice_client.stop() # Stop the playback
        await voice_client.disconnect() # Disconnect from the voice channel
        await ctx.send("Stopped playing and disconnected from the voice channel.") # Send a confirmation message
    else:
        await ctx.send("I'm not connected to a voice channel.") # Send an error message if the bot is not connected to a voice channel

bot.run(DISCORD_BOT_TOKEN)