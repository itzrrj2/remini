import os
import asyncio
from datetime import datetime, timedelta
from io import BytesIO

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

# Environment variables for security
API_ID = int(os.getenv("API_ID", 19593445))
API_HASH = os.getenv("API_HASH", "f78a8ae025c9131d3cc57d9ca0fbbc30")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7079552870:AAHr1vrLw_g3Hc_EcUeECDTS3baXESC2mJo")
ADMIN_ID = int(os.getenv("ADMIN_ID", 7174055187))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@sr_robots")
AR_HOSTING_API = os.getenv("AR_HOSTING_API", "https://ar-hosting.pages.dev/upload")

# Constants
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB
REQUEST_LIMIT = 300
MAX_RETRIES = 3
REQUEST_TIMEOUT = 5 * 60  # 5 minutes in seconds

# Initialize Pyrogram client
app = Client(
    "image_processing_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Storage for request deduplication
processed_requests = {}
last_cleanup = datetime.now()

async def cleanup_old_requests():
    global last_cleanup
    now = datetime.now()
    if (now - last_cleanup).seconds > REQUEST_TIMEOUT:
        for update_id, timestamp in list(processed_requests.items()):
            if (now - timestamp).seconds > REQUEST_TIMEOUT:
                del processed_requests[update_id]
        last_cleanup = now

async def send_message_with_retry(chat_id, text, reply_markup=None, max_retries=MAX_RETRIES):
    for attempt in range(max_retries):
        try:
            return await app.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup
            )
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1 * (attempt + 1))

async def is_user_in_channel(user_id):
    try:
        member = await app.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

