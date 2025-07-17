import discord
from discord.ext import commands
from discord import app_commands
import random
import sqlite3

intents = discord.Intents.default()
intents.message_content = False

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --- Database Setup ---
conn = sqlite3.connect("gacha.db")
c = conn.cursor()

# Create table if not exists (only id initially)
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY
)''')

# Function to add missing columns safely
def add_column_if_not_exists(cursor, table, column, col_type, default):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}")

# Add 'pity' and 'points' columns if missing
add_column_if_not_exists(c, "users", "pity", "INTEGER", 0)
add_column_if_not_exists(c, "users", "points", "INTEGER", 0)
conn.commit()

# --- Character Pools ---
five_star_characters = [
    {"name": "Seele", "rarity": 5, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Seele/SplashArt.png"},
    {"name": "Bronya", "rarity": 5, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Bronya/SplashArt.png"},
    {"name": "Jingliu", "rarity": 5, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Jingliu/SplashArt.png"},
    {"name": "Kafka", "rarity": 5, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Kafka/SplashArt.png"},
    {"name": "Welt", "rarity": 5, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Welt/SplashArt.png"},
    {"name": "Clara", "rarity": 5, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Clara/SplashArt.png"},
    {"name": "Himeko", "rarity": 5, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Himeko/SplashArt.png"},
    {"name": "Gepard", "rarity": 5, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Gepard/SplashArt.png"},
    {"name": "Kal'tsit", "rarity": 5, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Kaltsit/SplashArt.png"},
]

four_star_characters = [
    {"name": "Serval", "rarity": 4, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Serval/SplashArt.png"},
    {"name": "Sushang", "rarity": 4, "image": "https://github.com/Mar-7th/StarRailRes/raw/master/image/Sushang/SplashArt.png"},
]

three_star_characters = [
    {"name": "Silvermane Soldier", "rarity": 3, "image": None},
    {"name": "Curio Merchant", "rarity": 3, "image": None},
]

# --- Gacha Logic ---
def pull_character(pity):
    if pity >= 79:
        return random.choice(five_star_characters), True

    roll = random.random()
    if roll < 0.018:
        return random.choice(five_star_characters), True
    elif roll < 0.2:
        return random.choice(four_star_characters), False
    else:
        return random.choice(three_star_characters), False

# --- /pull command ---
@tree.command(name="pull", description="Do a 10x pull")
async def pull(interaction: discord.Interaction):
    await interaction.response.defer()

    user_id = interaction.user.id

    # Use the global cursor/connection here:
    c.execute("SELECT pity, points FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()

    if row:
        pity, points = row
    else:
        pity, points = 0, 0
        c.execute("INSERT INTO users (id, pity, points) VALUES (?, 0, 0)", (user_id,))
        conn.commit()

    if points < 10:
        await interaction.followup.send("You need 10 points to pull (1 point per message).", ephemeral=True)
        return

    results = []
    got_five_star = False
    for _ in range(10):
        character, is_five = pull_character(pity)
        results.append(character)
        if character["rarity"] >= 4:
            pity = 0
        else:
            pity += 1
        if is_five:
            got_five_star = True

    if got_five_star:
        pity = 0

    c.execute("UPDATE users SET pity = ?, points = points - 10 WHERE id = ?", (pity, user_id))
    conn.commit()

    for character in results:
        embed = discord.Embed(
            title=f"✨ You pulled {character['name']}!",
            description=f"⭐️ Rarity: {character['rarity']}★",
            color=0xFFD700 if character["rarity"] == 5 else 0x800080 if character["rarity"] == 4 else 0x808080
        )
        if character["image"]:
            embed.set_image(url=character["image"])
        await interaction.followup.send(embed=embed)

# --- Track messages to give points ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    c.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()

    if row:
        points = row[0] + 1
        c.execute("UPDATE users SET points = ? WHERE id = ?", (points, user_id))
    else:
        c.execute("INSERT INTO users (id, pity, points) VALUES (?, 0, 1)", (user_id,))
    conn.commit()

    await bot.process_commands(message)

# --- Ready event ---
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot is online as {bot.user}")

# --- Run bot ---
bot.run("MTM5MzMzMTA4MjUyNjcyMDE4Mg.GreDmv.eSFqdaNjwRP3hS-p5s1VJLyrU6WQjH6IEpqIzI")

