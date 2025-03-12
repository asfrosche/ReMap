# bot2.py
import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Verify token exists
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN found in .env file!")

# Initialize the commands bot with proper intents
intents = discord.Intents.default()
intents.message_content = True  # Required for command handling
bot = commands.Bot(command_prefix='!', intents=intents)

# Remove default help command to use our custom one
bot.remove_command("help")

async def load_extensions():
    """Load all extensions/cogs"""
    # Load specific cogs
    extensions = [
        "cogs.location_manager",
        "cogs.game_manager",
        "cogs.help",
        "cogs.aux_battle"  
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f"Loaded extension: {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}: {e}")

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord"""
    print(f'Logged in as {bot.user.name}')
    
    # Load all extensions
    await load_extensions()
    print("All extensions loaded")
    
    # Re-register game views (this will be handled by game_manager cog)
    print(f'Bot is ready!')

@bot.command()
async def ping(ctx):
    """Simple command to check if the bot is responsive"""
    await ctx.send('Pong! 🏓')

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid argument: {error}")
    else:
        await ctx.send(f"An error occurred: {error}")
        print(f"Command error: {error}")

if __name__ == "__main__":
    bot.run(TOKEN)
