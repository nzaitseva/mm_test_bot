import os
import uuid
import aiohttp
from datetime import datetime
from pathlib import Path

PHOTOS_DIR = Path(os.getenv('PHOTOS_DIR', 'photos'))

def ensure_photos_dir():
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

async def save_photo_from_message(message) -> str:
    """Сохранить самое большое фото из message.photo в папку photos и вернуть путь.

    Использует Telegram File API через bot.get_file + скачивание по URL.
    Возвращает абсолютный путь как строку.
    """
    ensure_photos_dir()

    if not getattr(message, 'photo', None):
        raise ValueError('No photo in message')

    # Берём самый большой вариант фото
    photo = message.photo[-1]
    file_id = photo.file_id

    # Получаем информацию о файле у Telegram
    file = await message.bot.get_file(file_id)
    file_path = file.file_path

    # Формируем URL для скачивания: https://api.telegram.org/file/bot<token>/<file_path>
    bot_token = getattr(message.bot, 'token', None)
    if not bot_token:
        raise RuntimeError('Bot token not available')

    file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

    # Уникальное имя
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    unique = uuid.uuid4().hex[:8]
    filename = f"test_{ts}_{unique}.jpg"
    dest = PHOTOS_DIR / filename

    # Скачиваем через aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            if resp.status != 200:
                raise RuntimeError(f'Failed to download file, status={resp.status}')
            data = await resp.read()
            with open(dest, 'wb') as f:
                f.write(data)

    return str(dest)
