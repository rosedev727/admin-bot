Thanks for grabbing our little admin bot. Follow these short steps and you’ll be moderating in no time.

# 1 . What you need

Python 3.9+ installed (We are developing on Python 3.12)
A Discord account with permission to create a bot in the Developer Portal
A server where you can add the bot

# 2 . Get the files

Download the ZIP from GitHub and unzip it.

# 3 . Install the libraries

python -m pip install -r requirements.txt
This pulls discord.py (for slash commands) and python-dotenv (to read .env file).

# 4 . Create a bot & grab its token

Go to https://discord.com/developers/applications
New Application → Bot tab → Add Bot
Copy the TOKEN (you’ll need it in a sec)
Under OAuth2 → URL Generator tick bot and applications.commands, select the bot permission set you want (at least Moderate Members, Ban, Kick, Manage Messages).
Open the generated link, choose your server, and authorize.

# 5 . Fill in the blanks.

Edit a file called .env in the project folder:
# BOT_TOKEN=PASTE_YOUR_TOKEN_HERE  # Replace with your own bot token created at https://discord.com/developers/applications.
# GUILD_ID=YOUR_SERVER_ID          # Your server's guild ID, copy guild ID from Discord, optional, speeds up slash command registration.
# LOG_CHANNEL_ID=MODLOG_CHANNEL_ID # Channel that will receive moderation logs, copy channel ID from Discord.
# STAFF_ROLE_ID=STAFF_ROLE_ID      # Role that can use staff commands, use your server's staff role ID.
(You can get IDs by enabling Developer Mode in Discord > Settings > Advanced.)

# 6 . Run it

## python bot.py
First start takes up to a minute while Discord registers slash commands.
After that you’ll see /warn, /ban, /ticket, etc. right in the chat bar.

# 7 . Daily use

• Moderation: /warn, /unwarn, /warn_list, /ban, /unban, /kick, /mute, /unmute, /purge, /say
• Tickets: users type /ticket <subject> → bot opens a private channel.
  Moderators close it with !close inside the ticket.
• All actions auto-log in the channel you set as LOG_CHANNEL_ID.

# 8 . Stopping the bot

Press CTRL-C in the terminal, or close the window.
To run 24/7, host it on a VPS, Docker, Railway, Heroku, etc.

Happy coding!
— Rose Development Team 🥀