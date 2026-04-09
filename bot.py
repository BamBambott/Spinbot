import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import os
from datetime import datetime, timedelta

# ─── CONFIG ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SPIN_COOLDOWN_HOURS = 24
WINNERS_FILE = "winners.json"

PRIZES = [
    {"label": "😔  Better Luck Next Time",   "weight": 40, "winner": False},
    {"label": "🎯  10% Discount Code",       "weight": 20, "winner": True},
    {"label": "⭐  VIP Access – 7 Days",     "weight": 10, "winner": True},
    {"label": "🎉  Free NFT Drop",           "weight": 8,  "winner": True},
    {"label": "🔥  Whitelist Spot",          "weight": 6,  "winner": True},
    {"label": "🎁  $5 Gift Card",            "weight": 5,  "winner": True},
    {"label": "🎵  Exclusive Merch",         "weight": 5,  "winner": True},
    {"label": "💎  $10 USDT",               "weight": 3,  "winner": True},
    {"label": "🚀  $20 Crypto",             "weight": 2,  "winner": True},
    {"label": "💰  $50 JACKPOT!",           "weight": 1,  "winner": True},
]

SPIN_FRAMES = [
    "🎰 | ❓  ❓  ❓ | Spinning...",
    "🎰 | 🌀  ❓  ❓ | Hold tight...",
    "🎰 | 🌀  🌀  ❓ | Almost...",
    "🎰 | 🌀  🌀  🌀 | Revealing...",
]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

cooldowns: dict[int, datetime] = {}

def pick_prize() -> dict:
    weights = [p["weight"] for p in PRIZES]
    return random.choices(PRIZES, weights=weights, k=1)[0]

def load_winners() -> list:
    if os.path.exists(WINNERS_FILE):
        with open(WINNERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_winner(user_id: int, username: str, prize: str):
    winners = load_winners()
    winners.append({
        "user_id": user_id,
        "username": username,
        "prize": prize,
        "timestamp": datetime.utcnow().isoformat()
    })
    with open(WINNERS_FILE, "w") as f:
        json.dump(winners, f, indent=2)

def format_cooldown(delta: timedelta) -> str:
    total = int(delta.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s or not parts: parts.append(f"{s}s")
    return " ".join(parts)

def spin_embed(title, description, color):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="🎰 SpinBot | Use /spin to try your luck!")
    return embed

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} is online and ready!")
    await bot.change_presence(activity=discord.Game(name="🎰 /spin to win prizes!"))

@bot.tree.command(name="spin", description="🎰 Spin the wheel and win a prize!")
async def spin(interaction: discord.Interaction):
    user_id = interaction.user.id
    now = datetime.utcnow()
    if user_id in cooldowns:
        elapsed = now - cooldowns[user_id]
        cooldown = timedelta(hours=SPIN_COOLDOWN_HOURS)
        if elapsed < cooldown:
            remaining = cooldown - elapsed
            embed = spin_embed("⏳ Cooldown Active", f"You already spun today!\nCome back in **{format_cooldown(remaining)}**.", discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    embed = spin_embed("🎰 Spinning...", SPIN_FRAMES[0], discord.Color.blurple())
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    for frame in SPIN_FRAMES[1:]:
        await asyncio.sleep(0.8)
        embed.description = frame
        await message.edit(embed=embed)
    await asyncio.sleep(0.8)
    prize = pick_prize()
    cooldowns[user_id] = now
    if prize["winner"]:
        save_winner(user_id, str(interaction.user), prize["label"])
        result_embed = discord.Embed(title="🎉 You Won!", description=f"**{interaction.user.mention}** just spun the wheel!\n\n**Prize: {prize['label']}**\n\nContact an admin to claim your reward! 🏆", color=discord.Color.gold())
        result_embed.set_thumbnail(url=interaction.user.display_avatar.url)
        result_embed.set_footer(text=f"🎰 SpinBot | Next spin in {SPIN_COOLDOWN_HOURS}h")
    else:
        result_embed = discord.Embed(title="😔 No Prize This Time", description=f"**{interaction.user.mention}** spun the wheel...\n\n**{prize['label']}**\n\nBetter luck next time! Come back in **{SPIN_COOLDOWN_HOURS}h**.", color=discord.Color.red())
        result_embed.set_footer(text="🎰 SpinBot | Use /spin to try your luck!")
    await message.edit(embed=result_embed)

@bot.tree.command(name="prizes", description="📋 View all available prizes and odds")
async def prizes(interaction: discord.Interaction):
    total_weight = sum(p["weight"] for p in PRIZES)
    lines = []
    for p in sorted(PRIZES, key=lambda x: x["weight"]):
        pct = (p["weight"] / total_weight) * 100
        lines.append(f"{p['label']} — **{pct:.1f}%**")
    embed = discord.Embed(title="🎰 Prize Pool", description="\n".join(lines), color=discord.Color.blurple())
    embed.set_footer(text="Use /spin to try your luck!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="winners", description="🏆 Show the latest 10 winners")
async def winners(interaction: discord.Interaction):
    all_winners = load_winners()
    if not all_winners:
        await interaction.response.send_message("No winners yet! Be the first — use `/spin`.", ephemeral=True)
        return
    recent = all_winners[-10:][::-1]
    lines = [f"**{w['username']}** — {w['prize']} _{w['timestamp'][:10]}_" for w in recent]
    embed = discord.Embed(title="🏆 Recent Winners", description="\n".join(lines), color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mystats", description="📊 Check your own spin history")
async def mystats(interaction: discord.Interaction):
    user_id = interaction.user.id
    all_winners = load_winners()
    user_wins = [w for w in all_winners if w["user_id"] == user_id]
    now = datetime.utcnow()
    in_cooldown = user_id in cooldowns and (now - cooldowns[user_id]) < timedelta(hours=SPIN_COOLDOWN_HOURS)
    next_spin = "Now!" if not in_cooldown else format_cooldown(timedelta(hours=SPIN_COOLDOWN_HOURS) - (now - cooldowns[user_id]))
    embed = discord.Embed(title=f"📊 {interaction.user.display_name}'s Stats", color=discord.Color.blurple())
    embed.add_field(name="Total Wins", value=str(len(user_wins)), inline=True)
    embed.add_field(name="Next Spin", value=next_spin, inline=True)
    if user_wins:
        embed.add_field(name="Last Prize", value=user_wins[-1]["prize"], inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
