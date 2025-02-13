import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
from dotenv import load_dotenv
from messages import generate_polite_response, analyze_message, parse_analysis
import os

# Load environment variables
load_dotenv()

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Helper function to create embeds
def create_embed(title, description, fields=None, color=0x3498db):
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)
    return embed

# Main Menu View
class MainMenu(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✨ Generate Response", style=discord.ButtonStyle.success)
    async def generate_response(self, interaction: discord.Interaction, button: Button):
        modal = GenerateResponseModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🤖 Analyze Message", style=discord.ButtonStyle.primary)
    async def analyze_message(self, interaction: discord.Interaction, button: Button):
        modal = AnalyzeMessageModal()
        await interaction.response.send_modal(modal)

# Generate Response Modal
class GenerateResponseModal(Modal, title="✨ Generate Polite Response"):
    def __init__(self):
        super().__init__(timeout=None)
        self.user_input = TextInput(
            label="✏️ Your Message",
            style=discord.TextStyle.long,
            placeholder="Enter your message here...",
            required=True
        )
        self.recipient_type = TextInput(
            label="👤 Recipient Type",
            placeholder="Professor or Classmate",
            required=True
        )
        self.content_type = TextInput(
            label="📝 Content Type",
            placeholder="Text or Email",
            required=True
        )
        self.num_variations = TextInput(
            label="🔢 Number of Variations",
            placeholder="Enter a number (1-5)",
            required=False,
            default="2"
        )
        self.add_item(self.user_input)
        self.add_item(self.recipient_type)
        self.add_item(self.content_type)
        self.add_item(self.num_variations)

    async def on_submit(self, interaction: discord.Interaction):
        recipient_type = self.recipient_type.value  # Get selected recipient type
        content_type = self.content_type.value      # Get selected content type
        num_variations = int(self.num_variations.value) if self.num_variations.value.isdigit() else 2

        responses = generate_polite_response(
            self.user_input.value,
            content_type,
            recipient_type,
            num_variations
        )
        if responses:
            fields = []
            for i, (subject, body) in enumerate(responses, 1):
                fields.append((f"📄 Variation {i}\n", f"**Subject:** {subject}\n{body}\n" if content_type == "Email" else body))
            embed = create_embed("✨ Generated Responses\n", "Here are your polite responses:\n", fields)

            view = ResponseView(
                responses=responses,
                user_input=self.user_input.value,
                content_type=content_type,
                recipient_type=recipient_type,
                num_variations=num_variations
            )

            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send("Failed to generate a response.")

# Response View
class ResponseView(View):
    def __init__(self, responses, user_input, content_type, recipient_type, num_variations):
        super().__init__(timeout=None)
        self.responses = responses  # Store all response variations
        self.user_input = user_input  # Store user input for "Generate Again"
        self.content_type = content_type  # Store content type for "Generate Again"
        self.recipient_type = recipient_type  # Store recipient type for "Generate Again"
        self.num_variations = num_variations  # Store number of variations for "Generate Again"

    @discord.ui.button(label="😊 Generate Again", style=discord.ButtonStyle.primary)
    async def generate_again(self, interaction: discord.Interaction, button: Button):
        # Call the generate_polite_response function again with the same attributes
        responses = generate_polite_response(
            self.user_input,
            self.content_type,
            self.recipient_type,
            self.num_variations
        )
        if responses:
            fields = []
            for i, (subject, body) in enumerate(responses, 1):
                fields.append((f"📄 Variation {i}\n", f"**Subject:** {subject}\n{body}\n" if self.content_type == "Email" else body))
            embed = create_embed("✨ Generated Responses\n", "Here are your polite responses:\n", fields)
            view = ResponseView(responses, self.user_input, self.content_type, self.recipient_type, self.num_variations)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send("Failed to generate a response.")

    @discord.ui.button(label="✨ Generate New Message", style=discord.ButtonStyle.red)
    async def generate_new_message(self, interaction: discord.Interaction, button: Button):
        # Open the modal again for new input
        modal = GenerateResponseModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🤖 Analyze Message", style=discord.ButtonStyle.success)
    async def analyze_message(self, interaction: discord.Interaction, button: Button):
        # Open the Analyze Message modal
        modal = AnalyzeMessageModal()
        await interaction.response.send_modal(modal)


# Analyze Message Modal
class AnalyzeMessageModal(Modal, title="Analyze Message 🤖"):
    received_message = TextInput(
        label="Received Message",
        style=discord.TextStyle.long,
        placeholder="🕵️‍♂️ Paste the message you want to analyze...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw_analysis = analyze_message(self.received_message.value)
        if "Error:" in raw_analysis:
            await interaction.response.send_message(raw_analysis, ephemeral=True)
            return
        
        analysis = parse_analysis(raw_analysis)
        
        # Create fields for the embed
        fields = [
            ("👁‍🗨 Primary Emotion", analysis["emotion"].capitalize()),
            ("👓 Social Cues", "\n".join([f"- {cue}" for cue in analysis["cues"]])),
            ("📌 Key Words", ", ".join(analysis["keywords"])),
            ("💌 Summary", analysis["summary"]),
            ("Response Suggestions", 
             f"😁 Positive: {analysis['responses']['positive']}\n\n"
             f"😐 Neutral: {analysis['responses']['neutral']}\n\n"
             f"🙁 Negative: {analysis['responses']['negative']}")
        ]
        
        # Create the embed
        embed = create_embed("🤖 Message Analysis", "Here is the analysis of your message:", fields)
        
        # Add a "Generate Message" button
        view = GenerateMessageView(analysis["responses"])
        await interaction.response.send_message(embed=embed, view=view)

# View for the "Generate Message" button
class GenerateMessageView(View):
    def __init__(self, responses):
        super().__init__(timeout=None)
        self.responses = responses  # Store response suggestions from the analysis

    @discord.ui.button(label="✨ Generate Message", style=discord.ButtonStyle.success)
    async def generate_message(self, interaction: discord.Interaction, button: Button):
        # Open a modal for generating a polite response
        modal = GenerateResponseModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🤖 Analyze Message", style=discord.ButtonStyle.primary)
    async def analyze_message(self, interaction: discord.Interaction, button: Button):
        # Open the Analyze Message modal
        modal = AnalyzeMessageModal()
        await interaction.response.send_modal(modal)

# Bot Commands
@bot.command(name="menu")
async def menu(ctx):
    embed = create_embed(
        title="📩  Communication Assistant",
        description="Choose an option below to get started!"
    )
    view = MainMenu()
    await ctx.send(embed=embed, view=view)

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))