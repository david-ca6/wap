import discord
from discord import app_commands
from chat_downloader import ChatDownloader
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict
from datetime import timedelta
from markdownify import markdownify as md
from tabulate import tabulate
import io

# W.A.P. or Watcher Activity Processor

# --------------- notes ---------------
# python3 -m pip install discord.py chat-downloader matplotlib pandas markdownify tabulate

# --------------- constants ---------------

BOT_ID = ""
BOT_PUBLIC_KEY = ""
BOT_TOKEN = ""

# --------------- youtube client ---------------

def get_youtube_chat(video_url: str):
    chat = ChatDownloader().get_chat(video_url)
    df = pd.DataFrame([
        {'time': msg['time_in_seconds'],
        # 'author': msg['author']['name'],
        'message': msg['message']}
        for msg in chat
    ])
    df = df[df['time'] >= 0]
    return df

def filter_chat(df: pd.DataFrame, filter: str):
    filters = filter.split("|")
    mask = df['message'].str.lower().apply(lambda x: any(f.lower() in x for f in filters))
    return df[mask]

def create_activity_per_minute_graph(df: pd.DataFrame, filtered_df: pd.DataFrame):
    # Convert seconds to minutes
    df['minute'] = (df['time'] / 60).astype(int)
    filtered_df['minute'] = (filtered_df['time'] / 60).astype(int)
    
    messages_per_minute = df.groupby('minute').size()
    filtered_messages_per_minute = filtered_df.groupby('minute').size()

    # Create lists for plotting with proper time formatting
    minutes = [str(timedelta(seconds=m*60)).split('.')[0] for m in messages_per_minute.index]
    
    # Set up the plot
    plt.figure(figsize=(12, 6))
    
    # Plot bars without spacing to create histogram look
    x = range(len(minutes))
    width = 1.0  # Full width to make bars touch
    plt.bar(x, messages_per_minute.values, width, label='All Messages', alpha=1, align='edge')
    
    # Ensure filtered data aligns with full dataset
    filtered_counts = [filtered_messages_per_minute.get(minute, 0) for minute in messages_per_minute.index]
    plt.bar(x, filtered_counts, width, label='Filtered Messages', alpha=1, align='edge')

    # Show fewer x-axis labels to prevent overlap
    step = max(len(x) // 10, 1)  # Show ~10 labels or less
    plt.xticks(x[::step], minutes[::step], rotation=45)
    plt.xlabel('Time (HH:MM:SS)')
    plt.ylabel('Messages per Minute')
    plt.title('Chat Activity Over Time')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save plot to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    return buf

def create_message_table(df: pd.DataFrame):
    return df.to_markdown(index=False)

def debug_print(df: pd.DataFrame):
    for _, row in df.iterrows():
        print(f"{row['time']}: {row['message']}")

# --------------- discord client ---------------

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = MyClient()

@client.tree.command()
@app_commands.describe(url="Video URL", filter="Filters are separated by |")
async def chat(interaction: discord.Interaction, url: str, filter: str = None):
    """A simple chat command"""
    username = interaction.user.name.lower()
    
    if username == "jonners" or username == "jonnersdes":
        await interaction.response.send_message("what a cute kitten... I'll help you!", ephemeral=True)
    else:
        # Send initial response
        await interaction.response.send_message("Working on it...", ephemeral=True)
        
    # Get chat and filter it
    df = get_youtube_chat(url)
    if filter:
        filtered_df = filter_chat(df, filter)
    else:
        filtered_df = df
    # debug_print(filtered_df)
    
    graph = create_activity_per_minute_graph(df, filtered_df)

    # create a H:MM:SS timestamp column using timedelta
    filtered_df['timestamp'] = filtered_df['time'].apply(lambda x: str(timedelta(seconds=int(x))).split('.')[0])
    filtered_df = filtered_df[['timestamp', 'message']]

    # create a csv file for the filtered data
    filtered_df.to_csv('table.csv', index=False)

    await interaction.followup.send(f"Here's the filtered chat graph with raw data:", files=[discord.File('table.csv'), discord.File(graph, 'graph.png')], ephemeral=True)
    

@client.tree.command()
async def help(interaction: discord.Interaction):
    """Print instructions"""
    username = interaction.user.name.lower()
    if username == "jonners":
        await interaction.response.send_message("""
        The cute kitten needs help?
        /chat <youtube url> <filter>
        /chat <twitch url> <filter>
        /help
        filters is are separated by |
        """, ephemeral=True)
    else:
        await interaction.response.send_message("""
        W.A.P. Present! I'm here to help!
        /chat <youtube url> <filter>
        /chat <twitch url> <filter>
        /help
        filters is are separated by |
        """, ephemeral=True)
    
client.run(BOT_TOKEN)