from discord.ext import commands

class AutoReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_responses = {}  # Store user responses

    @commands.command(name='addresponse')
    async def add_response(self, ctx, *, response):
        self.user_responses[ctx.author.id] = response
        await ctx.send(f"Response set to: {response}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        mentions = [mention for mention in message.mentions if mention.id in self.user_responses]
        for mention in mentions:
            response = self.user_responses[mention.id]
            await message.channel.send(response)

async def setup(bot):
    await bot.add_cog(AutoReply(bot))