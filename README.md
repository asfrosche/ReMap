# ReMap Discord Bot

A versatile Discord bot for tracking user locations, managing game lobbies, and hosting Aux Battle tournaments.

## Features

### Location Tracking
- Set and manage user locations
- View locations grouped by continent and country
- Generate interactive maps and heatmaps of user locations

### Game Management
- Create game lobbies with customizable player slots
- Join as player or sponsor
- Easy-to-use button interface for slot selection

### Aux Battle
- Music tournament where players match songs to images
- Tournament bracket system with automatic advancement
- Voting system to determine winners

## Commands

### Location Commands
- `!setloc @user <location>` - Set a user's location (Admin only)
- `!remloc @user` - Remove a user's location (Admin only)
- `!locations` - Show all user locations grouped by continent and country
- `!map` - Generate interactive map of user locations
- `!mapheat` - Generate heatmap of user locations
- `!mysetloc <location>` - Set your own location
- `!myremoveloc` - Remove your own location

### Game Commands
- `!startgame <max_players> @host <game_name>` - Start a new game lobby

### Aux Battle Commands
- `!auxbattle signup` - Join the aux battle tournament
- `!auxbattle submit [song_link]` - Submit a song for the current match
- `!auxbattle bracket` - View the current tournament bracket
- `!auxbattle opensignup` - Open registrations (Admin only)
- `!auxbattle closesignup` - Close registrations (Admin only)
- `!auxbattle start` - Start the tournament (Admin only)
- `!auxbattle reset` - Reset the tournament (Admin only)

## Setup

1. Clone this repository
2. Install required packages: `pip install -r requirements.txt`
3. Create a `.env` file with your Discord bot token:
