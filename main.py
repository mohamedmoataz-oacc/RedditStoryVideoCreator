#!/usr/bin/env python
import math
import os
import shutil
import time
import schedule
import sys
from os import name
from pathlib import Path
from subprocess import Popen
from typing import NoReturn

from prawcore import ResponseException
from utils.console import print_substep
from reddit.subreddit import get_subreddit_threads
from utils import settings
from utils.cleanup import cleanup
from utils.console import print_markdown, print_step
from utils.id import id
from utils.version import checkversion
from video_creation.background import (
    download_background_video,
    download_background_audio,
    chop_background,
    get_background_config,
)
from video_creation.final_video import make_final_video
from video_creation.screenshot_downloader import get_screenshots_of_reddit_posts
from video_creation.voices import save_text_to_mp3
from utils.ffmpeg_install import ffmpeg_install

__VERSION__ = "3.2.1"

print(
    """
██████╗ ███████╗██████╗ ██████╗ ██╗████████╗    ██╗   ██╗██╗██████╗ ███████╗ ██████╗     ███╗   ███╗ █████╗ ██╗  ██╗███████╗██████╗
██╔══██╗██╔════╝██╔══██╗██╔══██╗██║╚══██╔══╝    ██║   ██║██║██╔══██╗██╔════╝██╔═══██╗    ████╗ ████║██╔══██╗██║ ██╔╝██╔════╝██╔══██╗
██████╔╝█████╗  ██║  ██║██║  ██║██║   ██║       ██║   ██║██║██║  ██║█████╗  ██║   ██║    ██╔████╔██║███████║█████╔╝ █████╗  ██████╔╝
██╔══██╗██╔══╝  ██║  ██║██║  ██║██║   ██║       ╚██╗ ██╔╝██║██║  ██║██╔══╝  ██║   ██║    ██║╚██╔╝██║██╔══██║██╔═██╗ ██╔══╝  ██╔══██╗
██║  ██║███████╗██████╔╝██████╔╝██║   ██║        ╚████╔╝ ██║██████╔╝███████╗╚██████╔╝    ██║ ╚═╝ ██║██║  ██║██║  ██╗███████╗██║  ██║
╚═╝  ╚═╝╚══════╝╚═════╝ ╚═════╝ ╚═╝   ╚═╝         ╚═══╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝     ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
"""
)
# Modified by JasonLovesDoggo
print_markdown(
    "### Thanks for using this tool! Feel free to contribute to this project on GitHub! If you have any questions, feel free to join my Discord server or submit a GitHub issue. You can find solutions to many common problems in the documentation: https://reddit-video-maker-bot.netlify.app/"
)
checkversion(__VERSION__)

class Logger(object):
    def __init__(self):
        self.file = 'log.txt'
        self.backup = sys.stdout
    
    def write(self, obj):
        with open(self.file, 'a', encoding="utf-8") as f:
            f.write(obj)
        self.backup.write(obj)
    
    def flush(self):
        self.backup.flush()

sys.stdout = Logger()


def main(POST_ID=None) -> None:
    global redditid, reddit_object
    reddit_object = get_subreddit_threads(POST_ID)
    redditid = id(reddit_object)
    if not (settings.config["settings"]["debug"]["reuse_images"] and
            settings.config["settings"]["debug"]["reuse_separate_mp3s"]):
        reddit_object['thread_post'] = proofread_post(reddit_object['thread_post'])
    post_text = ' '.join(reddit_object['thread_post'])

    if not os.path.exists(f"./assets/temp/{reddit_object['thread_id']}/"):
        for key in settings.config["settings"]["debug"].keys():
            if key != "debug" and key != "no_youtube":
                settings.config["settings"]["debug"][key] = False

    length, number_of_comments = save_text_to_mp3(reddit_object)
    length = math.ceil(length)
    reel = length <= 60

    print(reddit_object['thread_post'])
    get_screenshots_of_reddit_posts(reddit_object, number_of_comments, reel)
    if not settings.config["settings"]["debug"]["reuse_background"]:
        bg_config = {
            "video": get_background_config("video"),
            "audio": get_background_config("audio"),
        }
        download_background_video(bg_config["video"])
        download_background_audio(bg_config["audio"])
        chop_background(bg_config, length, reddit_object)
    else:
        bg_config = {
            "video": ["debug mode", "debug mode", "debug mode"],
            "audio": ["debug mode", "debug mode", "debug mode"],
        }
    video_path = make_final_video(number_of_comments, length, reddit_object, bg_config, reel)
    if not video_path: return False

    video_data, thumbnail_text = get_video_data(post_text, bg_config)
    print("Video title:", video_data['title'])
    print("Video description:", video_data['description'])
    print("Video tags:", video_data['tags'])
    
    print_substep(f"Generating thumbnail...")
    thumbnail = generate_image(thumbnail_text, f"./assets/temp/{reddit_object['thread_id']}/thumbnail_image.png")
    thumbnail = add_text(
        thumbnail_path=thumbnail,
        text=video_data["thumbnail_text"],
        save_path=f"./assets/temp/{reddit_object['thread_id']}/thumbnail.png"
    )
    print_substep(f"Thumbnail generated successfully at: {thumbnail}", style="bold green")
    if not settings.config["settings"]["debug"]["no_youtube"]:
        upload_video_to_youtube(video_path, video_data, thumbnail)

    if not settings.config["settings"]["debug"]["debug"]:
        shutil.rmtree(f"./assets/temp/{reddit_object['thread_id']}/")
    return True


