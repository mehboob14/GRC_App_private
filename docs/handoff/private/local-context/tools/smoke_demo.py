"""Load each main page of the demo app in headless Chrome and report what broke.

  python smoke_demo.py route1 route2 ...

Per route: whether the page rendered text, an error boundary showed, and every uncaught
exception or console error. Signs in with the demo session like shot_demo.py.
"""

import asyncio
import json
import os
import subprocess
import sys
import time

import httpx
import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9353
BASE = "http://localhost:5175"
HERE = os.path.dirname(os.path.abspath(__file__))


async def main(routes: list[str]) -> None:
    session = json.load(open(os.path.join(HERE, "demo_session.json"), encoding="utf-8"))
    profile = os.path.join(HERE, "chrome-profile-smoke")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
         "--window-size=1440,900", "--no-first-run", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        page = None
        for _ in range(60):
            try:
                page = next(t for t in httpx.get(f"http://127.0.0.1:{PORT}/json").json() if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.25)
        assert page
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=80_000_000) as ws:
            counter = 0
            problems: list[str] = []

            async def pump_until(target_id: int | None, seconds: float) -> dict | None:
                end = time.time() + seconds
                while True:
                    remaining = end - time.time()
                    if target_id is None and remaining <= 0:
                        return None
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=max(remaining, 0.05) if target_id is None else 30)
                    except asyncio.TimeoutError:
                        return None
                    message = json.loads(raw)
                    method = message.get("method")
                    if method == "Runtime.exceptionThrown":
                        detail = message["params"]["exceptionDetails"]
                        problems.append("exception: " + (detail.get("exception", {}).get("description") or detail.get("text", ""))[:300])
                    elif method == "Runtime.consoleAPICalled" and message["params"]["type"] == "error":
                        args = message["params"]["args"]
                        problems.append("console.error: " + " ".join(str(a.get("value", a.get("description", ""))) for a in args)[:300])
                    elif target_id is not None and message.get("id") == target_id:
                        if "error" in message:
                            raise RuntimeError(message["error"])
                        return message.get("result", {})

            async def cdp(method: str, **params: object) -> dict:
                nonlocal counter
                counter += 1
                await ws.send(json.dumps({"id": counter, "method": method, "params": params}))
                return await pump_until(counter, 30) or {}

            async def evaluate(expression: str) -> object:
                result = await cdp("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
                return result.get("result", {}).get("value")

            await cdp("Page.enable")
            await cdp("Runtime.enable")
            await cdp("Emulation.setDeviceMetricsOverride", width=1440, height=900, deviceScaleFactor=1, mobile=False)
            await cdp("Page.navigate", url=BASE + "/sign-in")
            await pump_until(None, 3)
            await evaluate(
                "sessionStorage.setItem('verity.session.token', %s); sessionStorage.setItem('verity.session.principal', %s); 'ok'"
                % (json.dumps(session["token"]), json.dumps(json.dumps(session["principal"])))
            )
            for route in routes:
                problems.clear()
                await cdp("Page.navigate", url=BASE + route)
                await pump_until(None, 4.5)
                summary = await evaluate(
                    "JSON.stringify({path: location.pathname, chars: (document.querySelector('main')||document.body).innerText.length,"
                    " boundary: /something went wrong|unexpected error/i.test(document.body.innerText),"
                    " heading: (document.querySelector('h1')||{}).textContent||null})"
                )
                print(route, "->", summary, "| problems:", len(problems))
                for problem in problems[:4]:
                    print("    ", problem)
    finally:
        proc.terminate()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
