import os
import pyshorteners
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton as ikb, InlineKeyboardMarkup as ikm
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from terabox import getUrl
import pymongo
import asyncio
import youtube_dl
import tempfile
import shutil


bot = Client(
    "TerdaB",
    bot_token="6792537813:AAHMchO1Dlxs6vvcldQFeqA268pL0Cw6znE",
    api_id=1712043,
    api_hash="965c994b615e2644670ea106fd31daaf"
)

admin_ids = [6121699672, 1111214141]  # Add all admin IDs here
shortener = pyshorteners.Shortener()


# Define the maximum file size in bytes (200MB)
# Specify a temporary file path within the temporary directory
# Initialize MongoDB client and database
ConnectionString = "mongodb+srv://smit:smit@cluster0.pjccvjk.mongodb.net/?retryWrites=true&w=majority"
client = pymongo.MongoClient(ConnectionString)
db = client["terabox"]
user_links_collection = db["user_links"]

# Initialize plans

channel_username = "@TeleBotsUpdate"

def check_joined():
    async def func(flt, bot, message):
        join_msg = f"**To use this bot, Please join our channel.\nJoin From The Link Below 👇**"
        user_id = message.from_user.id
        chat_id = message.chat.id
        try:
            member_info = await bot.get_chat_member(channel_username, user_id)
            if member_info.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER):
                return True
            else:
                await bot.send_message(chat_id, join_msg , reply_markup=ikm([[ikb("✅ Join Channel", url="https://t.me/TeleBotsUpdate")]]))
                return False
        except Exception as e:
            await bot.send_message(chat_id, join_msg , reply_markup=ikm([[ikb("✅ Join Channel", url="https://t.me/TeleBotsUpdate")]]))
            return False

    return filters.create(func)
    

@bot.on_message(filters.command('stats') & filters.private)
async def get_users_info(bot, message):
    # Check if user is admin
    if message.from_user.id not in admin_ids:
        await message.reply_text("**You are not authorized to use this command.**")
        return

    # Check if the command is for premium users list
    if len(message.command) > 1 and message.command[1].lower() == 'premium':
        # Get all premium users
        premium_users = user_links_collection.find({"plan_id": {"$ne": 0}})
        
        # Prepare response message
        response_msg = "Premium Users List:\n"
        for user in premium_users:
            response_msg += (
                f"User ID: {user['user_id']}, "
                f"Plan: {user.get('plan_name', 'Unknown')}, "
                f"Price: {user.get('plan_price', 0)}\n"
            )
    else:
        # Get the count of premium users
        premium_users_count = user_links_collection.count_documents({"plan_id": {"$ne": 0}})

        # Get the count of free users
        free_users_count = user_links_collection.count_documents({"plan_id": 0})

        # Get the total number of users
        total_users_count = user_links_collection.count_documents({})

        # Prepare response message
        response_msg = (
            "<b>Statistics 📊</b>\n\n"
            f"⚡️ |<b> Premium Users: </b>{premium_users_count}\n"
            f"🆓 |<b> Free Users: </b>{free_users_count}\n"
            f"👥 |<b> Total Users: </b>{total_users_count}\n\n"
            "\t**Use** '/stats premium' <b>to view Premium users List</b>\n\n"
        )

    await message.reply_text(response_msg)

@bot.on_message(filters.command('start') & filters.private)
async def start(bot, message):
    welcomemsg = (f"**Hello {message.from_user.first_name} 👋,\nSend me terabox links and i will download video for you.")
    inline_keyboard = ikm(
    [
        [
            ikb("🪲 Report Bugs", url="https://t.me/telebotsupdategroup"),
            ikb("☎️ Support Channel", url="https://t.me/TeleBotsUpdate")
        ]
    ]
)

    await message.reply_text(welcomemsg, reply_markup=inline_keyboard)

@bot.on_message(filters.command("broadcast") & filters.private)
async def broadcast_message(bot, message: Message):
    # Check if user is admin
    if message.from_user.id not in admin_ids:
        await message.reply_text("You are not authorized to use this command.")
        return

    # If the user replied to a text message
    if message.reply_to_message and message.reply_to_message.text:
        # Extract the text
        msg = message.reply_to_message.text
    else:
        await message.reply_text("You need to reply to a text message to broadcast it.")
        return

    # Get all users using the bot
    users = user_links_collection.find({})

    total_users = 0
    success_count = 0
    error_count = 0

    # Count total number of users
    total_users = user_links_collection.count_documents({})
    print(f"Total number of users: {total_users}")

    await message.reply_text("Broadcasting...")

    # Send the message to all users
    for user in users:
        try:
            # Broadcasting the text message without parse_mode
            await bot.send_message(user['user_id'], msg)
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"Failed to send broadcast message to user {user['user_id']}: {e}")

    await message.reply_text(f"Broadcast message sent to {success_count} users with {error_count} errors.")

@bot.on_message(filters.command('admin') & filters.private)
async def admincommand(bot,message):
    if message.from_user.id not in admin_ids:
        await bot.send_message(message.chat.id, "Only admin can Use this command. 🥲")
        return
    
    await bot.send_message(message.chat.id,
                           "<b>Admin Commands </b>😁\n\n"
                           "/adduser <b>: to add user to premium plan. </b>\n"
                           "/stats <b>: to check how many users are using the bot.</b>\n" 
                           "/broadcast <b>: to broadcast a message to all the users. </b> \n"
                           )

@bot.on_message(filters.command("info") & filters.private)
async def user_info(bot, message):
    user_id = message.from_user.id
    user = user_links_collection.find_one({"user_id": user_id})
    
    if user:
        plan_name = user.get("plan_name", "Free")
        plan_price = user.get("plan_price", 0)
        
        response_msg = f"User ID: {user_id}\n"
        response_msg += f"Plan: {plan_name} (Price: {plan_price})\n"
    else:
        response_msg = "No plan subscribed"
    
    await message.reply_text(response_msg)



# Function to download video using youtube-dl
@bot.on_message(filters.text & filters.private & check_joined())
async def teraBox(bot, message):
    user_id = message.from_user.id

   

    msg = message.text
    print(msg)
    if message.from_user.username:
        user_id_text = f"🆔 | User ID: [{user_id}](http://telegram.me/{message.from_user.username})"
    else:
        user_id_text = f"🆔 | User ID: [{user_id}](tg://user?id={user_id})"

    await bot.send_message(
    -1001855899992,
    f"{user_id_text}\n"
    f"🔗 | Link: {msg}"
    )
    
    ProcessingMsg = await bot.send_message(message.chat.id, "📥")
    try:
        LinkConvert = getUrl(msg)
        ShortUrl = shortener.tinyurl.short(LinkConvert)
        print(ShortUrl)
        await bot.send_message(message.chat.id, f"<b>📥 | Here's your shortened link:\n{ShortUrl}\n\n🚫 | If you are not getting any video below.\nThen try downloading video manually using the link provided above. \n\n Join https://t.me/terabox_updates_x for bot updates.</b>")
        # Download the video using youtube-dl


    except Exception as e:       
        await ProcessingMsg.delete()
        ErrorMsg = await bot.send_message(message.chat.id, f"<code>Error: {e}</code>")
        await asyncio.sleep(3)
        await ErrorMsg.delete()

    finally:
        await ProcessingMsg.delete()
    

    
print("Started..")
bot.run()
