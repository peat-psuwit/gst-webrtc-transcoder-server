import json
import random
import string

from asyncio import AbstractEventLoop
from typing import Any
from websockets.asyncio.server import serve, ServerConnection

from .msgs import *
from .player_session import PlayerSession
from .ws_session import WsSession
from server import player_session


# https://stackoverflow.com/a/2257449
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


class App:
    event_loop: AbstractEventLoop
    player_sessions: dict[str, PlayerSession]

    def __init__(self, event_loop: AbstractEventLoop):
        self.event_loop = event_loop
        self.player_sessions = {}

    def create_new_player_session(
        self, media_url: str, ws_session: WsSession, sdp: SessionDescription
    ):
        session_id = id_generator()
        player_session = self.player_sessions[session_id] = PlayerSession(
            session_id,
            media_url,
            ws_session,
            self,  # App
            self.event_loop,
            sdp,
        )
        return player_session

    def player_session_ended(self, player_session: PlayerSession):
        del self.player_sessions[player_session.id]

    async def on_connect(self, ws_conn: ServerConnection):
        ws_session = WsSession(ws_conn, self.event_loop)
        while True:
            msgTxt = await ws_conn.recv()
            # XXX: no validation whatsoever.
            msg: Message = json.loads(msgTxt)
            await ws_session.handle_message(msg)

    # XXX: do people write stuffs in this way?
    def serve(self, host: str | None = None, port: int | None = None):
        return serve(self.on_connect, host, port)
