import asyncio
import os
import signal

from gi.events import GLibEventLoopPolicy
from gi.repository import GLib

from .app import App


async def async_main(loop: asyncio.AbstractEventLoop):
    app = App(loop)

    port = int(os.environ.get("PORT", "8001"))
    server = await app.serve("", port)
    await server.serve_forever()


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
