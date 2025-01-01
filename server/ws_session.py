import asyncio
import json

from asyncio import AbstractEventLoop
from typing import Any, Optional, TYPE_CHECKING
from websockets.asyncio.server import ServerConnection

from .extractor import extract_media_url_from_video_url
from .msgs import *

# https://www.reddit.com/r/Python/comments/18gsr42/are_there_any_peps_about_type_imports/
if TYPE_CHECKING:
    # pylint: disable = ungrouped-imports
    from .app import App
    from .player_session import PlayerSession


class WsSession:
    app: App
    conn: ServerConnection
    event_loop: AbstractEventLoop
    player_session: Optional[PlayerSession]

    def __init__(self, app: App, conn: ServerConnection, event_loop: AbstractEventLoop):
        self.app = app
        self.conn = conn
        self.event_loop = event_loop
        self.player_session = None

    async def send(self, msg: Message):
        assert self.conn
        await self.conn.send(json.dumps(msg))

    def send_soon(self, msg: Message):
        asyncio.run_coroutine_threadsafe(self.send(msg), self.event_loop)

    async def handle_message(self, msg: Message):
        match msg["type"]:
            case "newSession":
                # Workaround https://github.com/microsoft/pyright/issues/9647
                sdp: Any = msg["sdp"]
                await self.handle_new_session_msg(msg["videoUrl"], sdp)
            case "resumeSession":
                pass  # TODO
            case "endSession":
                await self.handle_end_session_msg()
            case "iceCandidate":
                self.handle_ice_candidate_msg(msg["candidate"])
            case "newSdp":
                self.handle_new_sdp_msg(msg["sdp"])

    async def handle_new_session_msg(
        self,
        video_url: str,
        sdp: SessionDescription,
    ):
        if self.player_session:
            # TODO: logging level
            print(f"{self} start a new session without ending old one.")
            await self.handle_end_session_msg()
            assert not self.player_session

        media_url = await extract_media_url_from_video_url(video_url)
        if not media_url:
            await self.send(
                {"type": "sessionEnded", "reason": "Unable to extract media URL"}
            )
            return

        if sdp["type"] != "offer" or "sdp" not in sdp:
            await self.send({"type": "sessionEnded", "reason": "Malformed offer"})
            return

        self.player_session = self.app.create_new_player_session(
            media_url, self, sdp["sdp"]
        )
        await self.send(
            {"type": "sessionConnected", "sessionId": self.player_session.id}
        )

    async def handle_end_session_msg(self):
        if self.player_session:
            self.player_session.end_session("Requested by client")
        else:
            await self.send(
                {"type": "sessionEnded", "reason": "No session bounded to connection"}
            )

    def handle_ice_candidate_msg(self, candidate: IceCandidate):
        if self.player_session:
            self.player_session.handle_ice_candidate(
                candidate.get("candidate", None),
                candidate.get("sdpMLineIndex", None),
                candidate.get("sdpMid", None),
            )
        else:
            pass  # TODO

    def handle_new_sdp_msg(self, sdp: SessionDescription):
        if self.player_session:
            self.player_session.handle_new_sdp(
                sdp["type"],
                sdp.get("sdp", None),
            )
        else:
            pass  # TODO

    def handle_connection_closed(self, ok: bool):
        if not self.player_session:
            # Nothing to do.
            return

        self.player_session.handle_ws_disconnected()
        if ok:
            self.player_session.end_session("Disconnected")
        else:
            # TODO: support session resumption
            self.player_session.end_session("Disconnected")

    def handle_player_send_sdp(self, sdp: SessionDescription):
        self.send_soon({"type": "newSdp", "sdp": sdp})

    def handle_player_send_ice_candidate(self, candidate: IceCandidate):
        self.send_soon({"type": "iceCandidate", "candidate": candidate})

    def handle_player_session_ended(self, reason: str):
        msg: SessionEndedMessage = {
            "type": "sessionEnded",
            "reason": reason,
        }
        if self.player_session:
            msg["sessionId"] = self.player_session.id

        self.send_soon(msg)
        self.player_session = None
