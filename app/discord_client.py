import os
from time import sleep

import requests
from loguru import logger
from requests import exceptions

from app.twitch_client import StreamInformation


class DiscordClient:
    notification_msg_id: str = ""

    def __init__(self):
        self._webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
        self.avatar_url = os.environ["AVATAR_URL"]
        self.content = os.environ["CONTENT"]

    def send_information_to_discord(
        self,
        stream: StreamInformation,
        profile_image: str,
        retry_count: int = 0,
    ) -> None:
        logger.info("Sending a message with an embed to the webhook...")
        streamer_url = f"https://www.twitch.tv/{stream.user_login}"
        try:
            response = requests.post(
                url=f"{self._webhook_url}?wait=true",
                json={
                    "username": "Randy",
                    # "avatar_url": "https://i.imgur.com/DBOuwjx.png",
                    "avatar_url": f"{self.avatar_url}",
                    "content": f"{self.content}",
                    "embeds": [
                        {
                            "title": stream.title,
                            "color": 8388863,
                            "timestamp": stream.started_at,
                            "url": streamer_url,
                            "author": {
                                "name": stream.user_name,
                                "url": streamer_url,
                                "icon_url": profile_image,
                            },
                            "image": {"url": stream.thumbnail_url},
                            "fields": [
                                {
                                    "name": "Game",
                                    "value": stream.game_name,
                                    "inline": True,
                                },
                                {
                                    "name": "Viewers",
                                    "value": stream.viewer_count,
                                    "inline": True,
                                },
                            ],
                        }
                    ],
                },
            )

            response.raise_for_status()

            self.notification_msg_id = response.json()["id"]
            logger.info("Stream information sent with ping to Discord.")
        except (exceptions.ConnectionError, exceptions.HTTPError) as err:
            logger.opt(exception=err).warning(
                "Could not send embed to Discord."
            )
            if retry_count > 5:
                logger.warning("Aborted sending the embed to Discord.")
                return
            retry_count += 1
            logger.info(f"Retrying finalize in {retry_count * 5} seconds.")
            sleep(retry_count * 5)
            self.send_information_to_discord(
                stream=stream,
                profile_image=profile_image,
                retry_count=retry_count,
            )

    def update_information_on_discord(
        self, stream: StreamInformation, profile_image: str
    ) -> None:
        logger.info("Updating stream information on Discord...")
        streamer_url = f"https://www.twitch.tv/{stream.user_login}"
        try:
            response = requests.patch(
                url=f"{self._webhook_url}/messages/{self.notification_msg_id}",
                json={
                    "embeds": [
                        {
                            "title": stream.title,
                            "color": 8388863,
                            "timestamp": stream.started_at,
                            "url": streamer_url,
                            "author": {
                                "name": f"{stream.user_name}",
                                "url": streamer_url,
                                "icon_url": profile_image,
                            },
                            "image": {"url": stream.thumbnail_url},
                            "fields": [
                                {
                                    "name": "Game",
                                    "value": stream.game_name,
                                    "inline": True,
                                },
                                {
                                    "name": "Viewers",
                                    "value": stream.viewer_count,
                                    "inline": True,
                                },
                            ],
                        }
                    ],
                },
            )
            response.raise_for_status()
            logger.info("Message embed content updated.")
        except (exceptions.ConnectionError, exceptions.HTTPError) as err:
            logger.opt(exception=err).warning(
                "Could not update embed content due to connection error. "
                "Not retrying due to this not being important."
            )

    def finalize_information_on_discord(
        self, streamer_name, vod_url: str | None, retry_count: int = 0
    ) -> None:
        logger.info("Finalizing stream information on Discord...")
        if not self.notification_msg_id:
            logger.info("Message ID not set, nothing to finalize.")
            return

        if not vod_url:
            vod_url = "None available."

        try:
            response = requests.patch(
                url=f"{self._webhook_url}/messages/{self.notification_msg_id}",
                json={
                    "username": "Oak Tree",
                    "avatar_url": "https://i.imgur.com/DBOuwjx.png",
                    "content": (
                        f"{streamer_name} stopped the stream. Check out the VOD!"
                        f"\n{vod_url}"
                    ),
                    "embeds": [],
                },
            )
            response.raise_for_status()
            logger.info("Message updated with VOD.")
        except (exceptions.ConnectionError, exceptions.HTTPError) as err:
            logger.opt(exception=err).warning(
                "Could not finalize embed on Discord."
            )
            if retry_count > 5:
                logger.warning(
                    "Aborted finalizing the embed on Discord. "
                    "It will be stuck on the last stream update."
                )
                return
            retry_count += 1
            logger.info(f"Retrying finalize in {retry_count * 5} seconds.")
            sleep(retry_count * 5)
            self.finalize_information_on_discord(
                streamer_name=streamer_name,
                vod_url=vod_url,
                retry_count=retry_count,
            )
