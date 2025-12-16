import os
import uuid
import aiohttp
from datetime import datetime
from pathlib import Path

PHOTOS_DIR = Path(os.getenv('PHOTOS_DIR', 'photos'))

def ensure_photos_dir():
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

async def save_photo_from_message(message) -> str:
    """
    Сохранить фото (поддерживает и message.photo и message.document с image/* mime-type)
    и вернуть локальный путь к файлу.
    """
    ensure_photos_dir()

    # Если это обычное photo (варианты размеров)
    if getattr(message, 'photo', None):
        file_id = message.photo[-1].file_id
        original_filename = f"photo_{file_id}.jpg"
    # Если это document (например, когда "compress image" выключен)
    elif getattr(message, 'document', None) and getattr(message.document, 'mime_type', '').startswith('image'):
        file_id = message.document.file_id
        # Попробуем взять оригинальное имя, если есть
        original_filename = getattr(message.document, 'file_name', f"doc_{file_id}.jpg")
    else:
        raise ValueError('No photo or image document in message')

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
    # Сохраняем с расширением из оригинального имени, если возможно
    ext = os.path.splitext(original_filename)[1] or '.jpg'
    filename = f"test_{ts}_{unique}{ext}"
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