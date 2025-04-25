import os
import asyncio
from io import BytesIO
from typing import Optional
import httpx

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.errors import UserNotParticipant

# Environment variables (from our chat)
API_ID = int(os.getenv("API_ID", 19593445))
API_HASH = os.getenv("API_HASH", "f78a8ae025c9131d3cc57d9ca0fbbc30")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7079552870:AAHr1vrLw_g3Hc_EcUeECDTS3baXESC2mJo")
ADMIN_ID = int(os.getenv("ADMIN_ID", 7174055187))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@SR_ROBOTS")
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "https://reminisrbot.shresthstakeyt.workers.dev/")
AR_HOSTING_API = os.getenv("AR_HOSTING_API", "https://ar-hosting.pages.dev/upload")

# Initialize Pyrogram client (from our chat)
app = Client(
    "image_processing_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Image processing functions (from our chat)
async def process_image(image_url: str, tool: str) -> Optional[str]:
    """Process image using the API we discussed"""
    tools = {
        'upscale': 'upscale',
        'restore': 'restore',
        'enhance': 'enhance',
        'removebg': 'removebg',
        'colorize': 'colorize'
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://reminisrbot.shresthstakeyt.workers.dev/",
                params={
                    'url': image_url,
                    'tool': tools[tool],
                    'key': IMAGE_API_KEY
                },
                timeout=30
            )
            data = response.json()
            return data.get('result', {}).get('resultImageUrl')
    except Exception as e:
        print(f"Error processing image ({tool}): {e}")
        return None

async def upload_to_ar_hosting(file_bytes: BytesIO, filename: str) -> Optional[str]:
    """Upload to AR Hosting as we discussed"""
    try:
        async with httpx.AsyncClient() as client:
            files = {'file': (filename, file_bytes.getvalue())}
            response = await client.post(AR_HOSTING_API, files=files)
            return response.json().get('data')
    except Exception as e:
        print(f"AR Hosting upload error: {e}")
        return None

# Channel verification (improved from our chat)
async def verify_channel_membership(user_id: int) -> bool:
    """Check if user is in channel"""
    try:
        member = await app.get_chat_member(
            CHANNEL_ID[1:] if CHANNEL_ID.startswith('@') else int(CHANNEL_ID),
            user_id
        )
        return member.status in ["member", "administrator", "creator"]
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Membership check error: {e}")
        return False

async def enforce_membership(message: Message) -> bool:
    """Enforce channel membership with buttons"""
    if await verify_channel_membership(message.from_user.id):
        return True
        
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton("Verify Join", callback_data="verify_join")]
    ])
    
    await message.reply_text(
        "🔒 Please join our channel to use this bot:",
        reply_markup=buttons
    )
    return False

# Command handlers (from our chat)
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    if not await enforce_membership(message):
        return
        
    await message.reply_text(
        "🖼️ Send me an image to process!\n"
        "Available operations:\n"
        "- Upscale\n- Enhance\n- Remove BG\n- Restore\n- Colorize",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Help", callback_data="help")]
        ])
    )

@app.on_callback_query(filters.regex("^verify_join$"))
async def verify_join_callback(client, callback: CallbackQuery):
    if await verify_channel_membership(callback.from_user.id):
        await callback.answer("✅ Verified!")
        await callback.message.edit_text("Thank you! You can now use the bot.")
    else:
        await callback.answer("❌ You haven't joined yet!", show_alert=True)

# Image processing handler (from our chat)
@app.on_message(filters.photo | filters.document)
async def handle_image(client, message: Message):
    if not await enforce_membership(message):
        return

    # Download image
    msg = await message.reply("⬇️ Downloading image...")
    try:
        file_path = await message.download(in_memory=True)
        file_bytes = BytesIO(file_path.getbuffer())
        
        # Upload to AR Hosting (from our chat)
        await msg.edit_text("☁️ Uploading to AR Hosting...")
        file_url = await upload_to_ar_hosting(file_bytes, "image.jpg")
        if not file_url:
            raise Exception("Upload failed")
            
        # Process image (from our chat)
        await msg.edit_text("🔄 Processing image...")
        processed_url = await process_image(file_url, "enhance")
        if not processed_url:
            raise Exception("Processing failed")
            
        # Send result
        await msg.delete()
        await message.reply_photo(
            processed_url,
            caption="✅ Enhanced image",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Download", url=processed_url)],
                [
                    InlineKeyboardButton("Upscale", callback_data=f"upscale_{processed_url}"),
                    InlineKeyboardButton("Remove BG", callback_data=f"removebg_{processed_url}")
                ]
            ])
        )
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")
        print(f"Image processing error: {e}")

# Callback handlers (from our chat)
@app.on_callback_query(filters.regex("^(upscale|removebg)_"))
async def process_callback(client, callback: CallbackQuery):
    action, image_url = callback.data.split('_', 1)
    await callback.answer(f"⏳ {action.capitalize()}ing image...")
    
    try:
        processed_url = await process_image(image_url, action)
        if processed_url:
            await callback.message.reply_photo(
                processed_url,
                caption=f"✅ {action.capitalize()}ed image"
            )
        else:
            await callback.answer("❌ Processing failed", show_alert=True)
    except Exception as e:
        await callback.answer(f"Error: {str(e)}", show_alert=True)
        print(f"Callback error: {e}")

# Start the bot (from our chat)
print("✅ Bot is running...")
app.run()
