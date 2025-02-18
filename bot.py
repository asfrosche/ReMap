import os
import discord
from discord.ext import commands
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import logging
from collections import defaultdict
from common import get_continent

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Store user locations in memory
user_locations = {}

# Initialize Discord bot with specific intents
intents = discord.Intents.default()
intents.message_content = True  # Required for reading message content
intents.members = True  # Required for accessing member information
intents.guilds = True  # Required for guild/server information
bot = commands.Bot(command_prefix='!', intents=intents)
geolocator = Nominatim(user_agent="discord-map-bot")

@bot.event
async def on_ready():
    logger.info(f'Bot is ready. Logged in as {bot.user.name}')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Enabled intents: {bot.intents}')

@bot.command(name='setlocation')
async def set_location(ctx, target: discord.Member = None, *, location=None):
    try:
        # Check if this is setting location for another user
        if target:
            # Check if user has permission to set others' locations
            if not ctx.author.guild_permissions.administrator:
                await ctx.send("You need administrator permissions to set locations for other users.")
                return
            user = target
            if not location:
                await ctx.send("Please provide a location after the username. Usage: !setlocation @username <location>")
                return
        else:
            user = ctx.author
            location = location if location else target  # If no target, the first argument is the location

        if not location:
            await ctx.send("Please provide a location. Usage: !setlocation <location> or !setlocation @username <location>")
            return

        # Get location data
        logger.debug(f"Attempting to geocode location: {location}")
        geo_location = geolocator.geocode(location)

        if geo_location is None:
            await ctx.send("Sorry, I couldn't find that location. Please try again with a valid city or country.")
            return

        # Store user data
        user_locations[user.id] = {
            'name': user.name,
            'avatar': str(user.avatar.url) if user.avatar else None,
            'lat': geo_location.latitude,
            'lon': geo_location.longitude,
            'country': geo_location.address.split(', ')[-1]
        }

        logger.info(f"Location set for user {user.name}: {geo_location.address}")
        await ctx.send(f"Location for {user.name} set to: {geo_location.address}")

    except GeocoderTimedOut:
        await ctx.send("Sorry, the location service timed out. Please try again.")
    except Exception as e:
        logger.error(f"Error setting location: {str(e)}")
        await ctx.send("An error occurred while setting the location.")

@bot.command(name='map')
async def show_map(ctx):
    try:
        if not user_locations:
            await ctx.send("No locations have been set yet. Use `!setlocation <city/country>` to add your location to the map.")
            return

        # Get the website URL from environment or use a default
        website_url = os.environ.get('REPLIT_URL', 'https://your-repl-url.repl.co')
        await ctx.send(f"View the interactive map here: {website_url}")

    except Exception as e:
        logger.error(f"Error showing map: {str(e)}")
        await ctx.send("An error occurred while showing the map. Please try again later.")

@bot.command(name='locations')
async def show_locations(ctx):
    """Show all locations grouped by continent and country"""
    if not user_locations:
        await ctx.send("No locations have been set yet. Use `!setlocation <city/country>` to add your location.")
        return

    # Group users by continent and country
    continent_groups = defaultdict(lambda: defaultdict(list))
    for user_id, data in user_locations.items():
        continent = get_continent(data['country'])
        continent_groups[continent][data['country']].append(data['name'])

    # Create formatted message
    message = "**Current User Locations by Continent:**\n\n"
    for continent, countries in sorted(continent_groups.items()):
        total_users = sum(len(users) for users in countries.values())
        message += f"🌎 **{continent}** ({total_users} users):\n"

        for country, users in sorted(countries.items()):
            message += f"  🌍 **{country}** ({len(users)} users):\n"
            for user in sorted(users):
                message += f"    • {user}\n"
        message += "\n"

    await ctx.send(message)

def start_bot():
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("No Discord bot token found. Please set the DISCORD_BOT_TOKEN environment variable.")
        return

    try:
        logger.info("Starting Discord bot...")
        bot.run(token)
    except discord.errors.LoginFailure as e:
        logger.error(f"Failed to login to Discord: {str(e)}")
    except Exception as e:
        logger.error(f"An error occurred while running the bot: {str(e)}")