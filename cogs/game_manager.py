import discord
from discord import SelectOption
from discord.ext import commands
from discord.ui import View, Button, Select

# Dictionary to store active games
games = {}

class GameSign:
    def __init__(self, max_slots, host_id, message_id, hostname, game_name, players_only):
        self.max_slots = max_slots
        self.host_id = host_id
        self.message_id = message_id
        self.hostname = hostname
        self.game_name = game_name
        self.players_only = players_only
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
                slot_info = f"Slot {num}: {player}"
                
                # Add sponsor information if there is a sponsor
                if data['sponsor']:
                    slot_info += f"\n   Sponsor: <@{data['sponsor']}>"
                
                if len(slot_text) + len(slot_info) > 1024:
                    embed.add_field(name="Slots", value=slot_text, inline=False)
                    slot_text = slot_info
                else:
                    slot_text += "\n" + slot_info if slot_text else slot_info
            
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

class GameManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        # Re-register views for active games
        for game_id in list(games.keys()):
            try:
                self.bot.add_view(GameView(game_id, self.bot))
                print(f"Re-registered view for game {game_id}")
            except Exception as e:
                print(f"Error re-registering view {game_id}: {e}")
                del games[game_id]
    
    @commands.command(aliases=['sg'])
    async def startgame(self, ctx, max_slots: int, host: discord.Member, *, args):
        """Start a new game lobby with specified slots and host"""
        if not 2 <= max_slots <= 50:
            return await ctx.send("Slots must be between 2-50")

        # Parse arguments
        args_list = args.split()
        players_only = "-p" in args_list
        game_name = " ".join([arg for arg in args_list if arg != "-p"])

        game_id = ctx.channel.id
        games[game_id] = GameSign(max_slots, host.id, None, host.display_name, game_name, players_only)

        view = GameView(game_id, self.bot)
        message = await ctx.send(f"Game lobby initializing for {game_name} hosted by {host.mention}...", view=view)

        games[game_id].message_id = message.id
        await view.update_embed()



    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addplayer(self, ctx, slot_num: int, player: discord.Member, *, game_name: str = None):
        """Add a player to an empty slot (Admin only)"""
        # Get the game from the current channel or by name
        game_id = ctx.channel.id
        game = games.get(game_id)
        
        if not game:
            if not game_name:
                return await ctx.send("No active game in this channel. Please specify a game name.")
            
            # Try to find the game by name in any channel
            for gid, g in games.items():
                if g.game_name.lower() == game_name.lower():
                    game = g
                    game_id = gid
                    break
            
            if not game:
                return await ctx.send(f"No game found with name '{game_name}'")
        
        # Check if slot number is valid
        if not 1 <= slot_num <= game.max_slots:
            return await ctx.send(f"Invalid slot number. Please choose between 1 and {game.max_slots}")
        
        # Check if slot is already taken
        slot_key = str(slot_num)
        if game.slots[slot_key]["player"]:
            return await ctx.send(f"Slot {slot_num} is already taken by <@{game.slots[slot_key]['player']}>")
        
        # Add player to slot
        user_id = str(player.id)
        
        # Check if player is already in another slot
        for slot in game.slots.values():
            if slot["player"] == user_id:
                return await ctx.send(f"{player.mention} is already in another slot. Please remove them first.")
        
        game.slots[slot_key]["player"] = user_id
        
        # Update the game embed
        channel = self.bot.get_channel(game_id)  # Changed bot to self.bot
        if channel:
            message = await channel.fetch_message(game.message_id)
            view = GameView(game_id, self.bot)
            await view.update_embed()
        
        await ctx.send(f"Added {player.mention} to slot {slot_num} in game '{game.game_name}'")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removeplayer(self, ctx, slot_num: int, *, game_name: str = None):
        """Remove a player from a slot (Admin only)"""
        # Get the game from the current channel or by name
        game_id = ctx.channel.id
        game = games.get(game_id)
        
        if not game:
            if not game_name:
                return await ctx.send("No active game in this channel. Please specify a game name.")
            
            # Try to find the game by name in any channel
            for gid, g in games.items():
                if g.game_name.lower() == game_name.lower():
                    game = g
                    game_id = gid
                    break
            
            if not game:
                return await ctx.send(f"No game found with name '{game_name}'")
        
        # Check if slot number is valid
        if not 1 <= slot_num <= game.max_slots:
            return await ctx.send(f"Invalid slot number. Please choose between 1 and {game.max_slots}")
        
        # Check if slot has a player
        slot_key = str(slot_num)
        if not game.slots[slot_key]["player"]:
            return await ctx.send(f"Slot {slot_num} is already empty")
        
        # Get player mention before removing
        player_id = game.slots[slot_key]["player"]
        player_mention = f"<@{player_id}>"
        
        # Remove player and sponsor from slot
        game.slots[slot_key]["player"] = None
        game.slots[slot_key]["sponsor"] = None
        
        # Update the game embed
        channel = self.bot.get_channel(game_id)
        if channel:
            message = await channel.fetch_message(game.message_id)
            view = GameView(game_id, self.bot)
            await view.update_embed()
        
        await ctx.send(f"Removed {player_mention} from slot {slot_num} in game '{game.game_name}'")

async def setup(bot):
    await bot.add_cog(GameManager(bot))
