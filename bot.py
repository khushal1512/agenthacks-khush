import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
import asyncio
import sys
import re

from portia_client import portia, bug_report_plan, feature_request_plan, doc_search_plan

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

print("Starting AI Product Manager Bot...")
load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    print(f'Bot is ready! Logged in as {bot.user.name} ({bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    await bot.change_presence(activity=discord.Game(name="Managing your workflow"))

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name='general')
    if channel:
        await channel.send(f"Welcome, {member.mention}! Type /help to see what I can do.")

@bot.tree.command(name="bug-report", description="Report a bug to be triaged automatically.")
@app_commands.describe(
    description="Clearly describe the bug you are experiencing.",
    email="Your email address to receive confirmation and updates."
)
async def bug_report(interaction: discord.Interaction, description: str, email: str):
    await interaction.response.defer(thinking=True, ephemeral=True)

    if not EMAIL_REGEX.match(email):
        await interaction.followup.send("❌ The email address you provided appears to be invalid. Please try again.", ephemeral=True)
        return

    logging.info(f"Bug report received from {interaction.user}: {description}")
    try:
        plan_run = await asyncio.to_thread(
            lambda: portia.run_plan(
                bug_report_plan,
                plan_run_inputs={"bug_description": description, "user_email": email}
            )
        )
        final_output = plan_run.outputs.final_output.value
        embed = discord.Embed(
            title="✅ Bug Report Processed Successfully",
            description="Your report has been submitted and tickets have been created.",
            color=discord.Color.green()
        )
        embed.add_field(name="GitHub Issue", value=f"[View Issue]({final_output.github_issue_url})", inline=True)
        embed.add_field(name="Linear Ticket", value=f"[View Ticket]({final_output.linear_ticket_url})", inline=True)
        embed.set_footer(text=f"A confirmation has been sent to {email}.")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logging.error(f"Error running bug_report_plan: {e}")
        await interaction.followup.send("❌ An error occurred while processing your bug report.", ephemeral=True)

@bot.tree.command(name="feature-request", description="Suggest a new feature to be triaged automatically.")
@app_commands.describe(
    description="Describe the new feature you would like to see.",
    email="Your email address to receive confirmation and updates."
)
async def feature_request(interaction: discord.Interaction, description: str, email: str):
    await interaction.response.defer(thinking=True, ephemeral=True)

    if not EMAIL_REGEX.match(email):
        await interaction.followup.send("❌ The email address you provided appears to be invalid. Please try again.", ephemeral=True)
        return

    logging.info(f"Feature request received from {interaction.user}: {description}")
    try:
        plan_run = await asyncio.to_thread(
            lambda: portia.run_plan(
                feature_request_plan,
                plan_run_inputs={"feature_description": description, "user_email": email}
            )
        )
        final_output = plan_run.outputs.final_output.value
        embed = discord.Embed(
            title="💡 Feature Request Processed",
            description="Your suggestion has been submitted and tickets have been created.",
            color=discord.Color.blue()
        )
        embed.add_field(name="GitHub Issue", value=f"[View Issue]({final_output.github_issue_url})", inline=True)
        embed.add_field(name="Linear Ticket", value=f"[View Ticket]({final_output.linear_ticket_url})", inline=True)
        embed.set_footer(text=f"A confirmation has been sent to {email}.")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logging.error(f"Error running feature_request_plan: {e}")
        await interaction.followup.send("❌ An error occurred while processing your feature request.", ephemeral=True)

@bot.tree.command(name="doc", description="Search the documentation for an answer to your question.")
@app_commands.describe(
    query="The question you want to ask the documentation."
)
async def doc_search(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    logging.info(f"Doc search received from {interaction.user}: {query}")

    try:
        plan_run = await asyncio.to_thread(
            lambda: portia.run_plan(
                doc_search_plan,
                plan_run_inputs={"user_query": query}
            )
        )
        answer = plan_run.outputs.final_output.value.answer

        # Create the initial embed
        embed = discord.Embed(
            title=f"🔎 Search Results for:",
            description=f"> {query}",
            color=discord.Color.og_blurple()
        )
        embed.set_footer(text=f"Search performed for {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)
        if answer:
            for i in range(0, len(answer), 2000):
                chunk = answer[i:i+2000]
                await interaction.followup.send(chunk)
        else:
            await interaction.followup.send("No answer was found.")

    except Exception as e:
        logging.error(f"Error running doc_search_plan: {e}")
        await interaction.followup.send("Sorry, I couldn't find an answer to that question.")


@bot.tree.command(name="help", description="Shows a list of available commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 AI Product Manager Bot - Help", color=discord.Color.blue())
    embed.add_field(name="/bug-report [description] [email]", value="Report a bug or issue.", inline=False)
    embed.add_field(name="/feature-request [description] [email]", value="Suggest a new feature.", inline=False)
    embed.add_field(name="/doc [query]", value="Search the Portia documentation for an answer to your question.", inline=False)
    embed.add_field(name="/help", value="Shows this help message.", inline=False)
    await interaction.response.send_message(embed=embed)

print("🔌 Starting bot connection...")
bot.run(token, log_handler=handler, log_level=logging.DEBUG)