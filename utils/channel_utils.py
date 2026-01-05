import re
import logging

logger = logging.getLogger(__name__)

def parse_channel_input(channel_input: str) -> str:
	"""
	Converts various channel link formats to @username or ID
	Recognizes:
	- https://t.me/channel_name
	- http://t.me/channel_name
	- t.me/channel_name
	- @channel_name
	- channel_name (without the @)
	- -1001234567890 (channel ID)

	Returns: @channel_name or the original text (if it's an ID or already a @username)
	"""
	if not channel_input or not isinstance(channel_input, str):
		return channel_input

	channel_input = channel_input.strip()

	if channel_input.startswith('@'):
		username = channel_input[1:]
		if is_valid_username(username):
			return channel_input
		else:
			return channel_input  # Still return, but channel name could be incorrect

	# Checkinf if it's a channel ID (starts with -100 and then only numbers)
	if channel_input.startswith('-100') and channel_input[4:].isdigit():
		return channel_input

	# Patterns for link recognition
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

	if is_valid_username(channel_input):
		return f"@{channel_input}"

	return channel_input


def is_valid_username(username: str) -> bool:
	if not username or len(username) < 5 or len(username) > 32:
		return False

	# Telegram usernames can contain a-z, 0-9, and underscores
	# Must start with a letter (but in reality can start with numbers too)
	pattern = r'^[a-zA-Z0-9_]+$'
	return bool(re.match(pattern, username))


def extract_channel_info(channel_input: str) -> dict:
	parsed = parse_channel_input(channel_input)

	if parsed.startswith('@'):
		return {'type': 'username', 'value': parsed}
	elif parsed.startswith('-100') and parsed[4:].isdigit():
		return {'type': 'id', 'value': parsed}
	else:
		return {'type': 'unknown', 'value': parsed}


