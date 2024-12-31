import asyncio
import os
import signal

from websockets.asyncio.server import serve, ServerConnection

from .app import App

async def main():
    loop = asyncio.get_running_loop()
    app = App(loop)

    # Set the stop condition when receiving SIGTERM.
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    port = int(os.environ.get("PORT", "8001"))
    async with app.serve("", port):
        await stop

if __name__ == "__main__":
    asyncio.run(main())
