import random
import time
from threading import Thread, Event
from telegram.ext import Updater, CommandHandler, Filters

TOKEN = '7388123945:AAEPN-9cslWEua3ro7njPzNTJxE1N0MD8Js'
OWNER_USER_ID = '5732310517'

# Global variables to control the message sending loop and channels list
user_running_status = {}  # Dictionary to store running status for each user
user_channels = {}  # Dictionary to store user-specific channel lists
user_starting_number = {}  # Dictionary to store user-specific starting numbers
user_target_channel = {}  # Dictionary to store user-specific target channels
authorized_users = set()  # Set to store authorized user IDs
user_threads = {}  # Dictionary to store user-specific threads
user_events = {}  # Dictionary to store user-specific events

def restricted(func):
    def wrapper(update, context, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id != OWNER_USER_ID and user_id not in authorized_users:
            update.message.reply_text("You are not authorized to use this bot.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

def owner_only(func):
    def wrapper(update, context, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id != OWNER_USER_ID:
            update.message.reply_text("Only the bot owner can use this command.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

def channel_owner_only(func):
    def wrapper(update, context, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id not in user_channels:
            update.message.reply_text("You don't have any channels added.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

@channel_owner_only
def start(update, context):
    user_id = str(update.effective_user.id)
    if user_id not in user_running_status:
        user_running_status[user_id] = False

    if not user_running_status[user_id]:
        user_running_status[user_id] = True
        update.message.reply_text('Bot started! Messages will be sent every minute.')

        # Create and start a new event and thread for the user
        user_events[user_id] = Event()
        user_threads[user_id] = Thread(target=send_messages, args=(context, user_id, user_events[user_id]))
        user_threads[user_id].start()
    else:
        update.message.reply_text('Bot is already running.')

@channel_owner_only
def stop(update, context):
    user_id = str(update.effective_user.id)
    if user_id in user_running_status and user_running_status[user_id]:
        user_running_status[user_id] = False
        user_events[user_id].set()  # Signal the event to stop the thread
        user_threads[user_id].join()  # Wait for the thread to finish
        update.message.reply_text('Bot stopped!')
    else:
        update.message.reply_text('Bot is already stopped.')

@restricted
def help_command(update, context):
    user_id = str(update.effective_user.id)
    if user_id == OWNER_USER_ID:
        update.message.reply_text(
            'Commands:\n'
            '/start - Start the bot\n'
            '/stop - Stop the bot\n'
            '/status - Check bot status\n'
            '/setnumber <number> - Set the starting number for messages\n'
            '/addchannel <channel_id> - Add a channel to send messages\n'
            '/removechannel <channel_id> - Remove a channel from the list\n'
            '/listchannels - List all added channels\n'
            '/settarget <channel_id> - Set a specific target channel\n'
            '/cleartarget - Clear the target channel (send to all channels)\n'
            '/adduser <user_id> - Add an authorized user (owner only)\n'
            '/removeuser <user_id> - Remove an authorized user (owner only)\n'
            '/listusers - List all authorized users (owner only)\n'
        )
    else:
        update.message.reply_text(
            'Commands:\n'
            '/start - Start the bot\n'
            '/stop - Stop the bot\n'
            '/status - Check bot status\n'
            '/setnumber <number> - Set the starting number for messages\n'
            '/addchannel <channel_id> - Add a channel to send messages\n'
            '/removechannel <channel_id> - Remove a channel from the list\n'
            '/listchannels - List all added channels\n'
            '/settarget <channel_id> - Set a specific target channel\n'
            '/cleartarget - Clear the target channel (send to all channels)\n'
        )

@restricted
def status(update, context):
    user_id = str(update.effective_user.id)
    if user_id in user_running_status and user_running_status[user_id]:
        update.message.reply_text('Bot is running.')
    else:
        update.message.reply_text('Bot is stopped.')

@restricted
def set_number(update, context):
    user_id = str(update.effective_user.id)
    try:
        number = int(context.args[0])
        user_starting_number[user_id] = number  # Update the starting number for the user
        update.message.reply_text(f'Starting number set to {number}.')
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /setnumber <number>')

@restricted
def add_channel(update, context):
    user_id = str(update.effective_user.id)
    if user_id not in user_channels:
        user_channels[user_id] = []

    try:
        channel_id = context.args[0]
        if channel_id not in user_channels[user_id]:
            user_channels[user_id].append(channel_id)
            update.message.reply_text(f'Channel {channel_id} added.')
        else:
            update.message.reply_text(f'Channel {channel_id} is already in the list.')
    except IndexError:
        update.message.reply_text('Usage: /addchannel <channel_id>')

@restricted
def remove_channel(update, context):
    user_id = str(update.effective_user.id)
    if user_id not in user_channels:
        update.message.reply_text('No channels found for this user.')
        return

    try:
        channel_id = context.args[0]
        if channel_id in user_channels[user_id]:
            user_channels[user_id].remove(channel_id)
            update.message.reply_text(f'Channel {channel_id} removed.')
        else:
            update.message.reply_text(f'Channel {channel_id} not found in the list.')
    except IndexError:
        update.message.reply_text('Usage: /removechannel <channel_id>')

@restricted
def list_channels(update, context):
    user_id = str(update.effective_user.id)
    if user_id in user_channels and user_channels[user_id]:
        update.message.reply_text('Added channels:\n' + '\n'.join(user_channels[user_id]))
    else:
        update.message.reply_text('No channels added.')

@restricted
def set_target(update, context):
    user_id = str(update.effective_user.id)
    try:
        channel_id = context.args[0]
        if channel_id in user_channels.get(user_id, []):
            user_target_channel[user_id] = channel_id
            update.message.reply_text(f'Target channel set to {channel_id}.')
        else:
            update.message.reply_text(f'Channel {channel_id} not found in your list.')
    except IndexError:
        update.message.reply_text('Usage: /settarget <channel_id>')

@restricted
def clear_target(update, context):
    user_id = str(update.effective_user.id)
    if user_id in user_target_channel:
        del user_target_channel[user_id]
        update.message.reply_text('Target channel cleared. Messages will be sent to all channels.')
    else:
        update.message.reply_text('No target channel set.')

@owner_only
def add_user(update, context):
    try:
        user_id = context.args[0]
        authorized_users.add(user_id)
        update.message.reply_text(f'User {user_id} authorized.')
    except IndexError:
        update.message.reply_text('Usage: /adduser <user_id>')

@owner_only
def remove_user(update, context):
    try:
        user_id = context.args[0]
        if user_id in authorized_users:
            authorized_users.remove(user_id)
            update.message.reply_text(f'User {user_id} unauthorized.')
        else:
            update.message.reply_text(f'User {user_id} not found in authorized list.')
    except IndexError:
        update.message.reply_text('Usage: /removeuser <user_id>')

@owner_only
def list_users(update, context):
    if authorized_users:
        update.message.reply_text('Authorized users:\n' + '\n'.join(authorized_users))
    else:
        update.message.reply_text('No authorized users.')

def send_messages(context, user_id, event):
    if user_id not in user_starting_number:
        context.bot.send_message(chat_id=user_id, text="Please set a starting number using /setnumber <number> before starting the bot.")
        user_running_status[user_id] = False
        return

    number = user_starting_number[user_id]  # Use the user's set starting number
    choices = ["...........Big", "..........Small"]
    colors = ["Red", "Green"]

    target_channel = user_target_channel.get(user_id)
    channels = user_channels.get(user_id, [])

    while user_running_status.get(user_id, False):
        if event.is_set():
            break
        selected_text = random.choice(choices)
        selected_color = random.choice(colors)
        message = f"{number} {selected_text} {selected_color}"
        print(f"Sending message: {message}")  # Debug statement

        if target_channel:
            if target_channel in channels:
                try:
                    context.bot.send_message(chat_id=target_channel, text=message)
                    print(f"Message sent to target channel: {target_channel}")  # Debug statement
                except Exception as e:
                    print(f"Failed to send message to {target_channel}: {e}")
            else:
                print(f"Target channel {target_channel} not found in user's channel list.")
        else:
            for channel in channels:
                try:
                    context.bot.send_message(chat_id=channel, text=message)
                    print(f"Message sent to channel: {channel}")  # Debug statement
                except Exception as e:
                    print(f"Failed to send message to {channel}: {e}")

        number += 1
        user_starting_number[user_id] = number  # Update the starting number for the user
        event.wait(60)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Add command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("setnumber", set_number))
    dp.add_handler(CommandHandler("addchannel", add_channel))
    dp.add_handler(CommandHandler("removechannel", remove_channel))
    dp.add_handler(CommandHandler("listchannels", list_channels))
    dp.add_handler(CommandHandler("settarget", set_target))
    dp.add_handler(CommandHandler("cleartarget", clear_target))
    dp.add_handler(CommandHandler("adduser", add_user))
    dp.add_handler(CommandHandler("removeuser", remove_user))
    dp.add_handler(CommandHandler("listusers", list_users))
    
    # Start the bot
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
