#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Made by @Jigarvarma2005

# Edit anything at your own risk

from PIL import Image, ImageDraw, ImageFont
import os
from telegraph import upload_file
from pyrogram import Client, filters
from pyrogram.types import Message
import logging
import asyncio
import time
from typing import Tuple, List, Optional, Iterator, Union, Any
import shlex
from os.path import basename, join, exists
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
import math
import random
from urllib.parse import unquote_plus
from pySmartDL import SmartDL
from config import *

# enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'),
              logging.StreamHandler()],
    level=logging.INFO)
    
logging.getLogger("pyrogram").setLevel(logging.WARNING)
_LOG = logging.getLogger(__name__)
jvbot = Client(
    "jvssbot",
    bot_token = BOT_TOKEN,
    api_id = API_ID,
    api_hash = API_HASH
)

DB = {}
DOWNLOAD_DIRECTORY = os.environ.get("DOWNLOAD_DIRECTORY","./downloads")
water_mark = os.environ.get("WATERMARK_TEXT","Jigar")

@jvbot.on_message(~filters.sticker & (filters.regex(pattern=".*http.*") | filters.media))
async def telegraph(bot, message) -> None:
    msg_ = await message.reply_text("Please wait ....")
    list_of_links = await main_func(bot, message,msg_)
    if list_of_links is None:
        return await message.reply_text("Failed to download")
    else:
        for image in list_of_links:
            await message.reply_photo(image)
            os.remove(image)
    await msg_.delete()

@jvbot.on_message(filters.command(["log","logs"]))
async def get_log_wm(bot, message) -> None:
    try:
        await message.reply_document("log.txt")
    except Exception as e:
        _LOG.info(e)

@jvbot.on_message(filters.command(["setw","set_watermark"]))
async def set_wm(bot, message) -> None:
    msg_text = "send cmd with watermark text"
    try:
        text_ = message.text.split(" ",1)[1]
        DB[str(message.from_user.id)] = text_
        msg_text = f"Watermark is: `{text_}`"
    except:
        pass
    await message.reply_text(msg_text)

@jvbot.on_message(filters.command(["delw","del_watermark"]))
async def set_wm(bot, message) -> None:
    try:
        del DB[str(message.from_user.id)]
    except:
        pass
    await message.reply_text("Now using default watermark"))

@jvbot.on_message(filters.command(["getw","get_watermark"]))
async def get_wm(bot, message) -> None:
    msg_text = "No watermark found, use /setw to set watermark."
    if DB.get(str(message.from_user.id), water_mark) is not None:
        msg_text = f"Watermark is: `{DB.get(str(message.from_user.id), water_mark)}`"
    await message.reply_text(msg_text)

@jvbot.on_message(filters.command(["help"]))
async def get_help(bot, message) -> None:
    await message.reply_text("/setw [text]: set watermark.\n/getw : get current watermark")

@jvbot.on_message(filters.command(["start"]))
async def get_help(bot, message) -> None:
    await message.reply_text("watermark bot with telegraph.\n\ntype /help")

async def main_func(b,m,msg_):
    start_t = time.time()
    if m.media:
        down_loc = await download_func_tg(b, m, msg_)
    else:
        down_loc = await download_func_url(b, m, msg_)
    if down_loc is None:
        return None
    get_ = await generate_screen_shots(down_loc, m)
    try:
        os.remove(down_loc)
    except:
        pass
    return get_

async def download_func_tg(c, m, sts):
    start_time = time.time()
    dl_loc = os.path.join(DOWNLOAD_DIRECTORY, str(m.from_user.id), str(time.time()), "/")
    dl_loc = await c.download_media(message=m,
                                 file_name=dl_loc,
                                 progress=progress_for_pyrogram,
                                 progress_args=("Downloading",
                                                sts,
                                                start_time))
    return dl_loc

async def download_func_url(c: Client, m: Message, sts):
    url = m.text
    custom_file_name = unquote_plus(os.path.basename(url))
    if "|" in url:
        url, c_file_name = url.split("|", maxsplit=1)
        url = url.strip()
        if c_file_name:
            custom_file_name = c_file_name.strip()
    temp_dl_loc = os.path.join(DOWNLOAD_DIRECTORY, str(m.from_user.id), str(time.time()))
    if not os.path.isdir(DOWNLOAD_DIRECTORY):
        os.makedirs(DOWNLOAD_DIRECTORY)
    dl_loc = os.path.join(temp_dl_loc, custom_file_name)
    downloader = SmartDL(url, dl_loc, progress_bar=False, verify=False)
    downloader.start(blocking=False)
    count = 0
    if url:
        while not downloader.isFinished():
            total_length = downloader.filesize if downloader.filesize else 0
            downloaded = downloader.get_dl_size()
            percentage = downloader.get_progress() * 100
            speed = downloader.get_speed(human=True)
            estimated_total_time = downloader.get_eta(human=True)
            pr = ""
            try:
                percentage=int(percentage)
            except:
                percentage = 0
            for i in range(1,11):
                if i <= int(percentage/10):
                    pr += "▪️"
                else:
                    pr += "▫️"
            progress_str = \
                "**Downloading: {}%**\n" + \
                "[{}]\n" + \
                "{} of {}\n" + \
                "Speed: {}\n" + \
                "ETA: {}"
            progress_str = progress_str.format(
                round(percentage, 2),
                pr,
                humanbytes(downloaded),
                humanbytes(total_length),
                speed,
                estimated_total_time)
            count += 1
            if count >= 4:
                count = 0
                try:
                    await sts.edit(progress_str, disable_web_page_preview=True)
                except:
                    pass
                await asyncio.sleep(4)
        if not downloader.isSuccessful():
            _LOG.info("Unable to download your file...")
            return None
    if not os.path.exists(dl_loc):
        _LOG.info("Unkown error occured with file")
        return None
    return dl_loc