def run_many(times) -> None:
    for x in range(1, times + 1):
        print_step(
            f'on the {x}{("th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th")[x % 10]} iteration of {times}'
        )  # correct 1st 2nd 3rd 4th 5th....
        main()
        Popen("cls" if name == "nt" else "clear", shell=True).wait()


def shutdown() -> NoReturn:
    if "redditid" in globals():
        print_markdown("## Clearing temp files")
        cleanup(redditid)

    print("Exiting...")
    sys.exit()

def run():
    if config["reddit"]["thread"]["post_id"]:
        for index, post_id in enumerate(config["reddit"]["thread"]["post_id"].split("+")):
            index += 1
            print_step(
                f'on the {index}{("st" if index % 10 == 1 else ("nd" if index % 10 == 2 else ("rd" if index % 10 == 3 else "th")))} post of {len(config["reddit"]["thread"]["post_id"].split("+"))}'
            )
            main(post_id)
            Popen("cls" if name == "nt" else "clear", shell=True).wait()
    # elif config["settings"]["times_to_run"]:
    #     run_many(config["settings"]["times_to_run"])
    else:
        # main()
        status = False
        while not status:
            try: status = main()
            except Exception as e:
                print(e)
            print("Status:", status)
    
    print_substep("The video was created successfully! 🎉", style="bold green")
    print_substep(
        f'Next run will be in {settings.config["settings"]["run_every"]} hours.',
        style="bold green"
    )


if __name__ == "__main__":
    if sys.version_info.major != 3 or sys.version_info.minor != 10:
        print(
            "Hey! Congratulations, you've made it so far (which is pretty rare with no Python 3.10). Unfortunately, this program only works on Python 3.10. Please install Python 3.10 and try again."
        )
        sys.exit()
    ffmpeg_install()
    directory = Path().absolute()
    config = settings.check_toml(
        f"{directory}/utils/.config.template.toml", f"{directory}/config.toml"
    )
    config is False and sys.exit()

    from video_data_generation.gemini import get_video_data
    from video_data_generation.image_generation import generate_image, add_text
    from utils.proofreading import proofread_post

    if not settings.config["settings"]["debug"]["no_youtube"]:
        from utils.youtube_uploader import upload_video_to_youtube

    if (
        not settings.config["settings"]["tts"]["tiktok_sessionid"]
        or settings.config["settings"]["tts"]["tiktok_sessionid"] == ""
    ) and config["settings"]["tts"]["voice_choice"] == "tiktok":
        print_substep(
            "TikTok voice requires a sessionid! Check our documentation on how to obtain one.",
            "bold red",
        )
        sys.exit()
    try:
        run()
        schedule.every(settings.config["settings"]["run_every"]).hours.do(run)
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()
    except ResponseException:
        print_markdown("## Invalid credentials")
        print_markdown("Please check your credentials in the config.toml file")
        shutdown()
    except Exception as err:
        config["settings"]["tts"]["tiktok_sessionid"] = "REDACTED"
        config["settings"]["tts"]["elevenlabs_api_key"] = "REDACTED"
        print_step(
            f"Sorry, something went wrong with this version! Try again, and feel free to report this issue at GitHub or the Discord community.\n"
            f"Version: {__VERSION__} \n"
            f"Error: {err} \n"
            f'Config: {config["settings"]}'
        )
        raise err

    f.close()