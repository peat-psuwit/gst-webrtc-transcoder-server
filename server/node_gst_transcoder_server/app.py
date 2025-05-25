import json
import random
import string

from asyncio import AbstractEventLoop
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from websockets.asyncio.server import serve, ServerConnection

from .msgs import Message
from .player_session import PlayerSession
from .types import RawMedia
from .ws_session import WsSession


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
        self, media_urls: list[RawMedia], ws_session: WsSession
    ):
        session_id = id_generator()
        player_session = self.player_sessions[session_id] = PlayerSession(
            session_id,
            media_urls,
            ws_session,
            self,  # App
            self.event_loop,
        )
        return player_session

    def player_session_ended(self, player_session: PlayerSession):
        try:
            del self.player_sessions[player_session.id]
        except KeyError:
            # TODO: logging level
            print(f"Warning: session {player_session.id} ended twice?")

    async def on_connect(self, ws_conn: ServerConnection):
        ws_session = WsSession(self, ws_conn, self.event_loop)
        while True:
            try:
                msgTxt = await ws_conn.recv()
            except ConnectionClosedOK:
                ws_session.handle_connection_closed(ok=True)
                return
            except ConnectionClosedError:
                ws_session.handle_connection_closed(ok=False)
                return

            # XXX: no validation whatsoever.
            msg: Message = json.loads(msgTxt)
            await ws_session.handle_message(msg)

    # XXX: do people write stuffs in this way?
    def serve(self, host: str | None = None, port: int | None = None):
        return serve(self.on_connect, host, port)
