# File: main.py - Core Application Logic
import os
import logging
from flask import Flask, request, jsonify
import requests
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CallbackContext

# Initialize Flask app and logging
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Configuration (USE ENVIRONMENT VARIABLES) ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
NVIM_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"  # From your code and API docs[citation:1]

# Initialize Telegram Bot
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === NVIDIA NIM API Call ===
def get_nim_response(user_message, conversation_history=[]):
    """
    Sends a request to the NVIDIA NIM chat completions endpoint[citation:1].
    Uses the 'moonshotai/kimi-k2.5' model as specified.
    """
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json"
    }
    
    # Prepare messages: history + new user message
    messages = conversation_history + [{"role": "user", "content": user_message}]
    
    # Match the payload structure from your example and the API reference[citation:1][citation:3]
    payload = {
        "model": "moonshotai/kimi-k2.5",
        "messages": messages,
        "max_tokens": 1024,  # Reduced from 16384 for quicker responses
        "temperature": 0.7,
        "top_p": 0.9,
        "stream": False  # Simpler handling for bot response
    }
    
    try:
        response = requests.post(NVIM_ENDPOINT, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Extract the AI's reply from the response
        # Structure matches the example from NVIDIA NIM docs[citation:3]
        reply = data["choices"][0]["message"]["content"]
        return reply
        
    except requests.exceptions.RequestException as e:
        logger.error(f"NVIDIA API request failed: {e}")
        return "I'm experiencing technical difficulties. Please try again later."

# === Telegram Bot Handlers ===
def handle_message(update: Update, context: CallbackContext):
    """Processes incoming Telegram messages."""
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    logger.info(f"Received message from {chat_id}: {user_message}")
    
    # Get AI response from NVIDIA NIM
    ai_reply = get_nim_response(user_message)
    
    # Send the reply back to Telegram
    telegram_bot.send_message(chat_id=chat_id, text=ai_reply)

# === Flask Routes for Webhook ===
@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint where Telegram sends updates."""
    dispatcher = Dispatcher(telegram_bot, None, workers=0)
    
    # Process the incoming update from Telegram
    update = Update.de_json(request.get_json(), telegram_bot)
    
    # Handle the message
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.process_update(update)
    
    return jsonify({'status': 'ok'})

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Initial setup route to configure Telegram webhook URL."""
    webhook_url = f"https://{request.host}/webhook"
    success = telegram_bot.set_webhook(webhook_url)
    return jsonify({'success': success, 'url': webhook_url})

@app.route('/health', methods=['GET'])
def health_check():
    """Health endpoint for Vercel monitoring."""
    return jsonify({'status': 'healthy'})

# Main entry point for Vercel serverless
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)