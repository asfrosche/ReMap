# bot.py (fixed version)
import discord
from discord.ext import commands
import json
import os
from geopy.geocoders import Nominatim
import pycountry_convert as pc
import folium
from geopy.exc import GeocoderUnavailable
from io import BytesIO
from dotenv import load_dotenv

from discord.ui import View, Button, Select
import random


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

async def load_extensions():
    await bot.load_extension("aux_battle")
                             
# Storage setup
DATA_FILE = "locations.json"

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def load_data():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_continent(country_name):
    try:
        country_code = pc.country_name_to_country_alpha2(country_name)
        return pc.convert_continent_code_to_continent_name(
            pc.country_alpha2_to_continent_code(country_code)
        )
    except:
        return "Unknown"

@bot.command()
async def ping(ctx):
    await ctx.send('pPong! 🏓')

@bot.command()
@commands.has_permissions(administrator=True)
async def setloc(ctx, member: discord.Member, *, location):
    """Set a user's location (Admin only)"""
    geolocator = Nominatim(user_agent="geo_bot")
    try:
        loc = geolocator.geocode(location, addressdetails=True)
        if not loc:
            await ctx.send("Location not found!")
            return
            
        address = loc.raw.get('address', {})
        data = load_data()
        
        data[str(member.id)] = {
            "city": address.get('city', address.get('town', location)),
            "country": address.get('country', "Unknown"),
            "continent": get_continent(address.get('country', "Unknown")),
            "lat": loc.latitude,
            "lon": loc.longitude
        }
        save_data(data)
        await ctx.send(f"📍 Location set for {member.display_name}!")
    except GeocoderUnavailable:
        await ctx.send("Geocoding service unavailable. Try again later.")

@bot.command()
@commands.has_permissions(administrator=True)
async def remloc(ctx, member: discord.Member):
    """Remove a user's location (Admin only)"""
    data = load_data()
    if str(member.id) in data:
        del data[str(member.id)]
        save_data(data)
        await ctx.send(f"❌ Location removed for {member.display_name}!")
    else:
        await ctx.send(f"⚠️ No location found for {member.display_name}.")


