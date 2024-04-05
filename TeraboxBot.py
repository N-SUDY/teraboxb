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
    bot_token="6979648310:AAFj6qlh9xnnDRMyGX_HUZUXkwmZCpPEdWg",
    api_id=1712043,
    api_hash="965c994b615e2644670ea106fd31daaf"
)

admin_ids = [6121699672, 1111214141]  # Add all admin IDs here
shortener = pyshorteners.Shortener()

# Create a temporary directory
temp_dir = tempfile.mkdtemp()

# Define the maximum file size in bytes (200MB)
MAX_FILE_SIZE = 350 * 1024 * 1024

# Specify a temporary file path within the temporary directory
temp_file_path = os.path.join(temp_dir, '@teraboxdownloader_xbot video.mp4')

# Initialize MongoDB client and database
ConnectionString = "mongodb+srv://smit:smit@cluster0.pjccvjk.mongodb.net/?retryWrites=true&w=majority"
client = pymongo.MongoClient(ConnectionString)
db = client["terabox"]
user_links_collection = db["user_links"]
plans_collection = db["plans"]

# Initialize plans
try:
    plans_collection.insert_many([
        {"_id": 4, "name": "30 days", "price": 40}
    ])

except:
    pass

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
    
def check_limit(user_id):
    user = user_links_collection.find_one({"user_id": user_id})
    if user:
        links_count = user.get("links_count", 0)
        last_conversion = user.get("last_conversion")
        if links_count >= 3 and datetime.now() - last_conversion < timedelta(days=1):
            return False
    return True

def update_limit(user_id):
    user = user_links_collection.find_one({"user_id": user_id})
    if user:
        links_count = user.get("links_count", 0) + 1
        user_links_collection.update_one({"user_id": user_id}, {
                                         "$set": {"links_count": links_count, "last_conversion": datetime.now()}})
    else:
        user_links_collection.insert_one(
            {"user_id": user_id, "links_count": 1, "last_conversion": datetime.now()})

async def subscribe_premium(bot, user_id, plan_id):
    # Retrieve plan details
    plan = plans_collection.find_one({"_id": plan_id})
    if not plan:
        return False
    user_links_collection.update_one({"user_id": user_id}, {"$set": {
                                     "plan_id": plan_id, "plan_name": plan["name"], "plan_price": plan["price"]}})
    try:
        await bot.send_message(user_id, f"**Congratulations! You have been subscribed to the {plan['name']} Validity.\nLinks Limit: Unlimited.**")
    except Exception as e:
        print(f"Failed to notify user {user_id}: {e}")

    return True

@bot.on_message(filters.command('adduser') & filters.private)
async def add_user_to_premium(bot, message):
    # Check if user is admin
    if message.from_user.id not in admin_ids:
        await bot.send_message(message.chat.id, "Only admin can add users to premium plans.")
        return

    # Parse command arguments
    try:
        _, user_identifier, plan_id_str = message.text.split(maxsplit=2)
        plan_id = int(plan_id_str)
    except ValueError:
        await bot.send_message(message.chat.id, "Invalid command format. Please use: /adduser @username_or_userID plan_id")
        return

    # Check if the plan exists
    plan = plans_collection.find_one({"_id": plan_id})
    if not plan:
        await bot.send_message(message.chat.id, "Invalid plan ID.")
        return

    # Get user ID from username or use user identifier directly
    try:
        user = await bot.get_users(user_identifier)
        user_id = user.id
    except ValueError:
        user_id = int(user_identifier)

    # Subscribe user to premium plan and notify the user
    success = await subscribe_premium(bot, user_id, plan_id)
    if success:
        await bot.send_message(message.chat.id, f"User {user_identifier} has been subscribed to the {plan['name']} premium plan.")
    else:
        await bot.send_message(message.chat.id, "**Failed to subscribe user to the premium plan.**")

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
    welcomemsg = (f"**Hello {message.from_user.first_name} 👋,\nSend me terabox links and i will download video for you.\n\nMade with ❤️ by @telebotsupdate**\nMade By : @mrxed_bot")
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


@bot.on_message(filters.command('plans') & filters.private)
async def plansList(bot, message):
    msg_text = ("<b>INR PRICING \n\n50₹ - 30 days**\n\nCRYPTO PRICING \n\n$1 - 30 days\n</b>")

    inline_keyboard = ikm(
        [[ikb("Buy Now ✅", url="https://t.me/mrxed_bot")]])
    await message.reply_text(msg_text, reply_markup=inline_keyboard)

