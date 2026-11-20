"""Serve the development build and rebuild on source changes."""

import argparse
import asyncio
import os
import re
import signal
import sys
from pathlib import Path

from tornado import httpserver, netutil, web, websocket


async def main(args):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--base-path", default="/")
    options, _ = parser.parse_known_args(args)
    prefix = options.base_path.strip("/")
    mount = f"/{prefix}/" if prefix else "/"
    stamp = Path(".build/live-reload")

    def build_version():
        try:
            return str(stamp.stat().st_mtime_ns)
        except FileNotFoundError:
            return "0"

    version = build_version()
    clients = set()

    class ReloadSocket(websocket.WebSocketHandler):
        async def open(self):
            clients.add(self)
            await self.write_message(version)

        def on_close(self):
            clients.discard(self)

    class PreviewFiles(web.StaticFileHandler):
        def set_extra_headers(self, path):
            self.set_header("Cache-Control", "no-store")

    routes = [(re.escape(mount + "__live_reload"), ReloadSocket)]
    if prefix:
        routes.append((rf"(?:/|{re.escape(mount.rstrip('/'))})", web.RedirectHandler,
                       {"url": mount, "permanent": False}))
    routes.append((re.escape(mount) + "(.*)", PreviewFiles,
                   {"path": "dist", "default_filename": "index.html"}))

    port = int(os.environ.get("PORT", "8000"))
    sockets = netutil.bind_sockets(port, address="127.0.0.1")
    server = httpserver.HTTPServer(web.Application(routes))
    server.add_sockets(sockets)
    print(f"Preview: http://127.0.0.1:{sockets[0].getsockname()[1]}{mount}", flush=True)

    watcher = await asyncio.create_subprocess_exec(
        "watchexec", "--on-busy-update", "queue", "--shell=none",
        "--watch", "assets", "--watch", "content", "--watch", "styles",
        "--watch", "templates", "--watch", "tools", "--watch", "build.sh",
        "--watch", "configure.py", "--ignore", "__pycache__",
        "--", "./build.sh", "--live-reload", *args, start_new_session=True,
    )
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, asyncio.current_task().cancel)
    try:
        while watcher.returncode is None:
            await asyncio.sleep(0.2)
            next_version = build_version()
            if next_version != version:
                version = next_version
                for client in tuple(clients):
                    try:
                        await client.write_message(version)
                    except websocket.WebSocketClosedError:
                        pass
        return watcher.returncode
    except asyncio.CancelledError:
        return 0
    finally:
        server.stop()
        for client in tuple(clients):
            client.close()
        if watcher.returncode is None:
            watcher.terminate()
            await watcher.wait()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