@bot.command()
async def locations(ctx):
    """Show all locations grouped by continent and country"""
    data = load_data()
    if not data:
        await ctx.send("No locations set yet!")
        return

    # Create nested structure: continent > country > cities > users
    continent_map = {}
    for user_id, loc in data.items():
        user = await bot.fetch_user(int(user_id))
        entry = {
            "mention": f"<@{user_id}>",  # Create mention for clickable profile
            "city": loc['city'],
            "country": loc['country']
        }
        
        # Initialize continent if not exists
        continent_map.setdefault(loc['continent'], {})
        
        # Initialize country if not exists
        country = loc['country']
        continent_map[loc['continent']].setdefault(country, {})
        
        # Initialize city if not exists
        city = loc['city']
        continent_map[loc['continent']][country].setdefault(city, [])
        
        # Add user to city
        continent_map[loc['continent']][country][city].append(entry)

    # Build embed
    embed = discord.Embed(title="User Locations", color=0x00ff00)
    
    for continent, countries in continent_map.items():
        continent_text = []
        
        for country, cities in countries.items():
            country_text = []
            
            for city, users in cities.items():
                user_list = ", ".join([u['mention'] for u in users])  # Use mention for clickable profiles
                country_text.append(f"**{city}**: {user_list}")
            
            country_entry = f"\n🌐 **{country}**\n" + "\n".join(country_text)
            continent_text.append(country_entry)
        
        # Add a blank line after the continent's details
        embed.add_field(
            name=f"🌏 {continent}\u200b",
            value="\n\n".join(continent_text) + "\n\u200b",  # Add invisible space after each continent
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command()
async def map(ctx):
    """Generate interactive OpenStreetMap"""
    data = load_data()
    if not data:
        await ctx.send("No locations set yet!")
        return

    # Create Folium map with OpenStreetMap tiles
    m = folium.Map(tiles='OpenStreetMap')
    
    # Add markers with user info
    for user_id, loc in data.items():
        user = await bot.fetch_user(int(user_id))
        popup = folium.Popup(f"<b>{user.display_name}</b><br>{loc['city']}, {loc['country']}", max_width=250)
        folium.CircleMarker(
            location=[loc['lat'], loc['lon']],
            radius=6,
            popup=popup,
            color='#7289da',
            fill=True,
            fill_color='#7289da'
        ).add_to(m)

    # Save to bytes buffer
    map_buffer = BytesIO()
    m.save(map_buffer, close_file=False)
    map_buffer.seek(0)
    
    await ctx.send(
        content="**User Locations Map**\nDownload and open in browser:",
        file=discord.File(map_buffer, filename="user_map.html")
    )

from io import BytesIO
import folium
from folium.plugins import HeatMap

@bot.command()
async def mapheat(ctx):
    """Generate a heatmap of user locations"""
    data = load_data()
    if not data:
        await ctx.send("No locations set yet!")
        return

    # Create base map with OpenStreetMap tiles
    m = folium.Map(tiles='OpenStreetMap')

    # Prepare data for heatmap (latitude, longitude, weight)
    heatmap_data = []
    for user_id, loc in data.items():
        # Add location to heatmap data
        heatmap_data.append([loc['lat'], loc['lon']])

    # Add HeatMap layer to the map
    if heatmap_data:
        HeatMap(heatmap_data, radius=10, blur=15).add_to(m)

    # Save map to a bytes buffer
    map_buffer = BytesIO()
    m.save(map_buffer, close_file=False)
    map_buffer.seek(0)

    # Send the map as a downloadable HTML file
    await ctx.send(
        content="**User Locations Heatmap**\nDownload and open in browser:",
        file=discord.File(map_buffer, filename="heatmap.html")
    )


@bot.command()
async def mysetloc(ctx, *, location):
    """Set your own location"""
    geolocator = Nominatim(user_agent="geo_bot")
    try:
        loc = geolocator.geocode(location, addressdetails=True)
        if not loc:
            await ctx.send("Location not found!")
            return

        address = loc.raw.get('address', {})
        user_id = str(ctx.author.id)
        data = load_data()

        data[user_id] = {
            "city": address.get('city', address.get('town', location)),
            "country": address.get('country', "Unknown"),
            "continent": get_continent(address.get('country', "Unknown")),
            "lat": loc.latitude,
            "lon": loc.longitude
        }
        save_data(data)
        await ctx.send(f"📍 Your location has been set to {data[user_id]['city']}, {data[user_id]['country']}!")
    except GeocoderUnavailable:
        await ctx.send("Geocoding service unavailable. Try again later.")

@bot.command()
async def myremoveloc(ctx):
    """Remove your own location"""
    user_id = str(ctx.author.id)
    data = load_data()

    if user_id in data:
        del data[user_id]
        save_data(data)
        await ctx.send("📍 Your location has been removed.")
    else:
        await ctx.send("You don't have a location set.")

# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************

import discord
from discord import SelectOption
from discord.ext import commands
from discord.ui import View, Button, Select

games = {}

class GameSign:
    def __init__(self, max_slots, host_id, message_id, hostname, game_name):
        self.max_slots = max_slots
        self.host_id = host_id
        self.message_id = message_id
        self.hostname = hostname
        self.game_name = game_name
        self.slots = {str(i): {"player": None, "sponsor": None} for i in range(1, max_slots + 1)}

class GameView(View):
    def __init__(self, game_id, bot):
        super().__init__(timeout=None)
        self.game_id = game_id
        self.bot = bot
        
        self.add_item(PlayerJoinButton(game_id))
        self.add_item(SponsorJoinButton(game_id))
        self.add_item(LeaveButton(game_id))
    
    async def update_embed(self):
        game = games.get(self.game_id)
        if not game:
            return

        try:
            channel = self.bot.get_channel(self.game_id)
            message = await channel.fetch_message(game.message_id)
            
            embed = discord.Embed(title=f"Game Lobby: {game.game_name}", color=0x00ff00)
            embed.add_field(name="Host", value=f"{game.hostname} (<@{game.host_id}>)", inline=False)
            
            slots = []
            slot_text = ""
            for num, data in game.slots.items():
                player = f"<@{data['player']}>" if data['player'] else "Empty"
                sponsor = f"<@{data['sponsor']}>" if data['sponsor'] else "No sponsor"
                slot_info = f"Slot {num}: {player}\n   Sponsor: {sponsor}"
                
                # Check if adding this slot info would exceed the limit
                if len(slot_text) + len(slot_info) > 1024:
                    # If it would exceed, add the current slot_text as a field and reset it
                    embed.add_field(name="Slots", value=slot_text, inline=False)
                    slot_text = slot_info
                else:
                    # If not, append the slot info to the current slot_text
                    if slot_text:
                        slot_text += "\n" + slot_info
                    else:
                        slot_text = slot_info
            
            # Add the last set of slots if any
            if slot_text:
                embed.add_field(name="Slots", value=slot_text, inline=False)
            
            await message.edit(embed=embed)
        except Exception as e:
            print(f"Error updating embed: {e}")


class PlayerJoinButton(Button):
    def __init__(self, game_id):
        super().__init__(label="Join as Player", style=discord.ButtonStyle.green, custom_id=f"game_{game_id}_player_join")
        self.game_id = game_id

    async def callback(self, interaction: discord.Interaction):
        game = games[self.game_id]
        user_id = str(interaction.user.id)
        
        if any(slot["player"] == user_id or slot["sponsor"] == user_id for slot in game.slots.values()):
            await interaction.response.send_message("You're already in a slot!", ephemeral=True)
            return
            
        available_slots = [
            SelectOption(label=f"Slot {i}", value=str(i))
            for i in range(1, game.max_slots + 1)
            if not game.slots[str(i)]["player"]
        ]
        
        if not available_slots:
            await interaction.response.send_message("All player slots are full!", ephemeral=True)
            return
        
        # Split into pages of 20 slots each
        pages = [available_slots[i:i+20] for i in range(0, len(available_slots), 20)]
        
        # Create a new message with the first page
        view = SimplePaginationView(self.game_id, pages, 0, self.view)
        await interaction.response.send_message("Choose a player slot:", view=view, ephemeral=True)


class SimplePaginationView(View):
    def __init__(self, game_id, pages, current_page, main_view):
        super().__init__(timeout=60)
        self.game_id = game_id
        self.pages = pages
        self.current_page = current_page
        self.main_view = main_view
        
        # Add the select menu for the current page
        self.add_item(PlayerSlotSelect(game_id, pages[current_page], main_view))
        
        # Add navigation buttons if needed
        if len(pages) > 1:
            if current_page > 0:
                prev_button = Button(
                    label="Previous", 
                    style=discord.ButtonStyle.secondary, 
                    custom_id=f"prev_{game_id}_{current_page}"
                )
                prev_button.callback = self.prev_button_callback
                self.add_item(prev_button)
                
            if current_page < len(pages) - 1:
                next_button = Button(
                    label="Next", 
                    style=discord.ButtonStyle.secondary, 
                    custom_id=f"next_{game_id}_{current_page}"
                )
                next_button.callback = self.next_button_callback
                self.add_item(next_button)
        
        # Add page indicator
        page_indicator = f"Page {current_page + 1}/{len(pages)}"
        self.add_item(Button(
            label=page_indicator, 
            style=discord.ButtonStyle.gray, 
            disabled=True, 
            custom_id=f"page_indicator_{game_id}_{current_page}"
        ))

    async def prev_button_callback(self, interaction: discord.Interaction):
        if self.current_page > 0:
            new_view = SimplePaginationView(self.game_id, self.pages, self.current_page - 1, self.main_view)
            await interaction.response.edit_message(view=new_view)
    
    async def next_button_callback(self, interaction: discord.Interaction):
        if self.current_page < len(self.pages) - 1:
            new_view = SimplePaginationView(self.game_id, self.pages, self.current_page + 1, self.main_view)
            await interaction.response.edit_message(view=new_view)

class PlayerSlotSelect(Select):
    def __init__(self, game_id, options, main_view):
        super().__init__(placeholder="Select a slot...", options=options)
        self.game_id = game_id
        self.main_view = main_view

    async def callback(self, interaction: discord.Interaction):
        game = games[self.game_id]
        slot_num = self.values[0]
        user_id = str(interaction.user.id)
        
        # Check if user is already in any slot
        if any(slot["player"] == user_id or slot["sponsor"] == user_id for slot in game.slots.values()):
            await interaction.response.send_message("You're already in a slot! Leave your current slot first.", ephemeral=True)
            return
        
        if game.slots[slot_num]["player"]:
            await interaction.response.send_message("Slot already taken!", ephemeral=True)
        else:
            game.slots[slot_num]["player"] = user_id
            await interaction.response.send_message(f"Joined slot {slot_num} as player!", ephemeral=True)
            await self.main_view.update_embed()

class SponsorJoinButton(Button):
    def __init__(self, game_id):
        super().__init__(label="Join as Sponsor", style=discord.ButtonStyle.blurple, custom_id=f"game_{game_id}_sponsor_join")
        self.game_id = game_id

    async def callback(self, interaction: discord.Interaction):
        game = games[self.game_id]
        user_id = str(interaction.user.id)
        
        if any(slot["sponsor"] == user_id for slot in game.slots.values()):
            await interaction.response.send_message("You're already sponsoring a slot!", ephemeral=True)
            return
            
        available_slots = [
            SelectOption(label=f"Slot {i}", value=str(i))
            for i in range(1, game.max_slots + 1)
            if game.slots[str(i)]["player"] and not game.slots[str(i)]["sponsor"]
        ]
        
        if not available_slots:
            await interaction.response.send_message("No available slots to sponsor!", ephemeral=True)
            return
            
        view = SponsorSlotView(self.game_id, available_slots, self.view)
        await interaction.response.send_message("Choose a slot to sponsor:", view=view, ephemeral=True)

class SponsorSlotView(View):
    def __init__(self, game_id, options, main_view):
        super().__init__(timeout=60)
        self.main_view = main_view
        self.add_item(SponsorSlotSelect(game_id, options))

class SponsorSlotSelect(Select):
    def __init__(self, game_id, options):
        super().__init__(placeholder="Select a slot...", options=options)
        self.game_id = game_id

    async def callback(self, interaction: discord.Interaction):
        game = games[self.game_id]
        slot_num = self.values[0]
        user_id = str(interaction.user.id)
        
        if game.slots[slot_num]["sponsor"]:
            await interaction.response.send_message("Slot already sponsored!", ephemeral=True)
        else:
            game.slots[slot_num]["sponsor"] = user_id
            await interaction.response.send_message(f"Now sponsoring slot {slot_num}!", ephemeral=True)
            await self.view.main_view.update_embed()

class LeaveButton(Button):
    def __init__(self, game_id):
        super().__init__(label="Leave Slot", style=discord.ButtonStyle.red, custom_id=f"game_{game_id}_leave")
        self.game_id = game_id

    async def callback(self, interaction: discord.Interaction):
        game = games[self.game_id]
        user_id = str(interaction.user.id)
        removed = False
        
        for slot in game.slots.values():
            if slot["player"] == user_id:
                slot["player"] = None
                slot["sponsor"] = None
                removed = True
            elif slot["sponsor"] == user_id:
                slot["sponsor"] = None
                removed = True
        
        await interaction.response.send_message(
            "Left your slot!" if removed else "You weren't in any slot!",
            ephemeral=True
        )
        await self.view.update_embed()
        
        if removed:
            host = interaction.guild.get_member(int(game.host_id))
            if host:
                await host.send(f"{interaction.user.name} has left the game lobby.")

@bot.command()
async def startgame(ctx, max_slots: int, host: discord.Member, *, game_name: str):
    if not 2 <= max_slots <= 50:
        return await ctx.send("Slots must be between 2-50")
        
    game_id = ctx.channel.id
    games[game_id] = GameSign(max_slots, host.id, None, host.display_name, game_name)
    
    view = GameView(game_id, bot)
    message = await ctx.send(f"Game lobby initializing for {game_name} hosted by {host.mention}...", view=view)
    
    games[game_id].message_id = message.id
    await view.update_embed()

@bot.event
async def on_ready():
    for game_id in list(games.keys()):
        try:
            bot.add_view(GameView(game_id, bot))
            print(f"Re-registered view for game {game_id}")
        except Exception as e:
            print(f"Error re-registering view {game_id}: {e}")
            del games[game_id]


# ^***************************end************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************
# ^******************************************************************

# Remove default help command
bot.remove_command("help")

@bot.command()
async def help(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="🌍 ReMap Help",
        description="A bot for tracking user locations and managing games",
        color=0x7289da
    )
    
    embed.add_field(
        name="Admin Commands",
        value=( 
            "`!setloc @user <location>`: Set a user's location (Admin only)\n"
            "`!remloc @user`: Remove a user's location (Admin only)\n"
        ),
        inline=False
    )
    
    embed.add_field(
        name="User Commands",
        value=( 
            "`!locations`: Show all user locations grouped by continent and country\n"
            "`!map`: Generate interactive map of user locations\n"
            "`!mapheat`: Generate heatmap of user locations\n"
            "`!mysetloc <location>`: Set your own location\n"
            "`!myremoveloc`: Remove your own location"
        ),
        inline=False
    )

    embed.add_field(
        name="Game Commands",
        value=(
            f"`!startgame <max_players> @host <game_name>`: Start a new game\n"
        ),
        inline=False
    )

    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    # global active_games
    # active_games = load_games()
    print(f'Logged in as {bot.user}')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await load_extensions()
    print("Aux Battle extension loaded")

if __name__ == "__main__":
    bot.run(TOKEN)