""""
Load environmemt virables
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Config:
    bot_token: str
    admin_ids: list[int]

def load_config():
    load_dotenv()
    return Config(
        bot_token=os.getenv("BOT_TOKEN"),
        admin_ids=[int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    )