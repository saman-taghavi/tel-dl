#!/usr/bin/env python3
import os, shutil
import sys
import pytz
from datetime import datetime
import time
import asyncio
from os import listdir
from os.path import isfile, join
import bot_replies

# Import the client
from telethon import TelegramClient, events, connection
from telethon import tl

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
server = os.environ.get("server", None)
port = int(os.environ.get("port", None))
secret = os.environ.get("secret", None)
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
proxy = (server, port, secret)  # https://github.com/Anorov/PySocks

# date format
fmt = "%Y-%m-%d %H:%M:%S"
tz = pytz.timezone("Asia/Tehran")

# Create a queue that we will use to store our downloads.
queue = asyncio.Queue()

# queue files
queue_files = {}
# download detail on downloading files
download_detail = True
# Create tmp path to store downloads until completed
tmp_path = os.path.join(download_path, "tmp")
os.makedirs(tmp_path, exist_ok=True)

# helper fuctions
async def task_messenger(message: str, update: tl.custom.message.Message):
    loop = asyncio.get_event_loop()
    # and use the call back for progress of download
    task = loop.create_task(update.reply(message))
    # here we wait for the download to finish as function is async so no problem here
    await asyncio.wait_for(task, timeout=30)


async def worker(name):
    while True:
        print(f"{name=}")
        print(queue)
        # Get a "work item" out of the queue.
        downloaded_files = [
            f for f in listdir(download_path) if isfile(join(download_path, f))
        ]
        tmp_downloaded_files = [
            f for f in listdir(tmp_path) if isfile(join(tmp_path, f))
        ]
        # print(f"{downloaded_files=}")
        # print(f"{tmp_downloaded_files=}")
        queue_item = await queue.get()
        update = queue_item[0]
        reply = queue_item[1]
        file_name = queue_item[2]
        file_path = tmp_path
        file_path = os.path.join(file_path, file_name)
        # check disk space
        total, used, free = shutil.disk_usage("/")
        free = free // (1000 ** 3)
        # print(f"frees space = {free}")
        # print(f"{queue_files=}")

        try:
            if free < 20:
                await task_messenger("less than 2 GB is left free some space", update)
                print("not free space")

            # # if file is downloaded or being downloaded tell the user
            # elif file_name in downloaded_files:
            #     await task_messenger("file is already downloaded", update)
            #     print("in Downloaded")

            # elif file_name in file_name in tmp_downloaded_files:
            #     await task_messenger("file is downloading", update)
            #     print("in Temp")
            else:
                print("Downloading")
                await reply.edit("Downloading...")
                # convert time to ir local using pytz
                print(
                    "[%s] Download started at %s"
                    % (file_name, datetime.now(tz).strftime(fmt))
                )

                # i can move this out with a simpler function which pases more data to this
                async def progress_bar(current, total):
                    percentage = "{:.0f}%".format(current * 100 / total)
                    if (queue_files[file_name] != percentage) and download_detail:
                        await reply.edit(f"{percentage}")
                    queue_files[file_name] = percentage

                loop = asyncio.get_event_loop()
                # and use the call back for progress of download
                task = loop.create_task(
                    client.download_media(
                        update.message, file_path, progress_callback=progress_bar
                    )
                )
                # here we wait for the download to finish as function is async so no problem here
                download_result = await asyncio.wait_for(task, timeout=3)
                queue_files.pop(file_name)
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
                queue.task_done()

        except asyncio.TimeoutError:
            print(
                "[%s] Timeout reached at %s"
                % (
                    file_name,
                    time.strftime("%Y-%m-%d %H:%M:%S", datetime.now(tz).strftime(fmt)),
                )
            )
            await reply.edit("Error!")
            message = await update.reply("ERROR: Timeout reached downloading this file")
        except Exception as e:
            print("[EXCEPTION]: %s" % (str(e)))
            # print("[%s]: %s" % (e.__class__.__name__, str(e)))
            print(
                "[%s] Exception at %s"
                % (
                    file_name,
                    time.strftime("%Y-%m-%d %H:%M:%S", datetime.now(tz).strftime(fmt)),
                )
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
    connection=connection.ConnectionTcpMTProxyRandomizedIntermediate,
)

# This is our update handler. It is called when a new update arrives.
# Register `events.NewMessage` before defining the client.
@events.register(events.NewMessage(func=lambda e: e.message.media))
async def downloader(update):
    print(tasks, "\n")
    # if debug_enabled:
    #     print(update)
    total, used, free = shutil.disk_usage("/")
    free = free // (1000 ** 3)
    file_name = "unknown name"
    attributes = update.message.media.document.attributes
    for attr in attributes:
        if isinstance(attr, tl.types.DocumentAttributeFilename):
            file_name = attr.file_name
            if file_name in list(queue_files):
                # if file is in queue don't go further than this
                await update.reply("file is in queue")
                return
            queue_files[file_name] = 0
            # maybe also check here if we have the file in queue or on disk or file is downloading
    print(
        "[%s] Download queued at %s"
        % (file_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())),
        "\n",
    )

    reply = await update.reply("In queue")
    await queue.put([update, reply, file_name])


@events.register(events.NewMessage(pattern="/status"))
async def get_status(update):
    if queue_files:
        await update.respond(
            "".join(["{0} = {1} \n".format(k, v) for k, v in queue_files.items()])
        )

    else:
        await update.respond(bot_replies.download["see files"])
        onlyfiles = [
            f for f in listdir(download_path) if isfile(join(download_path, f))
        ]
        # mak this output better using stickers or emojies
        await update.respond("\n".join(onlyfiles))


@events.register(events.NewMessage(pattern="/detail"))
async def get_details(update):
    global download_detail
    download_detail ^= True
    await update.respond(f"{download_detail}")


@events.register(events.NewMessage(pattern="/space"))
async def get_space(event):
    # show disk space info
    # a fucntion to check availabel space is good too
    total, used, free = shutil.disk_usage("/")
    await event.reply(
        f"free space: {free // (1000**3)} GB | used space: {used  // (1000**3)} GB | total space: {total // (1000**3)} GB "
    )


try:
    # Create worker tasks to process the queue concurrently.
    tasks = []
    for i in range(number_of_parallel_downloads):
        loop = asyncio.get_event_loop()
        task = loop.create_task(worker(f"worker-{i}"))
        tasks.append(task)
    print(tasks)
    # Start client with TG_BOT_TOKEN string
    client.start(bot_token=str(bot_token))
    # Register the update handler so that it gets called
    client.add_event_handler(downloader)
    client.add_event_handler(get_status)
    client.add_event_handler(get_details)
    client.add_event_handler(get_space)

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
