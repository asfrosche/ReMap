import discord
from discord.ext import commands
import random
import asyncio
import json
import os

class AuxBattle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.participants = []
        self.is_signup_open = False
        self.current_tournament = None
        self.matches = {}
        self.image_urls = [
            # Add some default image URLs or load from a file
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            # etc.
        ]
        
        # Load data if exists
        self.data_file = "aux_battle_data.json"
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.participants = data.get('participants', [])
                    self.matches = data.get('matches', {})
                    self.current_tournament = data.get('current_tournament', None)
                    self.is_signup_open = data.get('is_signup_open', False)
            except Exception as e:
                print(f"Error loading aux battle data: {e}")
    
    def save_data(self):
        data = {
            'participants': self.participants,
            'matches': self.matches,
            'current_tournament': self.current_tournament,
            'is_signup_open': self.is_signup_open
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f)
    
    @commands.group(name="auxbattle", aliases=["aux"], invoke_without_command=True)
    async def auxbattle(self, ctx):
        """Main command for Aux Battle. Use subcommands for specific actions."""
        await ctx.send("Welcome to Aux Battle! Use `!auxbattle signup` to join the tournament.")
    
    @auxbattle.command(name="signup")
    async def signup(self, ctx):
        """Sign up for the aux battle tournament"""
        if not self.is_signup_open:
            await ctx.send("Signups are currently closed!")
            return
            
        user_id = ctx.author.id
        if user_id in self.participants:
            await ctx.send("You're already signed up for the tournament!")
            return
            
        self.participants.append(user_id)
        self.save_data()
        await ctx.send(f"{ctx.author.mention} has signed up for the Aux Battle tournament!")
    
    @auxbattle.command(name="opensignup")
    @commands.has_permissions(administrator=True)
    async def open_signup(self, ctx):
        """Open signups for a new tournament"""
        self.is_signup_open = True
        self.participants = []
        self.save_data()
        await ctx.send("Aux Battle tournament signups are now open! Use `!auxbattle signup` to join.")
    
    @auxbattle.command(name="closesignup")
    @commands.has_permissions(administrator=True)
    async def close_signup(self, ctx):
        """Close signups and prepare for tournament"""
        if not self.is_signup_open:
            await ctx.send("Signups are already closed!")
            return
            
        self.is_signup_open = False
        self.save_data()
        await ctx.send(f"Signups are now closed! {len(self.participants)} players have registered.")
    
    @auxbattle.command(name="start")
    @commands.has_permissions(administrator=True)
    async def start_tournament(self, ctx):
        """Start the tournament and create the bracket"""
        if len(self.participants) < 2:
            await ctx.send("Need at least 2 participants to start a tournament!")
            return
            
        # Shuffle participants for random matchups
        random.shuffle(self.participants)
        
        # Create tournament bracket
        self.current_tournament = {
            'rounds': [],
            'current_round': 0,
            'current_match': 0
        }
        
        # Create first round matches
        matches = []
        for i in range(0, len(self.participants), 2):
            if i + 1 < len(self.participants):
                match_id = f"r0m{i//2}"
                self.matches[match_id] = {
                    'player1': self.participants[i],
                    'player2': self.participants[i+1],
                    'image': random.choice(self.image_urls),
                    'song1': None,
                    'song2': None,
                    'votes1': 0,
                    'votes2': 0,
                    'winner': None,
                    'status': 'pending'
                }
                matches.append(match_id)
            else:
                # If odd number of participants, give one a bye
                next_round_match_id = f"r1m{i//4}"
                if next_round_match_id not in self.matches:
                    self.matches[next_round_match_id] = {
                        'player1': self.participants[i],
                        'player2': None,
                        'image': None,
                        'song1': None,
                        'song2': None,
                        'votes1': 0,
                        'votes2': 0,
                        'winner': self.participants[i],
                        'status': 'pending'
                    }
        
        self.current_tournament['rounds'].append(matches)
        self.save_data()
        
        await ctx.send("Tournament has been created! Use `!auxbattle bracket` to see the matchups.")
        await self.next_match(ctx)
    
    @auxbattle.command(name="submit")
    async def submit_song(self, ctx, song_link: str):
        """Submit a song for your current match"""
        if not self.current_tournament:
            await ctx.send("No active tournament!")
            return
            
        # Find user's current match
        current_round = self.current_tournament['current_round']
        current_match_id = self.current_tournament['rounds'][current_round][self.current_tournament['current_match']]
        match = self.matches[current_match_id]
        
        user_id = ctx.author.id
        if user_id != match['player1'] and user_id != match['player2']:
            await ctx.send("You're not in the current match!")
            return
            
        # Validate song link (basic check)
        if not ('youtube.com' in song_link or 'youtu.be' in song_link or 
                'spotify.com' in song_link or 'soundcloud.com' in song_link):
            await ctx.send("Please submit a valid music link (YouTube, Spotify, SoundCloud).")
            return
            
        # Store the song
        if user_id == match['player1']:
            match['song1'] = song_link
            await ctx.send(f"{ctx.author.mention} has submitted their song!")
        else:
            match['song2'] = song_link
            await ctx.send(f"{ctx.author.mention} has submitted their song!")
        
        self.save_data()
        
        # If both songs submitted, start voting
        if match['song1'] and match['song2']:
            match['status'] = 'voting'
            self.save_data()
            await self.start_voting(ctx, current_match_id)
    
    async def start_voting(self, ctx, match_id):
        """Start voting for a match"""
        match = self.matches[match_id]
        
        # Get player usernames
        player1 = await self.bot.fetch_user(match['player1'])
        player2 = await self.bot.fetch_user(match['player2'])
        
        embed = discord.Embed(title="Aux Battle Voting", color=discord.Color.blue())
        embed.set_image(url=match['image'])
        embed.add_field(name=f"Option 1: {player1.name}", value=match['song1'], inline=False)
        embed.add_field(name=f"Option 2: {player2.name}", value=match['song2'], inline=False)
        embed.add_field(name="How to vote", value="React with 1️⃣ for Option 1 or 2️⃣ for Option 2", inline=False)
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("1️⃣")
        await message.add_reaction("2️⃣")
        
        # Wait for votes (60 seconds)
        await ctx.send("Voting is now open for 60 seconds!")
        await asyncio.sleep(60*60*24)
        
        # Get updated message to count reactions
        message = await ctx.channel.fetch_message(message.id)
        
        # Count votes
        votes1 = 0
        votes2 = 0
        
        for reaction in message.reactions:
            if str(reaction.emoji) == "1️⃣":
                votes1 = reaction.count - 1  # Subtract 1 for the bot's reaction
            elif str(reaction.emoji) == "2️⃣":
                votes2 = reaction.count - 1  # Subtract 1 for the bot's reaction
        
        match['votes1'] = votes1
        match['votes2'] = votes2
        
        # Determine winner
        if votes1 > votes2:
            match['winner'] = match['player1']
            winner_name = player1.name
        elif votes2 > votes1:
            match['winner'] = match['player2']
            winner_name = player2.name
        else:
            # In case of a tie, randomly select winner
            match['winner'] = random.choice([match['player1'], match['player2']])
            winner_name = player1.name if match['winner'] == match['player1'] else player2.name
        
        match['status'] = 'completed'
        self.save_data()
        
        await ctx.send(f"Voting has ended! The winner is {winner_name} with {max(votes1, votes2)} votes!")
        
        # Move to next match or advance tournament
        await self.advance_tournament(ctx)
    
    async def advance_tournament(self, ctx):
        """Advance to the next match or next round"""
        current_round = self.current_tournament['current_round']
        current_match = self.current_tournament['current_match']
        
        # Move to next match in current round
        if current_match < len(self.current_tournament['rounds'][current_round]) - 1:
            self.current_tournament['current_match'] += 1
            self.save_data()
            await self.next_match(ctx)
            return
        
        # All matches in current round complete, create next round
        winners = []
        for match_id in self.current_tournament['rounds'][current_round]:
            winners.append(self.matches[match_id]['winner'])
        
        # If only one winner, tournament is over
        if len(winners) == 1:
            winner = await self.bot.fetch_user(winners[0])
            await ctx.send(f"🏆 Tournament completed! The champion is {winner.mention}! 🏆")
            self.current_tournament = None
            self.save_data()
            return
        
        # Create next round matches
        next_round = current_round + 1
        matches = []
        
        for i in range(0, len(winners), 2):
            if i + 1 < len(winners):
                match_id = f"r{next_round}m{i//2}"
                self.matches[match_id] = {
                    'player1': winners[i],
                    'player2': winners[i+1],
                    'image': random.choice(self.image_urls),
                    'song1': None,
                    'song2': None,
                    'votes1': 0,
                    'votes2': 0,
                    'winner': None,
                    'status': 'pending'
                }
                matches.append(match_id)
            else:
                # If odd number of winners, give one a bye
                next_round_match_id = f"r{next_round+1}m{i//4}"
                if next_round_match_id not in self.matches:
                    self.matches[next_round_match_id] = {
                        'player1': winners[i],
                        'player2': None,
                        'image': None,
                        'song1': None,
                        'song2': None,
                        'votes1': 0,
                        'votes2': 0,
                        'winner': winners[i],
                        'status': 'pending'
                    }
        
        self.current_tournament['rounds'].append(matches)
        self.current_tournament['current_round'] = next_round
        self.current_tournament['current_match'] = 0
        self.save_data()
        
        await ctx.send(f"Round {next_round + 1} created! Moving to next match.")
        await self.next_match(ctx)
    
    async def next_match(self, ctx):
        """Start the next match"""
        if not self.current_tournament:
            await ctx.send("No active tournament!")
            return
            
        current_round = self.current_tournament['current_round']
        current_match = self.current_tournament['current_match']
        
        if current_round >= len(self.current_tournament['rounds']):
            await ctx.send("Tournament is complete!")
            self.current_tournament = None
            self.save_data()
            return
            
        if current_match >= len(self.current_tournament['rounds'][current_round]):
            await ctx.send("All matches in this round are complete!")
            await self.advance_tournament(ctx)
            return
            
        match_id = self.current_tournament['rounds'][current_round][current_match]
        match = self.matches[match_id]
        
        # Get player usernames
        player1 = await self.bot.fetch_user(match['player1'])
        player2 = await self.bot.fetch_user(match['player2'])
        
        embed = discord.Embed(title=f"Aux Battle - Round {current_round + 1}, Match {current_match + 1}", 
                             color=discord.Color.green())
        embed.set_image(url=match['image'])
        embed.add_field(name="Players", value=f"{player1.mention} vs {player2.mention}", inline=False)
        embed.add_field(name="Instructions", 
                       value="Submit a song that matches this image using `!auxbattle submit [song_link]`", 
                       inline=False)
        
        await ctx.send(embed=embed)
        await ctx.send(f"{player1.mention} and {player2.mention}, please submit your songs!")
    
    @auxbattle.command(name="bracket")
    async def show_bracket(self, ctx):
        """Display the current tournament bracket"""
        if not self.current_tournament:
            await ctx.send("No active tournament!")
            return
            
        embed = discord.Embed(title="Aux Battle Tournament Bracket", color=discord.Color.gold())
        
        for round_idx, round_matches in enumerate(self.current_tournament['rounds']):
            round_text = ""
            for match_idx, match_id in enumerate(round_matches):
                match = self.matches[match_id]
                
                # Get player names
                try:
                    player1 = await self.bot.fetch_user(match['player1'])
                    player1_name = player1.name
                except:
                    player1_name = "TBD"
                    
                try:
                    if match['player2']:
                        player2 = await self.bot.fetch_user(match['player2'])
                        player2_name = player2.name
                    else:
                        player2_name = "BYE"
                except:
                    player2_name = "TBD"
                
                # Show winner if match is completed
                if match['status'] == 'completed':
                    winner_name = player1_name if match['winner'] == match['player1'] else player2_name
                    round_text += f"Match {match_idx+1}: {player1_name} vs {player2_name} - Winner: {winner_name}\n"
                else:
                    round_text += f"Match {match_idx+1}: {player1_name} vs {player2_name}\n"
            
            embed.add_field(name=f"Round {round_idx+1}", value=round_text or "No matches", inline=False)
        
        await ctx.send(embed=embed)
    
    @auxbattle.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset_tournament(self, ctx):
        """Reset the current tournament"""
        self.current_tournament = None
        self.matches = {}
        self.participants = []
        self.is_signup_open = False
        self.save_data()
        await ctx.send("Tournament has been reset!")

    @commands.command(name='help_aux')
    async def help_aux(self, ctx):
        """Display help information for the Aux Battle commands"""
        embed = discord.Embed(
            title="🎵 Aux Battle Help 🎵",
            description="A music tournament where players submit songs that match an image, and others vote for the best match!",
            color=discord.Color.blue()
        )
        
        # Player Commands
        player_commands = [
            "`!auxbattle signup` - Join the aux battle tournament",
            "`!auxbattle submit [song_link]` - Submit a song for the current match",
            "`!auxbattle vote [match_id] [1/2]` - Vote for your favorite song submission",
            "`!auxbattle bracket` - View the current tournament bracket"
        ]
        embed.add_field(name="Player Commands", value="\n".join(player_commands), inline=False)
        
        # Admin Commands
        admin_commands = [
            "`!auxbattle opensignup` - Open registrations for a new tournament",
            "`!auxbattle closesignup` - Close registrations",
            "`!auxbattle start` - Create and start the tournament with signed-up players",
            "`!auxbattle endvoting [match_id]` - End voting for a specific match",
            "`!auxbattle reset` - Reset the entire tournament"
        ]
        embed.add_field(name="Admin Commands", value="\n".join(admin_commands), inline=False)
        
        # How to Play
        how_to_play = [
            "1. Sign up using `!auxbattle signup`",
            "2. Wait for an admin to start the tournament",
            "3. When it's your turn, you'll be shown an image",
            "4. Submit a song that matches the vibe of the image using `!auxbattle submit [song_link]`",
            "5. Everyone votes on which song fits better",
            "6. Winners advance to the next round",
            "7. Last player standing wins!"
        ]
        embed.add_field(name="How to Play", value="\n".join(how_to_play), inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AuxBattle(bot))

