import asyncio
import os
import signal

from gi.events import GLibEventLoopPolicy
from gi.repository import GLib

from .app import App


async def async_main(loop: asyncio.AbstractEventLoop):
    app = App(loop)

    # Set the stop condition when receiving SIGTERM.
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    port = int(os.environ.get("PORT", "8001"))
    async with app.serve("", port):
        await stop


def main():
    policy = GLibEventLoopPolicy()
    asyncio.set_event_loop_policy(policy)

    loop = policy.get_event_loop()
    task = loop.create_task(async_main(loop))

    glib_mainloop = GLib.MainLoop()
    glib_mainloop.run()


if __name__ == "__main__":
    main()

__all__ = ["main"]
