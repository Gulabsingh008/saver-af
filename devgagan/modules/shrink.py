from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import random
import requests
import string
import aiohttp
from devgagan import app
from devgagan.core.func import *
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB, WEBSITE_URL, AD_API # you can edit this by any short link provider

# MongoDB setup
tclient = AsyncIOMotorClient(MONGO_DB)
tdb = tclient["telegram_bot"]
token = tdb["tokens"]

# Create a TTL index for sessions collection
async def create_ttl_index():
    await token.create_index("expires_at", expireAfterSeconds=0)


# In-memory parameter storage
Param = {}


async def generate_random_param(length=8):
    """Generate a random parameter."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def get_shortened_url(deep_link):
    api_url = f"https://{WEBSITE_URL}/api?api={AD_API}&url={deep_link}"
    
    # Use aiohttp to perform an asynchronous request
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status == 200:
                data = await response.json()  # Get the JSON response asynchronously
                if data.get("status") == "success":
                    return data.get("shortenedUrl")
    return None


async def is_user_verified(user_id):
    """Check if a user has an active session."""
    session = await token.find_one({"user_id": user_id})
    return session is not None


@app.on_message(filters.command("start"))
async def token_handler(client, message):
    """Handle the /token command."""
    join = await subscribe(client, message)
    if join == 1:
        return
    user_id = message.chat.id
    if len(message.command) <= 1:
        image_url = "https://i.ibb.co/PZJRN57d/photo-2025-07-09-15-05-52-7525098747760476176.jpg"
        join_button = InlineKeyboardButton("Join Channel", url="https://t.me/team_zozo_pro")
        premium = InlineKeyboardButton("Get Premium", url="https://t.me/team_zozo_x_bot")  # Callback for Help button
        keyboard = InlineKeyboardMarkup([
            [join_button],  # First button
            [premium]   # Second button
        ])
        # Send the message with the image and keyboard
        await message.reply_photo(
            photo=image_url,
            caption=(
                "🚀 𝙒𝙚𝙡𝙘𝙤𝙢𝙚 𝙩𝙤 𝙏𝙀𝘼𝙈 𝙕𝙤𝙯𝙤 — 𝙔𝙤𝙪𝙧 𝙍𝙚𝙨𝙩𝙧𝙞𝙘𝙩𝙚𝙙 𝘾𝙤𝙣𝙩𝙚𝙣𝙩 𝙐𝙣𝙡𝙤𝙘𝙠𝙚𝙧! 🔓\n\n"
                "👋 𝙒𝙝𝙖𝙩 𝙄 𝘿𝙤:\n"
                "🔹 Bypass \"Forwarding Restricted\" posts from Telegram channels & groups\n"
                "🔹 Instantly retrieve content from public channels\n"
                "🔹 Support for *private content* (with login)\n"
                "🔹 *Also supports downloading from YouTube, Instagram & more!* 🎬\n"
                "🔹 *Use* `/login` *for private content, and* `/help` *to learn more*\n\n"
                "📥 𝙃𝙤𝙬 𝙏𝙤 𝙐𝙨𝙚:\n"
                "1. 🔗 Send me any *Telegram post link*\n"
                "2. 🧠 I’ll unlock & show you the *full content*\n"
                "3. 🔒 For private channels — Login required\n\n"
                "✨ 𝙁𝙚𝙖𝙩𝙪𝙧𝙚𝙨:\n"
                "✅ Access restricted posts with ease\n"
                "✅ Works with both *Public* & *Private* channels\n"
                "✅ Super-fast & Accurate\n"
                "✅ Clean & Simple to use\n\n"
                "📌 𝙄𝙢𝙥𝙤𝙧𝙩𝙖𝙣𝙩:\n"
                "> Check /terms, /plan & /help before using\n"
                "> 👉 *Owner? Run* `/set` *once to setup all commands*\n\n"
                "🔧 𝙈𝙖𝙞𝙣𝙩𝙖𝙞𝙣𝙚𝙙 𝙗𝙮: @team_zozo_pro"
            ),
            reply_markup=keyboard
        )

        return  
        
    param = message.command[1] if len(message.command) > 1 else None
    freecheck = await chk_user(message, user_id)
    if freecheck != 1:
        await message.reply("You are a premium user no need of token 😉")
        return

    # Handle deep link with parameter
    if param:
        if user_id in Param and Param[user_id] == param:
            # Add user to MongoDB as a verified user for the next 6 hours
            await token.insert_one({
                "user_id": user_id,
                "param": param,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=3),
            })
            del Param[user_id]  # Remove the parameter from Param
            await message.reply("✅ You have been verified successfully! Enjoy your session for next 3 hours.")
            return
        else:
            await message.reply("❌ Invalid or expired verification link. Please generate a new token.")
            return

@app.on_message(filters.command("token"))
async def smart_handler(client, message):
    user_id = message.chat.id
    # Check if the user is already verified or premium
    freecheck = await chk_user(message, user_id)
    if freecheck != 1:
        await message.reply("You are a premium user no need of token 😉")
        return
    if await is_user_verified(user_id):
        await message.reply("✅ Your free session is already active enjoy!")
    else:
        # Generate a session and send the link
        param = await generate_random_param()
        Param[user_id] = param  # Store the parameter in Param dictionary

        # Create a deep link
        deep_link = f"https://t.me/{client.me.username}?start={param}"

        # Get shortened URL
        shortened_url = await get_shortened_url(deep_link)
        if not shortened_url:
            await message.reply("❌ Failed to generate the token link. Please try again.")
            return

        # Create a button with the shortened link
        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Verify the token now...", url=shortened_url)]]
        )
        await message.reply("Click the button below to verify your free access token: \n\n> What will you get ? \n1. No time bound upto 3 hours \n2. Batch command limit will be FreeLimit + 20 \n3. All functions unlocked", reply_markup=button)
