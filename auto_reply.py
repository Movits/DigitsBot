import os
from discord.ext import commands
import mysql.connector
from dotenv import load_dotenv
import asyncio

# Load environment variables from .env file
load_dotenv()

class AutoReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Establish a database connection using the environment variables
        self.db = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        self.cursor = self.db.cursor(buffered=True)

    @commands.command(name='addresponse')
    async def add_response(self, ctx, *, response):
        user_id = str(ctx.author.id)
        sql = "REPLACE INTO responses (user_id, response) VALUES (%s, %s)"
        val = (user_id, response)
        # Execute SQL command in an executor to avoid blocking
        await self.bot.loop.run_in_executor(None, self.cursor.execute, sql, val)
        self.db.commit()
        await ctx.send(f"Response set to: {response}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.author == self.bot.user:
            return

        mentions = [mention for mention in message.mentions if mention.id != self.bot.user.id]
        for mention in mentions:
            sql = "SELECT response FROM responses WHERE user_id = %s"
            val = (str(mention.id),)
            # Execute SQL command in an executor to avoid blocking
            await self.bot.loop.run_in_executor(None, self.cursor.execute, sql, val)
            result = self.cursor.fetchone()
            if result:
                await message.channel.send(result[0])

async def setup(bot):
    await bot.add_cog(AutoReply(bot))