async def enforce_channel_join(chat_id, user_id, name):
    if not await is_user_in_channel(user_id):
        buttons = [
            [InlineKeyboardButton("Join Channel ✅", url=f"https://t.me/{CHANNEL_ID[1:]}")],
            [InlineKeyboardButton("Check Join Status 🔍", callback_data="/checkjoin")],
            [InlineKeyboardButton("Refresh 🔄", callback_data="/refresh")]
        ]
        await send_message_with_retry(
            chat_id,
            f"Hey {name}\n\n✳️ You must join our channel to use this bot. Please join and verify your status.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        raise Exception("User not in channel")

async def upload_to_ar_hosting(file_bytes, filename):
    # Implement your AR Hosting API upload logic here
    # This is a placeholder - replace with actual implementation
    return f"https://example.com/{filename}"

async def process_image(image_url, tool):
    # Implement your image processing logic here
    # This is a placeholder - replace with actual implementation
    return f"https://reminisrbot.shresthstakeyt.workers.dev/{tool}/{image_url.split('/')[-1]}"

# Command handlers
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await cleanup_old_requests()
    
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    try:
        await enforce_channel_join(message.chat.id, user_id, name)
    except Exception:
        return
    
    buttons = [
        [InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton("Check Join Status 🔍", callback_data="/checkjoin")],
        [InlineKeyboardButton("Refresh 🔄", callback_data="/refresh")]
    ]
    
    await message.reply_text(
        f"Hey {name}\n\nWelcome to the REMINI PRO FREE Bot! Send an image to remove backgrounds, enhance, upscale, or host it permanently. 💛",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_message(filters.command("admin"))
async def admin_command(client, message: Message):
    admin_message = f"📋 <a href='https://t.me/{CHANNEL_ID[1:]}'>Admin Details:</a>\n\nThis bot is proudly developed by the SR BOTS.\n\nLearn more about us via the Admin Channel."
    buttons = [
        [InlineKeyboardButton("Admin Channel 📢", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton("Bots List 🦋", url="https://t.me/SR_robots/6")],
        [InlineKeyboardButton("Back to Menu ⬅️", callback_data="/menu")]
    ]
    await message.reply_text(
        admin_message,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    help_text = (
        "ℹ️ Commands:\n"
        "/start - Start the bot\n"
        "/about - Bot info\n"
        "/admin - Admin details\n"
        "/help - Show this message\n"
        "/checkjoin - Verify channel membership\n"
        "/restart - Reset bot interaction\n\n"
        "Send an image to process it!"
    )
    await message.reply_text(help_text)

# Image processing handlers
@app.on_message(filters.photo | filters.document)
async def handle_image_upload(client, message: Message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    try:
        await enforce_channel_join(message.chat.id, user_id, name)
    except Exception:
        return
    
    # Check if document is an image
    if message.document and not message.document.mime_type.startswith("image/"):
        await message.reply_text("❌ Only images are allowed. Please send a valid image file.")
        return
    
    # Get the file
    if message.photo:
        file_id = message.photo.file_id
        filename = "photo.jpg"
    else:
        file_id = message.document.file_id
        filename = message.document.file_name or "document.jpg"
    
    # Download the file
    try:
        msg = await message.reply_text("Uploading your photo to AR hosting, please wait...")
        file_path = await client.download_media(file_id, in_memory=True)
        
        # Upload to AR Hosting
        file_bytes = file_path.getbuffer()
        original_url = await upload_to_ar_hosting(file_bytes, filename)
        
        await msg.delete()
        
        if not original_url:
            raise Exception("Upload failed")
        
        # Create processing buttons
        buttons = [
            [
                InlineKeyboardButton("Enhance 🦋", callback_data=f"/enhance {original_url}"),
                InlineKeyboardButton("Remove BG 🦋", callback_data=f"/removebg {original_url}")
            ],
            [
                InlineKeyboardButton("Restore 🦋", callback_data=f"/restore {original_url}"),
                InlineKeyboardButton("Colorize 🦋", callback_data=f"/colorize {original_url}")
            ],
            [
                InlineKeyboardButton("Upscale 🦋", callback_data=f"/upscale {original_url}"),
                InlineKeyboardButton("View 🔰", url=original_url)
            ],
            [
                InlineKeyboardButton("Permanent Link 🖇️", callback_data=f"/permanent {original_url}"),
                InlineKeyboardButton("Back to Menu ⬅️", callback_data="/menu")
            ]
        ]
        
        await message.reply_text(
            "✅ Image uploaded successfully! Choose an action:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        await message.reply_text(f"❌ An error occurred: {str(e)}")
        buttons = [
            [InlineKeyboardButton("Retry 🔄", callback_data=f"/retry_upload {file_id}")],
            [InlineKeyboardButton("Back to Menu ⬅️", callback_data="/menu")]
        ]
        await message.reply_text(
            "❌ Error processing your image.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

# Callback query handlers
@app.on_callback_query()
async def handle_callback_query(client, callback_query: CallbackQuery):
    data = callback_query.data
    message = callback_query.message
    user_id = callback_query.from_user.id
    name = callback_query.from_user.first_name
    
    try:
        await enforce_channel_join(message.chat.id, user_id, name)
    except Exception:
        return
    
    if data == "/checkjoin":
        if await is_user_in_channel(user_id):
            await callback_query.answer("✅ You are a member of the channel!")
            await message.edit_text("✅ You are a member of the channel! You can use the bot.")
        else:
            await enforce_channel_join(message.chat.id, user_id, name)
        return
    
    elif data == "/refresh":
        if await is_user_in_channel(user_id):
            await callback_query.answer("✅ Channel membership verified!")
            await message.edit_text("✅ Channel membership verified! You can use the bot.")
        else:
            await enforce_channel_join(message.chat.id, user_id, name)
        return
    
    elif data == "/menu":
        buttons = [
            [InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{CHANNEL_ID[1:]}")],
            [InlineKeyboardButton("Check Join Status 🔍", callback_data="/checkjoin")],
            [InlineKeyboardButton("Help ℹ️", callback_data="/help")]
        ]
        await message.edit_text(
            "📋 Main Menu: Send an image or choose an option.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    elif data.startswith(("/enhance", "/removebg", "/restore", "/colorize", "/upscale")):
        tool = data.split()[0][1:]  # Remove leading slash
        tool_name = tool.capitalize()
        image_url = data.split()[1]
        
        await callback_query.answer(f"{tool_name}ing your image...")
        processing_msg = await message.reply_text(f"{tool_name}ing your image, please wait...")
        
        try:
            result_image_url = await process_image(image_url, tool)
            
            if not result_image_url:
                raise Exception(f"{tool_name} failed")
            
            # Download processed image
            async with httpx.AsyncClient() as client:
                response = await client.get(result_image_url)
                file_bytes = BytesIO(response.content)
                file_bytes.name = f"{tool}_image.jpg"
            
            # Send as photo if small enough
            if len(response.content) <= MAX_PHOTO_SIZE:
                await message.reply_photo(
                    photo=file_bytes,
                    caption=f"✅ Image {tool}ed successfully!\nBy - @TrumpTrBot"
                )
            
            # Always send as document
            await message.reply_document(
                document=file_bytes,
                caption=f"✅ Here's the {tool}ed image as a document."
            )
            
            buttons = [
                [InlineKeyboardButton("Back to Menu ⬅️", callback_data="/menu")]
            ]
            await message.reply_text(
                "✅ Processing complete! What next?",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            
        except Exception as e:
            await message.reply_text(f"❌ Error {tool}ing the image: {str(e)}")
            buttons = [
                [InlineKeyboardButton("Retry 🔄", callback_data=data)],
                [InlineKeyboardButton("Back to Menu ⬅️", callback_data="/menu")]
            ]
            await message.reply_text(
                f"❌ Error {tool}ing the image.",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        
        finally:
            await processing_msg.delete()
    
    elif data.startswith("/permanent"):
        image_url = data.split()[1]
        uploading_msg = await message.reply_text("Uploading to SR hosting, please wait...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                file_bytes = BytesIO(response.content)
                file_bytes.name = "permanent.jpg"
                permanent_url = await upload_to_ar_hosting(file_bytes, "permanent.jpg")
                
                if not permanent_url:
                    raise Exception("Upload failed")
                
                buttons = [
                    [InlineKeyboardButton("View Image 🌟", url=permanent_url)],
                    [InlineKeyboardButton("Back to Menu ⬅️", callback_data="/menu")]
                ]
                await message.reply_text(
                    f"✅ Image uploaded to SR hosting!\nPermanent link:\n{permanent_url}",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
        
        except Exception as e:
            await message.reply_text(f"❌ Error uploading to SR hosting: {str(e)}")
            buttons = [
                [InlineKeyboardButton("Retry 🔄", callback_data=data)],
                [InlineKeyboardButton("Back to Menu ⬅️", callback_data="/menu")]
            ]
            await message.reply_text(
                "❌ Error uploading to SR hosting.",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        
        finally:
            await uploading_msg.delete()
    
    elif data.startswith("/retry_upload"):
        file_id = data.split()[1]
        await callback_query.answer("Retrying upload...")
        
        try:
            msg = await message.reply_text("Retrying upload to SR hosting, please wait...")
            file_path = await client.download_media(file_id, in_memory=True)
            file_bytes = file_path.getbuffer()
            original_url = await upload_to_ar_hosting(file_bytes, "retry.jpg")
            
            await msg.delete()
            
            if not original_url:
                raise Exception("Upload failed")
            
            buttons = [
                [
                    InlineKeyboardButton("Enhance 🦋", callback_data=f"/enhance {original_url}"),
                    InlineKeyboardButton("Remove BG 🦋", callback_data=f"/removebg {original_url}")
                ],
                [
                    InlineKeyboardButton("Restore 🦋", callback_data=f"/restore {original_url}"),
                    InlineKeyboardButton("Colorize 🦋", callback_data=f"/colorize {original_url}")
                ],
                [
                    InlineKeyboardButton("Upscale 🦋", callback_data=f"/upscale {original_url}"),
                    InlineKeyboardButton("View 🔰", url=original_url)
                ],
                [
                    InlineKeyboardButton("Permanent Link 🖇️", callback_data=f"/permanent {original_url}"),
                    InlineKeyboardButton("Back to Menu ⬅️", callback_data="/menu")
                ]
            ]
            await message.reply_text(
                "✅ Retry successful! Choose an action:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        
        except Exception as e:
            await message.reply_text(f"❌ Retry failed: {str(e)}")
            buttons = [
                [InlineKeyboardButton("Retry 🔄", callback_data=data)],
                [InlineKeyboardButton("Back to Menu ⬅️", callback_data="/menu")]
            ]
            await message.reply_text(
                "❌ Retry failed.",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

# Start the bot
if __name__ == "__main__":
    print("Starting bot...")
    app.run()
