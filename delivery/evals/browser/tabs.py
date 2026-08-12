#!/usr/bin/env python
"""Открыть вкладку History в настоящем браузере и снять её — пункт приёмки B6."""
import asyncio, base64, json, os, pathlib, subprocess, sys, time, urllib.request
import websockets

S = pathlib.Path(__file__).parent
OUT = pathlib.Path(os.environ.get("BROWSER_EVAL_OUT", S / "out"))
OUT.mkdir(parents=True, exist_ok=True)
TAB = sys.argv[1] if len(sys.argv) > 1 else "History"
CHROME = (pathlib.Path.home() / "Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64"
          / "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
PORT = 9444

p = subprocess.Popen(
    [str(CHROME), "--headless=new", f"--remote-debugging-port={PORT}",
     f"--user-data-dir={OUT}/tabs-profile", "--no-first-run", "--no-default-browser-check",
     "--disable-gpu", "--window-size=900,900", "http://localhost:5273/"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def main():
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as r:
                t = next((x for x in json.load(r)
                          if x["type"] == "page" and "5273" in x.get("url", "")), None)
            if t:
                break
        except Exception:
            pass
        time.sleep(0.5)
    n = 0

    async def call(ws, method, **params):
        nonlocal n
        n += 1
        await ws.send(json.dumps({"id": n, "method": method, "params": params}))
        while True:
            m = json.loads(await ws.recv())
            if m.get("id") == n:
                return m.get("result", {})

    async with websockets.connect(t["webSocketDebuggerUrl"], max_size=None) as ws:
        await call(ws, "Page.enable")
        await call(ws, "Runtime.enable")
        await asyncio.sleep(4)
        r = await call(
            ws,
            "Runtime.evaluate",
            returnByValue=True,
            expression=(
                "(() => { const name=" + json.dumps(TAB) + ";"
                " const b=[...document.querySelectorAll('button')]"
                "   .find(x=>x.textContent.trim()===name);"
                " if(!b) return false; b.click(); return true; })()"
            ),
        )
        print(f"клик «{TAB}»:", r.get("result", {}).get("value"))
        await asyncio.sleep(4)
        r = await call(ws, "Runtime.evaluate", returnByValue=True,
                       expression="document.body.innerText.slice(0,900)")
        print("--- что на экране ---")
        print(r.get("result", {}).get("value"))
        probe = await call(ws, "Runtime.evaluate", returnByValue=True, awaitPromise=True,
            expression="""(async () => {
              try {
                const r = await fetch('/sessions/interviews');
                const body = await r.text();
                return JSON.stringify({status: r.status, body: body.slice(0,200)});
              } catch (e) { return 'FETCH THREW: ' + e; }
            })()""")
        print("fetch из страницы:", probe.get("result", {}).get("value"))
        shot = await call(ws, "Page.captureScreenshot", format="png")
        (OUT / f"tab-{TAB.lower().replace(chr(32), chr(45))}.png").write_bytes(base64.b64decode(shot["data"]))
        print(f"снимок: {OUT.name}/tab-*.png")

try:
    asyncio.run(main())
finally:
    p.terminate()
