import re
from utils.emoji import Emoji as E

def parse_channel_input(channel_input: str) -> str:
	"""
	Преобразует различные форматы ссылок на каналы в @username или ID
	Распознаёт:
	- https://t.me/channel_name
	- http://t.me/channel_name
	- t.me/channel_name
	- @channel_name
	- channel_name (без @)
	- -1001234567890 (ID канала)

	Возвращает: @channel_name или исходный текст (если это ID или уже @username)
	"""
	if not channel_input or not isinstance(channel_input, str):
		return channel_input

	channel_input = channel_input.strip()

	# Если уже @username или числовой ID, возвращаем как есть
	if channel_input.startswith('@'):
		# Проверяем валидность username после @
		username = channel_input[1:]
		if is_valid_username(username):
			return channel_input
		else:
			return channel_input  # Все равно возвращаем, но это может быть некорректным

	# Проверяем на ID канала (начинается с -100 и затем только цифры)
	if channel_input.startswith('-100') and channel_input[4:].isdigit():
		return channel_input

	# Паттерны для распознавания ссылок
	patterns = [
		r'https?://(?:www\.)?t\.me/([a-zA-Z0-9_]+)(?:/.*)?$',  # https://t.me/channel_name
		r'https?://(?:www\.)?telegram\.me/([a-zA-Z0-9_]+)(?:/.*)?$',  # https://telegram.me/channel_name
		r't\.me/([a-zA-Z0-9_]+)(?:/.*)?$',  # t.me/channel_name
		r'telegram\.me/([a-zA-Z0-9_]+)(?:/.*)?$',  # telegram.me/channel_name
	]

	for pattern in patterns:
		match = re.search(pattern, channel_input)
		if match:
			username = match.group(1)
			if is_valid_username(username):
				return f"@{username}"

	# Если ввод выглядит как username (только буквы, цифры, подчеркивания)
	if is_valid_username(channel_input):
		return f"@{channel_input}"

	# Если ничего не распознано, возвращаем исходный текст
	# TODO: возвращать ошибку и поде ввода повторно, вместо исходного текста
	return channel_input


def is_valid_username(username: str) -> bool:
	"""Проверяет, является ли строка валидным username телеграм"""
	if not username or len(username) < 5 or len(username) > 32:
		return False

	# Telegram usernames can contain a-z, 0-9, and underscores
	# Must start with a letter (but in reality can start with numbers too)
	pattern = r'^[a-zA-Z0-9_]+$'
	return bool(re.match(pattern, username))


def extract_channel_info(channel_input: str) -> dict:
	"""
	Извлекает информацию о канале из различных форматов
	"""
	parsed = parse_channel_input(channel_input)

	if parsed.startswith('@'):
		return {'type': 'username', 'value': parsed}
	elif parsed.startswith('-100') and parsed[4:].isdigit():
		return {'type': 'id', 'value': parsed}
	else:
		return {'type': 'unknown', 'value': parsed}


# Тестовая функция
def test_parse_channel_input():
	test_cases = [
		("https://t.me/channel_name", "@channel_name"),
		("http://t.me/channel_name", "@channel_name"),
		("t.me/channel_name", "@channel_name"),
		("https://t.me/channel_name/123", "@channel_name"),
		("@channel_name", "@channel_name"),
		("channel_name", "@channel_name"),
		("-1001234567890", "-1001234567890"),
		("https://t.me/joinchat/ABCDEF", "https://t.me/joinchat/ABCDEF"),
		("", ""),
		("invalid@username", "invalid@username"),
	]

	logger.info("🔍 Тестирование парсера каналов:")
	for input_text, expected in test_cases:
		result = parse_channel_input(input_text)
		status = f"{E.SUCCESS}" if result == expected else f"{E.ERROR}"
		logger.info(f"{status} '{input_text}' -> '{result}' (expected: '{expected}')")


if __name__ == "__main__":
	test_parse_channel_input()