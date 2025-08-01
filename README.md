# Discord Bot with Gemini

This is a Discord bot that uses Google's Gemini 2.5 Flash model to interact with users in a Discord server. The bot can engage in conversations, send direct messages, and analyze images.

## Features

*   **Conversational AI:** The bot uses the Gemini Pro model to have natural and engaging conversations with users.
*   **Direct Messaging:** The bot can send direct messages to other users on behalf of the user who issued the command.
*   **Image Understanding:** The bot can analyze images sent by users and respond to them.
*   **Conversation History:** The bot maintains a chat history to provide context for ongoing conversations.
*   **Conversation Reset:** The bot has a `!reset` command to clear the conversation history.

## Setup

1.  **Clone the repository:**

    ```
    git clone https://github.com/your-username/discord-bot-gemini.git
    ```

2.  **Install the dependencies:**

    ```
    pip install -r requirements.txt
    ```

3.  **Create a `.env` file in the root directory of the project and add the following variables:**

    ```
    DISCORD_BOT_TOKEN=your-discord-bot-token
    GEMINI_API_KEY=your-gemini-api-key
    ```

## Usage

1.  **Run the bot:**

    ```
    python bot.py
    ```

2.  **Interact with the bot in a Discord server:**

    *   **To have a conversation with the bot, simply mention it in a message or include the keyword "mrok" (case-insensitive) in your message.**
    *   **To send a direct message to another user, use the following format:**

        ```
        @bot-name dm @username message
        ```

    *   **To reset the conversation history, type `!reset` in the channel.**
