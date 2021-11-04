import time

from telethon import events, utils
from telethon.sync import TelegramClient
from telethon.tl import types

from FastTelethon import download_file, upload_file
import os
from os import listdir
from os.path import isfile, join
import shutil
from dotenv import load_dotenv

load_dotenv()
api_id: int = os.getenv("api_id")
api_hash: str = os.getenv("api_hash")
token = os.getenv("token")
client = TelegramClient("bot", api_id, api_hash)
download_path = "downloads/"
client.start(bot_token=token)


class Timer:
    def __init__(self, time_between=20):
        self.start_time = time.time()
        self.time_between = time_between

    def can_send(self):
        if time.time() > (self.start_time + self.time_between):
            self.start_time = time.time()
            return True
        return False


current_download = {}


@client.on(events.NewMessage())
async def download(event):

    print(event.text, sep="\n \n")
    print(event.stringify(), sep="\n ok \n")
    document = event.document
    name = None
    if event.document:
        for item in document.attributes:
            name = getattr(item, "file_name", None)
    if name:

        # check downloaded files in directory
        downloaded_files = [
            f for f in listdir(download_path) if isfile(join(download_path, f))
        ]
        if name not in list(current_download) and name not in list(downloaded_files):
            #  if file is new down load it 
            await download_manager(event, name)
        elif name in downloaded_files : await event.reply("downloaded")
        else: await event.reply("already downloading")


@client.on(events.NewMessage(pattern="/space"))
async def get_space(event):
    # show disk space info
    # a fucntion to check availabel space is good too
    total, used, free = shutil.disk_usage("/")
    await event.reply(
        f"free space: {free // (1000**2)} MB | used space: {used  // (1000**2)} MB | total space: {total // (1000**2)} MB "
    )


@client.on(events.NewMessage(pattern="/status"))
async def get_status(event):
    # show info about current downloads or downloaded files
    if current_download:
        for file, percent in list(current_download.items()):
            if percent == "100%":
                current_download.pop(file)
        await event.respond(
            "".join(["{0} = {1} \n".format(k, v) for k, v in current_download.items()])
        )
    else:
        await event.respond(
            """
        دانلود ها تمام شده است
لیست فایل های موجود👇🏻
        """
        )
        onlyfiles = [
            f for f in listdir(download_path) if isfile(join(download_path, f))
        ]
        # mak this output better using stickers or emojies
        await event.respond("\n".join(onlyfiles))


async def download_manager(event, name):
    async def progress_bar(current, total):
        current_download[name] = "{:.0f}%".format(current * 100 / total)

    msg = await event.reply("#downloading")
    with open(download_path + event.file.name, "wb") as out:
        await download_file(
            event.client, event.document, out, progress_callback=progress_bar
        )
    await msg.edit("#done")


client.run_until_disconnected()
