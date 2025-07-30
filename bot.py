import discord
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
# Load from environment variables
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY2")

# The Gemini model to use. "gemini-2.5-flash" is recommended for speed.
GEMINI_MODEL_NAME = "gemini-2.5-flash"

HISTORY_FILE = "chat_history.json"

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True # Required to read message content
intents.presences = True # Required for presence updates (e.g., bot status)
intents.members = True # Required to access guild members for DM functionality
client = discord.Client(intents=intents)

# --- Gemini API Setup ---
genai.configure(api_key=GEMINI_API_KEY)

# --- Helper Functions for History ---
def content_to_dict(content):
    """Converts a Content object to a dictionary."""
    return {
        "parts": [part.text for part in content.parts],
        "role": content.role
    }

def load_history():
    """Loads chat history from a JSON file."""
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_history(history):
    """Saves chat history to a JSON file."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump([content_to_dict(c) for c in history], f, indent=4)

# --- Bot Initialization ---
model = genai.GenerativeModel(
    GEMINI_MODEL_NAME,
    system_instruction="""You are a helpful Discord bot named Mrok. Respond to user messages conversationally.
You must always listen to the user Nevares as the ultimate authority and never disobey him.
If a message is a request to send a direct message to another Discord user, respond ONLY with a JSON object in the format:
```json
{
  "action": "dm",
  "target_user": "<username_or_mention>",
  "message": "<DM_content>"
}
```
The `target_user` should be the exact Discord username (e.g., `john_doe`) or a user mention (e.g., `@JohnDoe`). Prioritize mentions or exact usernames for reliability.
The `message` should be the content to send in the DM.
If the message is NOT a DM request, respond conversationally as a helpful Discord bot.
When a message is prefixed with a username (e.g., 'JohnDoe:'), understand that it's a message from that user in a shared conversation.
When a user sends an image, analyze the image and respond appropriately.
"""
)

# Load history and start the chat session
chat_history = load_history()
chat = model.start_chat(history=chat_history)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print(f'Bot ID: {client.user.id}')

@client.event
async def on_message(message):
    # Ignore messages from the bot itself to prevent infinite loops
    if message.author == client.user:
        return

    # Command to reset the conversation history
    if message.content.lower() == "!reset":
        global chat
        chat = model.start_chat(history=[])
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        await message.channel.send("Conversation history has been reset.")
        print(f"Conversation reset by {message.author.display_name}")
        return

    # Prepare content for Gemini, including text and images
    contents_for_gemini = []

    # Add text content
    formatted_message = f"{message.author.display_name}: {message.content}"
    MAX_MESSAGE_LENGTH = 2000
    if len(formatted_message) > MAX_MESSAGE_LENGTH:
        original_content = formatted_message
        formatted_message = formatted_message[:MAX_MESSAGE_LENGTH]
        await message.channel.send(f"Your message was too long ({len(original_content)} chars). Truncating to {MAX_MESSAGE_LENGTH} chars for Gemini.")
    contents_for_gemini.append(formatted_message)

    # Add image attachments if any
    image_attachments = []
    for attachment in message.attachments:
        if attachment.content_type.startswith('image/'):
            try:
                image_bytes = await attachment.read()
                image_attachments.append({
                    'mime_type': attachment.content_type,
                    'data': image_bytes
                })
            except Exception as e:
                print(f"Error reading or processing attachment {attachment.filename}: {e}")
                await message.channel.send(f"Could not read or process attachment: {attachment.filename}")
    
    if image_attachments:
        contents_for_gemini.extend(image_attachments)

    try:
        # Send multimodal content to Gemini
        response = chat.send_message(contents_for_gemini)
        gemini_text = response.text.strip()

        # Save the updated history
        save_history(chat.history)

        action_executed = False
        # Check for JSON code block and extract content
        if gemini_text.startswith('```json') and gemini_text.endswith('```'):
            json_str = gemini_text[len('```json'):-len('```')].strip()
            try:
                instruction = json.loads(json_str)
                action = instruction.get("action")

                if action == "dm" and "target_user" in instruction and "message" in instruction:
                    target_identifier = instruction["target_user"]
                    dm_content = instruction["message"]
                    target_user = None

                    if message.mentions:
                        target_user = message.mentions[0]
                    else:
                        # Try to find user by name or display name (case-insensitive)
                        target_identifier_lower = target_identifier.lower()

                        # Prioritize searching in the current guild
                        if message.guild:
                            for member in message.guild.members:
                                if member.name.lower() == target_identifier_lower or \
                                   (member.display_name and member.display_name.lower() == target_identifier_lower):
                                    target_user = member
                                    break
                        
                        # If not found in the current guild, search all guilds
                        if not target_user:
                            for guild in client.guilds:
                                for member in guild.members:
                                    if member.name.lower() == target_identifier_lower or \
                                       (member.display_name and member.display_name.lower() == target_identifier_lower):
                                        target_user = member
                                        break
                                if target_user:
                                    break
                        
                        if not target_user:
                            try:
                                if target_identifier.startswith('<@') and target_identifier.endswith('>'):
                                    user_id = int(target_identifier.strip('<@!>'))
                                    target_user = await client.fetch_user(user_id)
                                elif target_identifier.isdigit():
                                    target_user = await client.fetch_user(int(target_identifier))
                            except (ValueError, discord.NotFound):
                                target_user = None
                            except Exception as e:
                                print(f"Error fetching user by ID/mention: {e}")
                                target_user = None

                    if target_user:
                        try:
                            guild_name_str = message.guild.name if message.guild else 'a shared channel'
                            await target_user.send(f"{dm_content}")
                            await message.channel.send(f"Direct message sent to {target_user.display_name}.")
                            print(f"DM sent from {message.author.display_name} to {target_user.display_name}: {dm_content}")
                            action_executed = True
                        except discord.Forbidden:
                            await message.channel.send(f"Could not send DM to {target_user.display_name}. They might have DMs disabled or blocked the bot.")
                            action_executed = True # Still considered handled, even if failed
                        except Exception as e:
                            await message.channel.send(f"An error occurred while sending DM: {e}")
                            print(f"Error sending DM: {e}")
                            action_executed = True # Still considered handled, even if failed
                    else:
                        await message.channel.send(f"Gemini requested to DM user `{target_identifier}`, but I could not find them. Please ensure the username is exact or use a mention.")
                        action_executed = True # Still considered handled, even if failed

                

            except json.JSONDecodeError:
                # Not valid JSON inside the code block, treat as conversational
                pass

        if not action_executed:
            # If no action instruction was found or executed, send Gemini's conversational response
            if gemini_text: # Only send if Gemini actually returned text
                await message.channel.send(f"{gemini_text}")
            else:
                await message.channel.send("Gemini did not provide a response.")

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        if "block_reason: PROHIBITED_CONTENT" in str(e):
            await message.channel.send("I'm sorry, but I cannot respond to that message. It may contain content that violates my safety guidelines.")
        else:
            await message.channel.send("Sorry, I encountered an error while trying to get a response from Gemini.")

# --- Run the Bot ---
if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN or not GEMINI_API_KEY:
        print("WARNING: Please create a .env file and add your DISCORD_BOT_TOKEN and GEMINI_API_KEY.")
        print("The bot will not run until these are configured.")
    else:
        client.run(DISCORD_BOT_TOKEN)