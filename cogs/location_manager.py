# cogs/location_manager.py
import discord
from discord.ext import commands
import pycountry_convert as pc
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable

from utils.data_manager import save_json, load_json
from utils.map_generator import create_location_map, create_heatmap, map_to_bytes
from config import LOCATIONS_FILE, GEOCODER_USER_AGENT

class LocationManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.geolocator = Nominatim(user_agent=GEOCODER_USER_AGENT)
    
    def get_continent(self, country_name):
        try:
            country_code = pc.country_name_to_country_alpha2(country_name)
            return pc.convert_continent_code_to_continent_name(
                pc.country_alpha2_to_continent_code(country_code)
            )
        except:
            return "Unknown"
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setloc(self, ctx, member: discord.Member, *, location):
        """Set a user's location (Admin only)"""
        try:
            loc = self.geolocator.geocode(location, addressdetails=True)
            if not loc:
                await ctx.send("Location not found!")
                return
                
            address = loc.raw.get('address', {})
            data = load_json(LOCATIONS_FILE)
            
            data[str(member.id)] = {
                "username": member.display_name,
                "city": address.get('city', address.get('town', location)),
                "country": address.get('country', "Unknown"),
                "continent": self.get_continent(address.get('country', "Unknown")),
                "lat": loc.latitude,
                "lon": loc.longitude
            }
            save_json(LOCATIONS_FILE, data)
            await ctx.send(f"📍 Location set for {member.display_name}!")
        except GeocoderUnavailable:
            await ctx.send("Geocoding service unavailable. Try again later.")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def remloc(self, ctx, member: discord.Member):
        """Remove a user's location (Admin only)"""
        data = load_json(LOCATIONS_FILE)
        if str(member.id) in data:
            del data[str(member.id)]
            save_json(LOCATIONS_FILE, data)
            await ctx.send(f"❌ Location removed for {member.display_name}!")
        else:
            await ctx.send(f"⚠️ No location found for {member.display_name}.")
    
    @commands.command()
    async def locations(self, ctx):
        """Show all locations grouped by continent and country"""
        data = load_json(LOCATIONS_FILE)
        if not data:
            await ctx.send("No locations set yet!")
            return

        # Create nested structure: continent > country > cities > users
        continent_map = {}
        for user_id, loc in data.items():
            user = await self.bot.fetch_user(int(user_id))
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
    
    @commands.command()
    async def map(self, ctx):
        """Generate interactive OpenStreetMap"""
        data = load_json(LOCATIONS_FILE)
        if not data:
            await ctx.send("No locations set yet!")
            return

        # Update username for each entry
        for user_id in data:
            try:
                user = await self.bot.fetch_user(int(user_id))
                data[user_id]['username'] = user.display_name
            except:
                data[user_id]['username'] = "Unknown User"
        
        # Create map and convert to bytes
        m = create_location_map(data)
        map_buffer = map_to_bytes(m)
        
        await ctx.send(
            content="**User Locations Map**\nDownload and open in browser:",
            file=discord.File(map_buffer, filename="user_map.html")
        )
    
    @commands.command()
    async def mapheat(self, ctx):
        """Generate a heatmap of user locations"""
        data = load_json(LOCATIONS_FILE)
        if not data:
            await ctx.send("No locations set yet!")
            return

        # Create heatmap and convert to bytes
        m = create_heatmap(data)
        map_buffer = map_to_bytes(m)

        # Send the map as a downloadable HTML file
        await ctx.send(
            content="**User Locations Heatmap**\nDownload and open in browser:",
            file=discord.File(map_buffer, filename="heatmap.html")
        )
    
    @commands.command()
    async def mysetloc(self, ctx, *, location):
        """Set your own location"""
        try:
            loc = self.geolocator.geocode(location, addressdetails=True)
            if not loc:
                await ctx.send("Location not found!")
                return

            address = loc.raw.get('address', {})
            user_id = str(ctx.author.id)
            data = load_json(LOCATIONS_FILE)

            data[user_id] = {
                "username": ctx.author.display_name,
                "city": address.get('city', address.get('town', location)),
                "country": address.get('country', "Unknown"),
                "continent": self.get_continent(address.get('country', "Unknown")),
                "lat": loc.latitude,
                "lon": loc.longitude
            }
            save_json(LOCATIONS_FILE, data)
            await ctx.send(f"📍 Your location has been set to {data[user_id]['city']}, {data[user_id]['country']}!")
        except GeocoderUnavailable:
            await ctx.send("Geocoding service unavailable. Try again later.")
    
    @commands.command()
    async def myremoveloc(self, ctx):
        """Remove your own location"""
        user_id = str(ctx.author.id)
        data = load_json(LOCATIONS_FILE)

        if user_id in data:
            del data[user_id]
            save_json(LOCATIONS_FILE, data)
            await ctx.send("📍 Your location has been removed.")
        else:
            await ctx.send("You don't have a location set.")

async def setup(bot):
    await bot.add_cog(LocationManager(bot))