async def generate_screen_shots(
    video_file,
    msg
):
    meta = extractMetadata(createParser(video_file))
    if meta and meta.has("duration"):
        vid_len = meta.get("duration").seconds
    else:
        await msg.reply_text("Something went wrong, Not able to gather metadata")
        return None
    try:
        images = []
        ss_c = 6
        for frames in random.sample(range(vid_len), int(ss_c)):
            capture = await take_screen_shot(video_file, int(frames), os.path.join(DOWNLOAD_DIRECTORY, f"{str(time.time())}.jpg"))
            if capture is not None:
                if DB.get(str(msg.from_user.id), water_mark) is not None:
                    temp_file = os.path.join(DOWNLOAD_DIRECTORY, f"{str(time.time())}.jpg")
                    capture = await place_watermark(capture, temp_file, DB.get(str(msg.from_user.id), water_mark))
                if capture is not None:
                    #response = upload_file(capture)
                    images.append(capture)
                    #os.remove(capture)
    except Exception as e:
        _LOG.info(e)
        await msg.reply_text(e)
        return None
    if len(images) != 0:
        return images
    else:
        return None

async def runcmd(cmd: str) -> Tuple[str, str, int, int]:
    """ run command in terminal """
    args = shlex.split(cmd)
    process = await asyncio.create_subprocess_exec(*args,
                                                   stdout=asyncio.subprocess.PIPE,
                                                   stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    return (stdout.decode('utf-8', 'replace').strip(),
            stderr.decode('utf-8', 'replace').strip(),
            process.returncode,
            process.pid)


async def take_screen_shot(video_file: str, duration: int, path: str = '') -> Optional[str]:
    """ take a screenshot """
    _LOG.info('Extracting a frame from %s ||| Video duration => %s', video_file, duration)

    ttl = duration // 2
    thumb_image_path = path or join(DOWNLOAD_DIRECTORY, f"{basename(video_file)}.jpg")
    command = f'''ffmpeg -ss {ttl} -i "{video_file}" -vframes 1 "{thumb_image_path}"'''

    err = (await runcmd(command))[1]
    if err:
        _LOG.info(err)
    return thumb_image_path if exists(thumb_image_path) else None

async def place_watermark(ss_img, output, wt_text):
    #Create an Image Object from an Image
    im = Image.open(ss_img)
    width, height = im.size
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype('Arial.ttf', 26)
    textwidth, textheight = draw.textsize(wt_text, font)
    # calculate the x,y coordinates of the text
    margin = 10
    x = width - (width - textwidth - margin)
    y = (height - textheight - margin)
    # draw watermark in the bottom right corner
    draw.text((x, y), wt_text, font=font)
    im.save(output)
    os.remove(ss_img)
    return output


async def progress_for_pyrogram(
    current,
    total,
    ud_type,
    message,
    start
):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        # if round(current / total * 100, 0) % 5 == 0:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion
        comp = "▪️"
        ncomp = "▫️"
        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)
        pr = ""
        try:
            percentage=int(percentage)
        except:
            percentage = 0
        for i in range(1,11):
            if i <= int(percentage/10):
                pr += comp
            else:
                pr += ncomp
        progress = "{}: {}%\n[{}]\n".format(
            ud_type,
            round(percentage, 2),
            pr)

        tmp = progress + "{0} of {1}\nSpeed: {2}/sec\nETA: {3}\n\nThanks for using @JV_MegaUploadBot".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            # elapsed_time if elapsed_time != '' else "0 s",
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text="{}".format(
                    tmp
                )
            )
        except:
            pass


def humanbytes(size):
    # https://stackoverflow.com/a/49361727/4723940
    # 2**10 = 1024
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T', 5: 'P', 6: 'E', 7: 'Z', 8: 'Y'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]


if __name__ == "__main__" :
    # create download directory, if not exist
    if not os.path.isdir(DOWNLOAD_DIRECTORY):
        os.makedirs(DOWNLOAD_DIRECTORY)
    jvbot.run()
