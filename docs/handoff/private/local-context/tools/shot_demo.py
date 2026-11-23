"""Headless Chrome screenshots of the demo app over CDP, for when the preview pane will not draw.

  python shot_demo.py <out.png> <path> [js-to-run-after-load] [width] [height]

Signs in by writing the demo session into sessionStorage, as the preview browser does.
"""

import asyncio
import base64
import json
import os
import subprocess
import sys
import time

import httpx
import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9352
BASE = "http://localhost:5175"
HERE = os.path.dirname(os.path.abspath(__file__))


async def main(out: str, path: str, js: str, width: int, height: int) -> None:
    session = json.load(open(os.path.join(HERE, os.environ.get("DEMO_SESSION", "demo_session.json")), encoding="utf-8"))
    profile = os.path.join(HERE, "chrome-profile-demo")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
         f"--window-size={width},{height}", "--hide-scrollbars", "--no-first-run", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        page = None
        for _ in range(60):
            try:
                targets = httpx.get(f"http://127.0.0.1:{PORT}/json").json()
                page = next(t for t in targets if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.25)
        assert page, "no chrome page"
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=80_000_000) as ws:
            counter = 0

            async def cdp(method: str, **params: object) -> dict:
                nonlocal counter
                counter += 1
                mine = counter
                await ws.send(json.dumps({"id": mine, "method": method, "params": params}))
                while True:
                    message = json.loads(await ws.recv())
                    if message.get("id") == mine:
                        if "error" in message:
                            raise RuntimeError(message["error"])
                        return message.get("result", {})

            async def evaluate(expression: str) -> object:
                result = await cdp("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
                return result.get("result", {}).get("value")

            await cdp("Page.enable")
            await cdp("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
            await cdp("Page.navigate", url=BASE + "/sign-in")
            await asyncio.sleep(3)
            await evaluate(
                "sessionStorage.setItem('verity.session.token', %s); sessionStorage.setItem('verity.session.principal', %s); 'ok'"
                % (json.dumps(session["token"]), json.dumps(json.dumps(session["principal"])))
            )
            await cdp("Page.navigate", url=BASE + path)
            await asyncio.sleep(5)
            if js:
                print("js:", await evaluate(js))
                await asyncio.sleep(1.5)
            shot = await cdp("Page.captureScreenshot", format="png")
            with open(out, "wb") as handle:
                handle.write(base64.b64decode(shot["data"]))
            print("saved", out)
    finally:
        proc.terminate()


if __name__ == "__main__":
    args = sys.argv
    asyncio.run(
        main(
            args[1],
            args[2],
            args[3] if len(args) > 3 else "",
            int(args[4]) if len(args) > 4 else 1440,
            int(args[5]) if len(args) > 5 else 900,
        )
    )
