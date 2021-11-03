import time

from telethon import events, utils
from telethon.sync import TelegramClient
from telethon.tl import types

from FastTelethon import download_file, upload_file
import os
from dotenv import load_dotenv

load_dotenv()
api_id: int = os.getenv('api_id')
api_hash: str = os.getenv('api_hash')
token = os.getenv('token')
client = TelegramClient("bot", api_id, api_hash)

client.start(bot_token=token)


class Timer:
    def __init__(self, time_between=2):
        self.start_time = time.time()
        self.time_between = time_between

    def can_send(self):
        if time.time() > (self.start_time + self.time_between):
            self.start_time = time.time()
            return True
        return False


@client.on(events.NewMessage())
async def download_or_upload(event):
    type_of = ""
    msg = None
    timer = Timer()

    async def progress_bar(current, total):
        if timer.can_send():
            await msg.edit("{} {:.2f}%".format(type_of, current * 100 / total))

    if event.document:
        type_of = "download"
        msg = await event.reply("downloading started")
        with open('downloads/'+event.file.name, "wb") as out:
            await download_file(event.client, event.document, out, progress_callback=progress_bar)
        await msg.edit("Finished downloading")


client.run_until_disconnected()