@bot.on_message(filters.command('support') & filters.private)
async def support(bot, message):
    ContactUs = "**Contact US** : @mrxed_bot & @mrwhite7206_bot"
    await bot.send_message(message.chat.id,ContactUs)

# Function to download video using youtube-dl
async def download_video(url, temp_file_path):
    ydl_opts = {
        'format': 'best',
        'outtmpl': temp_file_path
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info_dict)
    return filename

@bot.on_message(filters.text & filters.private & check_joined())
async def teraBox(bot, message):
    user_id = message.from_user.id
    user = user_links_collection.find_one({"user_id": user_id})
    if not user:
        user_links_collection.insert_one(
            {"user_id": user_id, "links_count": 0, "last_conversion": datetime.now(), "plan_id": 0})
        user = user_links_collection.find_one({"user_id": user_id})

    plan_id = user.get("plan_id", 0)
    if plan_id == 0:
        if not check_limit(user_id):
            await bot.send_message(message.chat.id, "**You have reached your daily conversion limit. Limit Will resert tomorrow or You can Subscribe to a premium our plan. Click on /plans to see plans.**")
            return

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
        try:
            ShortUrl = shortener.tinyurl.short(LinkConvert)
        except:
            ShortUrl = shortener.dagd.short(LinkConvert)
        print(ShortUrl)
        with youtube_dl.YoutubeDL() as ydl:
            info = ydl.extract_info(ShortUrl, download=False)

# Create caption with size and duration
        caption = f"❤️ | Here's is your Download link: {ShortUrl}\n\n⚙️ | Video Downloaded Using @teraboxdownloader_xbot"
        if info.get('duration'):
            caption += f"\n🕒 Duration: {info['duration']} seconds"
        if info.get('filesize'):
            caption += f"\n📁 Size: {info['filesize'] / (1024 * 1024):.2f} MB"
        # Download the video using youtube-dl
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, '@teraboxdownloader_xbot video.mp4')
        VideoPath = await download_video(ShortUrl, temp_file_path)
    
        # Check if the file size is below the maximum threshold
        file_size = os.path.getsize(temp_file_path)
        if file_size <= MAX_FILE_SIZE:
            # Upload the video if it's below the maximum size
            await ProcessingMsg.delete()
            SendVideoMsg = await bot.send_message(message.chat.id, "📤")
            #caption = f"❤️ | Here's is your Download link: {ShortUrl}\n\n⚙️ |"
            await bot.send_video(
    message.chat.id,
    video=VideoPath,
    caption=caption,
    thumb=info.get('thumbnail'),
    disable_notification=True,  # Disable notification for silent send
    supports_streaming=True  # Enable streaming for larger files
)
            try:
                os.remove(VideoPath)
            except:
                pass
            try:
                os.remove(temp_dir)
            except:
                pass
            try:
                os.remove(temp_file_path)
            except:
                pass
            await SendVideoMsg.delete()

        else:
            # Send the direct download link if the video exceeds the size limit
            try:
                os.remove(VideoPath)
            except:
                pass
            try:
                os.remove(temp_dir)
            except:
                pass
            try:
                os.remove(temp_file_path)
            except:
                pass
            await bot.send_message(message.chat.id, f"**⚠️ This bot cannot upload videos more than 200mb in size on telegram. So we request you to download your video from the direct link given below 👇\n{ShortUrl}\n\nThanks For Patience**")

    except Exception as e:
        try:
            os.remove(VideoPath)
        except:
            pass
        try:
            os.remove(temp_dir)
        except:
            pass
        try:
            os.remove(temp_file_path)
        except:
            pass
        try:
            await SendVideoMsg.delete()
        except:
             pass       
        await ProcessingMsg.delete()
        ErrorMsg = await bot.send_message(message.chat.id, f"<code>Error: {e}</code>")
        await asyncio.sleep(3)
        await ErrorMsg.delete()

    finally:
        await ProcessingMsg.delete()
        try:
            await SendVideoMsg.delete()
        except:
             pass 
        shutil.rmtree(temp_dir)
        update_limit(user_id)

    
print("Started..")
bot.run()

