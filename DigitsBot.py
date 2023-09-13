import os  # Import the OS module to interact with the operating system.
import discord  # Import the Discord library to interact with Discord.
from googleapiclient.discovery import build  # Import the Google API client to interact with Google services.
from discord.ext import commands  # Import commands from the Discord library to create bot commands.
import yt_dlp  # Import yt_dlp to download YouTube videos.
import asyncio  # Import asyncio for asynchronous programming.
from dotenv import load_dotenv  # Import load_dotenv to load environment variables from a .env file.

# Load the environment variables from the .env file.
load_dotenv()
# Get the Discord bot token from the environment variables.
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
# Get the YouTube API key from the environment variables.
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Create the bot object with default settings and a command prefix of '/'.
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Build the YouTube API client using the API key.
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Options for yt_dlp to download audio from YouTube videos.
YDL_OPTS = {
    'format': 'bestaudio/best',  # Choose the best audio format.
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',  # Use FFmpeg to extract audio.
        'preferredcodec': 'mp3',  # Save the audio as an mp3.
        'preferredquality': '128', # Quality of the sound
    }],
    'outtmpl': 'downloads/%(id)s.%(ext)s',  # Output template for saved files.
    'restrictfilenames': True,  # Restrict filenames to ASCII characters.
    'nocheckcertificate': True,  # Don't check SSL certificates.
    'ignoreerrors': False,  # Don't ignore errors.
    'quiet': True,  # Don't print messages to console.
    'no_warnings': True,  # Don't print warnings.
    'default_search': 'auto',  # Search for videos automatically.
    'nooverwrites': True,  # Don't overwrite existing files.
    'noplaylist': True,  # Don't download playlists, only individual videos.
}

# Run this when the bot is connected to Discord.
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')  # Print a message to console saying the bot is connected.

# Function to connect the bot to a voice channel.
async def get_voice_client(ctx):
    voice_client = ctx.guild.voice_client  # Get the voice client for the server.
    if not voice_client or not voice_client.is_connected():
        channel = ctx.author.voice.channel  # Get the voice channel of the message author.
        voice_client = await channel.connect()  # Connect to the voice channel.
    return voice_client  # Return the voice client.

# Function to download audio from a YouTube video.
async def download_audio(ctx, url):
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:  # Initialize yt_dlp with the specified options.
        info = ydl.extract_info(url, download=False)  # Get info about the video without downloading it.
        title = info.get('title', None)  # Get the title of the video.
        video_id = info.get('id', None)  # Get the ID of the video.
        filename = f"downloads/{video_id}.mp3"  # Create a filename based on the video ID.

        if not os.path.exists(filename):  # If the file doesn't already exist,
            try:
                ydl.download([url])  # download the audio.
            except yt_dlp.DownloadError as e:
                print(f"Error downloading video: {e}")
                await ctx.send(f"Error downloading audio: {e}")
                return None

    return filename  # Return the filename.

# Function to play audio in a voice channel.
async def play_audio(ctx, url):
    voice_client = await get_voice_client(ctx)  # Get the voice client.

    if voice_client.is_playing():  # If audio is already playing,
        voice_client.stop()  # stop it.

    audio_file = await download_audio(ctx, url)  # Download the audio.

    if audio_file is None:
        await ctx.send("Failed to download audio.")
        return

    # Function to run after the audio finishes playing.
    def after_playing(error):
        coro = voice_client.disconnect()  # Coroutine to disconnect from voice channel.
        fut = asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)  # Run the coroutine in the event loop.
        try:
            fut.result()  # Get the result of the coroutine.
        except:
            pass

    # Play the audio.
    voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=audio_file), after=after_playing)


# Command to search for and play a YouTube video's audio.
@bot.command(name='play')
async def play(ctx, *, search_query):
    # Search YouTube for videos matching the search query.
    search_response = youtube.search().list(q=search_query, part='id,snippet', maxResults=4, type='video').execute()

    # Build a list of video titles.
    video_list = ''
    for i, item in enumerate(search_response['items'], start=1):
        video_list += f"{i}. {item['snippet']['title']}\n"

    # Send the list to the Discord channel and ask for user choice.
    await ctx.send('Here are the top results:\n' + video_list + '\nPlease choose a video by replying with the number (1-4).')

    # Check if the response message is valid.
    def check(msg):
        return msg.author == ctx.author and msg.content.isdigit() and 1 <= int(msg.content) <= 4

    try:
        # Wait for the user to reply with their choice.
        user_choice = await bot.wait_for('message', check=check, timeout=30)

        # Get the video URL from the chosen option.
        chosen_index = int(user_choice.content) - 1
        chosen_video_url = f"https://www.youtube.com/watch?v={search_response['items'][chosen_index]['id']['videoId']}"

        # Play the audio from the chosen video.
        await play_audio(ctx, chosen_video_url)

    except asyncio.TimeoutError:
        # Send a message if the user doesn't reply in time.
        await ctx.send('No response received. Please try again.')

# Command to stop playing audio and disconnect the bot from the voice channel.
@bot.command(name="stop", help="Stops the currently playing audio and disconnects the bot from the voice channel.")
async def stop(ctx):
    voice_client = ctx.guild.voice_client  # Get the voice client for the server.
    if voice_client is not None:  # If the bot is in a voice channel,
        voice_client.stop()  # stop playing audio.
        await voice_client.disconnect()  # Disconnect from the voice channel.
        await ctx.send("Stopped playing and disconnected from the voice channel.")  # Send a confirmation message.
    else:
        await ctx.send("I'm not connected to a voice channel.")  # Send a messageif the bot is not in a voice channel.

# Start the bot using the token.
bot.run(DISCORD_BOT_TOKEN)  # This line actually starts the bot with the token you got from Discord.