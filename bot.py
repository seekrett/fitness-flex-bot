import os
import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("DISCORD_TOKEN is missing! Check your .env file.")


# TODO: clean up project structure. new class in its own etc.


# --- INTENSITY MULTIPLIERS ---
INTENSITY_MULTIPLIERS = {
    "low": 1.0,
    "medium": 1.2,
    "high": 1.5
}

class WorkoutBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Set up SQLite Database with new columns for categories
        async with aiosqlite.connect("workouts.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    points REAL DEFAULT 0,
                    total_minutes INTEGER DEFAULT 0,
                    core_points REAL DEFAULT 0,
                    arms_points REAL DEFAULT 0,
                    legs_points REAL DEFAULT 0,
                    full_body_points REAL DEFAULT 0
                )
            """)
            await db.commit()
        
        # Sync slash commands globally
        await self.tree.sync()
        print("Slash commands synced successfully!")

bot = WorkoutBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')


# --- COMMAND 1: LOG WORKOUT ---
@bot.tree.command(name="log", description="Log a workout session to earn points!")
@app_commands.choices(category=[
    app_commands.Choice(name="Core", value="core"),
    app_commands.Choice(name="Arms", value="arms"),
    app_commands.Choice(name="Legs", value="legs"),
    app_commands.Choice(name="Full Body", value="full body"),
])
@app_commands.choices(intensity=[
    app_commands.Choice(name="Low", value="low"),
    app_commands.Choice(name="Medium", value="medium"),
    app_commands.Choice(name="High", value="high"),
])
async def log_workout(interaction: discord.Interaction, category: app_commands.Choice[str], intensity: app_commands.Choice[str], minutes: int):
    if minutes <= 0:
        await interaction.response.send_message("Minutes must be greater than 0!", ephemeral=True)
        return

    user_id = interaction.user.id
    
    # Calculate points based on the intensity multiplier
    multiplier = INTENSITY_MULTIPLIERS.get(intensity.value, 1.0)
    earned_points = round(minutes * multiplier, 1) 
    
    # Format the category string to match our database column names
    category_col = f"{category.value.replace(' ', '_')}_points"

    async with aiosqlite.connect("workouts.db") as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
            if row:
                query = f"UPDATE users SET points = points + ?, total_minutes = total_minutes + ?, {category_col} = {category_col} + ? WHERE user_id = ?"
                await db.execute(query, (earned_points, minutes, earned_points, user_id))
            else:
                query = f"INSERT INTO users (user_id, points, total_minutes, {category_col}) VALUES (?, ?, ?, ?)"
                await db.execute(query, (user_id, earned_points, minutes, earned_points))
        await db.commit()

    embed = discord.Embed(
        title="💪 Workout Logged!",
        color=discord.Color.green()
    )
    embed.add_field(name="Category", value=category.name, inline=True)
    embed.add_field(name="Intensity", value=intensity.name, inline=True)
    embed.add_field(name="Duration", value=f"{minutes} mins", inline=True)
    embed.add_field(name="Points Earned", value=f"+{earned_points} pts", inline=False)
    embed.set_footer(text=f"Logged by {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed)


# --- COMMAND 2: PROFILE ---
@bot.tree.command(name="profile", description="View your workout profile and stats!")
async def profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    async with aiosqlite.connect("workouts.db") as db:
        async with db.execute("SELECT points, total_minutes, core_points, arms_points, legs_points, full_body_points FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()

    if not row:
        await interaction.response.send_message("You haven't logged any workouts yet! Use `/log` to get started.", ephemeral=True)
        return

    points, total_minutes, core_pts, arms_pts, legs_pts, full_body_pts = row

    embed = discord.Embed(
        title=f"👤 {interaction.user.display_name}'s Profile",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Overall Points", value=f"**{round(points, 1)}** pts", inline=True)
    embed.add_field(name="Total Time", value=f"**{total_minutes}** mins", inline=True)
    embed.add_field(name="\u200B", value="\u200B", inline=True) 
    
    embed.add_field(name="Core", value=f"{round(core_pts, 1)} pts", inline=True)
    embed.add_field(name="Arms", value=f"{round(arms_pts, 1)} pts", inline=True)
    embed.add_field(name="Legs", value=f"{round(legs_pts, 1)} pts", inline=True)
    embed.add_field(name="Full Body", value=f"{round(full_body_pts, 1)} pts", inline=True)
    
    if interaction.user.display_avatar:
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)


# --- COMMAND 3: INTERACTIVE LEADERBOARD ---
class LeaderboardSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Overall", value="points", description="Total points across all categories", emoji="🏆"),
            discord.SelectOption(label="Core", value="core_points", description="Top points in Core", emoji="🔥"),
            discord.SelectOption(label="Arms", value="arms_points", description="Top points in Arms", emoji="💪"),
            discord.SelectOption(label="Legs", value="legs_points", description="Top points in Legs", emoji="🦵"),
            discord.SelectOption(label="Full Body", value="full_body_points", description="Top points in Full Body", emoji="🏋️"),
        ]
        super().__init__(placeholder="Choose a category to filter...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_category = self.values[0]
        
        titles = {
            "points": "Overall",
            "core_points": "Core",
            "arms_points": "Arms",
            "legs_points": "Legs",
            "full_body_points": "Full Body"
        }
        category_name = titles.get(selected_category)

        async with aiosqlite.connect("workouts.db") as db:
            query = f"SELECT user_id, {selected_category} FROM users WHERE {selected_category} > 0 ORDER BY {selected_category} DESC LIMIT 10"
            async with db.execute(query) as cursor:
                top_users = await cursor.fetchall()

        embed = discord.Embed(
            title=f"🏆 {category_name} Leaderboard",
            color=discord.Color.gold()
        )

        if not top_users:
            embed.description = f"No workouts have been logged in the **{category_name}** category yet!"
        else:
            medals = ["🥇", "🥈", "🥉"]
            description = ""
            for idx, (user_id, points) in enumerate(top_users, start=1):
                prefix = medals[idx - 1] if idx <= 3 else f"`#{idx}`"
                description += f"{prefix} <@{user_id}> — **{round(points, 1)} pts**\n"
            embed.description = description

        await interaction.response.edit_message(embed=embed, view=self.view)


class LeaderboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LeaderboardSelect())


@bot.tree.command(name="leaderboard", description="Check the server workout leaderboard!")
async def leaderboard(interaction: discord.Interaction):
    async with aiosqlite.connect("workouts.db") as db:
        async with db.execute("SELECT user_id, points, total_minutes FROM users WHERE points > 0 ORDER BY points DESC LIMIT 10") as cursor:
            top_users = await cursor.fetchall()

    embed = discord.Embed(
        title="🏆 Overall Leaderboard",
        color=discord.Color.gold()
    )

    if not top_users:
        embed.description = "No workouts have been logged yet! Be the first using `/log`."
    else:
        medals = ["🥇", "🥈", "🥉"]
        description = ""
        for idx, (user_id, points, total_mins) in enumerate(top_users, start=1):
            prefix = medals[idx - 1] if idx <= 3 else f"`#{idx}`"
            description += f"{prefix} <@{user_id}> — **{round(points, 1)} pts** ({total_mins} mins)\n"
        embed.description = description

    view = LeaderboardView()
    await interaction.response.send_message(embed=embed, view=view)


# --- COMMAND 4: REFRESH (ADMIN ONLY) ---
@bot.tree.command(name="refresh", description="[ADMIN] Wipes the database and resets everyone to 0.")
@app_commands.checks.has_permissions(administrator=True)
async def refresh_db(interaction: discord.Interaction):
    async with aiosqlite.connect("workouts.db") as db:
        await db.execute("DELETE FROM users")
        await db.commit()
    
    await interaction.response.send_message("✅ The database has been completely wiped. Everyone is back to 0 points!", ephemeral=False)

@refresh_db.error
async def refresh_db_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You must be a server Administrator to use this command!", ephemeral=True)


bot.run(TOKEN)