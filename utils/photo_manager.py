import os
import uuid
import aiohttp
import datetime
from pathlib import Path

PHOTOS_DIR = Path(os.getenv('PHOTOS_DIR', 'photos'))

def ensure_photos_dir():
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Save a photo (supports both message.document and image/* mime-type)
# and return the local path to the file.
async def save_photo_from_message(message) -> str:
    ensure_photos_dir()

    if getattr(message, 'photo', None):
        file_id = message.photo[-1].file_id
        original_filename = f"photo_{file_id}.jpg"

    elif getattr(message, 'document', None) and getattr(message.document, 'mime_type', '').startswith('image'):
        file_id = message.document.file_id
        # try to get the original file name, if any
        original_filename = getattr(message.document, 'file_name', f"doc_{file_id}.jpg")
    else:
        raise ValueError('No photo or image document in message')

    # Get info about the file from Telegram
    file = await message.bot.get_file(file_id)
    file_path = file.file_path

    # Create URL for downloading: https://api.telegram.org/file/bot<token>/<file_path>
    bot_token = getattr(message.bot, 'token', None)
    if not bot_token:
        raise RuntimeError('Bot token not available')

    file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

    # Create unique image file name
    ts = datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')
    unique = uuid.uuid4().hex[:8]

    ext = os.path.splitext(original_filename)[1] or '.jpg'
    filename = f"test_{ts}_{unique}{ext}"
    dest = PHOTOS_DIR / filename

    # Download via aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            if resp.status != 200:
                raise RuntimeError(f'Failed to download file, status={resp.status}')
            data = await resp.read()
            with open(dest, 'wb') as f:
                f.write(data)

    return str(dest)