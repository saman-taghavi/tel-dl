#!/usr/bin/env python3
import os
import sys
import pytz
from datetime import datetime
import time
import asyncio

# Import the client
from telethon import TelegramClient, events
from telethon.tl import types

# Enable logging
import logging

# use dotenv
from dotenv import load_dotenv

load_dotenv()
# This is a helper method to access environment variables or
# prompt the user to type them in the terminal if missing.
def get_env(name, message, cast=str):
    if name in os.environ:
        return os.environ[name]
    while True:
        value = input(message)
        try:
            return cast(value)
        except ValueError as e:
            print(e, file=sys.stderr)
            time.sleep(1)


# Define some variables so the code reads easier
session = os.environ.get("TG_SESSION", "tg_downloader")
api_id = get_env("TG_API_ID", "Enter your API ID: ", int)
api_hash = get_env("TG_API_HASH", "Enter your API hash: ")
bot_token = get_env("TG_BOT_TOKEN", "Enter your Telegram BOT token: ")
download_path = get_env("TG_DOWNLOAD_PATH", "Enter full path to downloads directory: ")
debug_enabled = "DEBUG_ENABLED" in os.environ
if debug_enabled:
    logging.basicConfig(
        format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
        level=logging.DEBUG,
    )
else:
    logging.basicConfig(
        format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
        level=logging.ERROR,
    )

number_of_parallel_downloads = int(os.environ.get("TG_MAX_PARALLEL", 4))
maximum_seconds_per_download = int(os.environ.get("TG_DL_TIMEOUT", 3600))
proxy = None  # https://github.com/Anorov/PySocks

# date format
fmt = "%Y-%m-%d %H:%M:%S"
tz = pytz.timezone("Asia/Tehran")

# Create a queue that we will use to store our downloads.
queue = asyncio.Queue()

# Create tmp path to store downloads until completed
tmp_path = os.path.join(download_path, "tmp")
os.makedirs(tmp_path, exist_ok=True)


async def worker(name):
    while True:
        # Get a "work item" out of the queue.
        queue_item = await queue.get()
        update = queue_item[0]
        reply = queue_item[1]
        file_name = queue_item[2]
        file_path = tmp_path
        file_path = os.path.join(file_path, file_name)

        await reply.edit("Downloading...")
        # convert time to ir local using pytz
        print(
            "[%s] Download started at %s" % (file_name, datetime.now(tz).strftime(fmt))
        )
        try:
            loop = asyncio.get_event_loop()
            # and use the call back for progress of download
            task = loop.create_task(client.download_media(update.message, file_path))
            # here we wait for the download to finish as function is async so no problem here
            download_result = await asyncio.wait_for(
                task, timeout=maximum_seconds_per_download
            )
            #  format time to ir local here
            end_time = datetime.now(tz).strftime(fmt)
            _, filename = os.path.split(download_result)
            final_path = os.path.join(download_path, filename)
            # this moves the file
            os.rename(download_result, final_path)
            print(
                "[%s] Successfully downloaded to %s at %s"
                % (file_name, final_path, end_time)
            )
            await reply.edit("Finished at %s" % (end_time))
        except asyncio.TimeoutError:
            print(
                "[%s] Timeout reached at %s"
                % (file_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            )
            await reply.edit("Error!")
            message = await update.reply("ERROR: Timeout reached downloading this file")
        except Exception as e:
            print("[EXCEPTION]: %s" % (str(e)))
            # print("[%s]: %s" % (e.__class__.__name__, str(e)))
            print(
                "[%s] Exception at %s"
                % (file_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            )
            await reply.edit("Error!")
            message = await update.reply(
                "ERROR: Exception %s raised downloading this file: %s"
                % (e.__class__.__name__, str(e))
            )

        # Notify the queue that the "work item" has been processed.
        queue.task_done()


client = TelegramClient(
    session,
    api_id,
    api_hash,
    proxy=proxy,
    request_retries=10,
    flood_sleep_threshold=120,
)

# This is our update handler. It is called when a new update arrives.
# Register `events.NewMessage` before defining the client.
@events.register(events.NewMessage)
async def handler(update):
    if debug_enabled:
        print(update)
    if update.message.media:
        file_name = "unknown name"
        attributes = update.message.media.document.attributes
        for attr in attributes:
            if isinstance(attr, types.DocumentAttributeFilename):
                file_name = attr.file_name
                # maybe also check here if we have the file in queue or on disk or file is downloading
        print(
            "[%s] Download queued at %s"
            % (file_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        )
        reply = await update.reply("In queue")
        await queue.put([update, reply, file_name])


try:
    # Create worker tasks to process the queue concurrently.
    tasks = []
    for i in range(number_of_parallel_downloads):
        loop = asyncio.get_event_loop()
        task = loop.create_task(worker(f"worker-{i}"))
        tasks.append(task)

    # Start client with TG_BOT_TOKEN string
    client.start(bot_token=str(bot_token))
    # Register the update handler so that it gets called
    client.add_event_handler(handler)

    # Run the client until Ctrl+C is pressed, or the client disconnects
    print("Successfully started (Press Ctrl+C to stop)")
    client.run_until_disconnected()
finally:
    # Cancel our worker tasks.
    for task in tasks:
        task.cancel()
    # Wait until all worker tasks are cancelled.
    # await asyncio.gather(*tasks, return_exceptions=True)
    # Stop Telethon client
    client.disconnect()
    print("Stopped!")
