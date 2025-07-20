import discord
from discord.ext import commands
from discord import app_commands
import random
import sqlite3

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

conn = sqlite3.connect("gacha.db")
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY
)''')

def add_column_if_not_exists(cursor, table, column, col_type, default):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}")

add_column_if_not_exists(c, "users", "pity", "INTEGER", 0)
add_column_if_not_exists(c, "users", "points", "INTEGER", 0)

c.execute('''
CREATE TABLE IF NOT EXISTS inventory (
    user_id INTEGER,
    character_name TEXT,
    rarity INTEGER,
    UNIQUE(user_id, character_name)
)
''')

conn.commit()

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

@tree.command(name="pull", description="Do a 10x pull")
async def pull(interaction: discord.Interaction):
    await interaction.response.defer()

    user_id = interaction.user.id

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

        try:
            c.execute(
                "INSERT OR IGNORE INTO inventory (user_id, character_name, rarity) VALUES (?, ?, ?)",
                (user_id, character["name"], character["rarity"])
            )
        except Exception as e:
            print(f"Error inserting inventory: {e}")

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

@tree.command(name="balance", description="Check your currency balance")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    c.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    points = row[0] if row else 0
    await interaction.response.send_message(f"💰 You have {points} points.", ephemeral=True)

@tree.command(name="inventory", description="See your pulled characters")
async def inventory(interaction: discord.Interaction):
    user_id = interaction.user.id
    c.execute("SELECT character_name, rarity FROM inventory WHERE user_id = ?", (user_id,))
    rows = c.fetchall()

    if not rows:
        await interaction.response.send_message("You have no characters yet. Try pulling some!", ephemeral=True)
        return

    embed = discord.Embed(title=f"{interaction.user.name}'s Inventory", color=0x00FF00)
    for name, rarity in rows:
        stars = "⭐" * rarity
        embed.add_field(name=name, value=stars, inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)

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

GUILD_ID = 1057046944020713473

@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)
    print(f"✅ Bot is online as {bot.user}")

bot.run("enter your bot token")

