from asyncio import AbstractEventLoop
from websockets.asyncio.server import serve, ServerConnection

class App:
    event_loop: AbstractEventLoop

    def __init__(self, event_loop: AbstractEventLoop):
        self.event_loop = event_loop

    async def on_connect(self, ws_conn: ServerConnection):
        while True:
            message = await ws_conn.recv()
            print(message)

    # XXX: do people write stuffs in this way?
    def serve(self, host: str | None=None, port: int | None=None):
        return serve(self.on_connect, host, port)
