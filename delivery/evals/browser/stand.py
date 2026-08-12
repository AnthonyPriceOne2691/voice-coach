#!/usr/bin/env python
"""Ручная приёмка Phase 2 в настоящем браузере: закрыть вкладку НА СЕРЕДИНЕ ХОДА.

Что настоящее: Chromium 151, страница приложения, его VAD, MediaRecorder,
WebSocket по doc 15, whisper.cpp, qwen2.5:14b-instruct, Piper, SQLite.
Что имитировано: только источник звука — `getUserMedia` подменён потоком из
AudioContext (флаг Chromium `--use-file-for-fake-audio-capture` в этой сборке
отдаёт цифровую тишину, замер: peak_rms 0, -180 dBFS).

Ход считается начатым, когда UI перешёл в Thinking… после нашей реплики:
значит запись закрыта VAD'ом и ответ ушёл в STT+LLM. Вкладка закрывается
именно там — без end_session.
"""

import asyncio
import base64
import json
import pathlib
import os
import subprocess
import time
import urllib.request

import websockets

S = pathlib.Path(__file__).parent
OUT = pathlib.Path(os.environ.get("BROWSER_EVAL_OUT", S / "out"))
OUT.mkdir(parents=True, exist_ok=True)
CHROME = (
    pathlib.Path.home()
    / "Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64"
    / "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)
PORT = 9222
APP = "http://localhost:5273/"
API = "http://127.0.0.1:8000"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def api_get(path: str):
    with urllib.request.urlopen(f"{API}{path}", timeout=10) as r:
        return json.load(r)


WAV_B64 = base64.b64encode((OUT / "answer.wav").read_bytes()).decode()

SHIM = """
(() => {
  const B64 = "%s";
  const bytes = Uint8Array.from(atob(B64), c => c.charCodeAt(0));
  const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  window.__micLog = [];
  navigator.mediaDevices.getUserMedia = async (c) => {
    if (!c || !c.audio) return real(c);
    const ctx = new AudioContext();
    await ctx.resume();
    const buf = await ctx.decodeAudioData(bytes.buffer.slice(0));
    const dest = ctx.createMediaStreamDestination();
    window.__mic = { ctx, buf, dest, spoke: false };
    window.__speak = () => {
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(dest);
      src.start();
      window.__mic.spoke = true;
      window.__micLog.push("speak@" + new Date().toISOString());
      return buf.duration;
    };
    window.__micLog.push("stream handed to app, ctx=" + ctx.state + ", dur=" + buf.duration);
    return dest.stream;
  };
})();
""" % WAV_B64

STATE_JS = """
JSON.stringify({
  ring: (document.querySelector('[role=status]') || {}).textContent || '',
  body: document.body.innerText.slice(0, 2000),
  micLog: window.__micLog || null,
})
"""


class CDP:
    def __init__(self, ws):
        self.ws, self.n = ws, 0

    async def call(self, method, **params):
        self.n += 1
        mid = self.n
        await self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    async def js(self, expr, await_promise=True):
        r = await self.call("Runtime.evaluate", expression=expr,
                            returnByValue=True, awaitPromise=await_promise)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("text"))
        return r.get("result", {}).get("value")

    async def shot(self, name):
        r = await self.call("Page.captureScreenshot", format="png")
        (OUT / f"{name}.png").write_bytes(base64.b64decode(r["data"]))
        log(f"снимок: {OUT.name}/{name}.png")


def launch():
    args = [str(CHROME), "--headless=new", f"--remote-debugging-port={PORT}",
            f"--user-data-dir={OUT}/chrome-profile",
            "--use-fake-ui-for-media-stream",
            "--autoplay-policy=no-user-gesture-required",
            "--no-first-run", "--no-default-browser-check", "--disable-gpu", APP]
    log("запускаю Chromium")
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def page_target():
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as r:
                for t in json.load(r):
                    if t["type"] == "page" and "5273" in t.get("url", ""):
                        return t
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("страница не появилась")


async def main():
    before = api_get("/sessions/interviews")
    log(f"сессий в БД до прогона: {before['total']}")
    proc = launch()
    result = {}
    try:
        t = page_target()
        async with websockets.connect(t["webSocketDebuggerUrl"], max_size=None) as ws:
            cdp = CDP(ws)
            await cdp.call("Page.enable")
            await cdp.call("Runtime.enable")
            await cdp.call("Page.addScriptToEvaluateOnNewDocument", source=SHIM)
            await cdp.call("Page.reload")
            await asyncio.sleep(2.5)
            log("шим микрофона установлен, страница перезагружена")

            async def state():
                return json.loads(await cdp.js(STATE_JS))

            async def wait_ring(needle, limit, tag):
                end, last = time.time() + limit, ""
                while time.time() < end:
                    st = await state()
                    if st["ring"] != last:
                        log(f"  UI: {st['ring']!r}")
                        last = st["ring"]
                    if needle.lower() in st["ring"].lower():
                        log(f"дождался «{needle}» — {tag}")
                        return True
                    await asyncio.sleep(1)
                log(f"НЕ дождался «{needle}» за {limit:.0f} с (последнее {last!r})")
                return False

            ok = await cdp.js("""(() => {
                const b = [...document.querySelectorAll('button')]
                  .find(x => x.textContent.toLowerCase().includes('start mock'));
                if (!b) return false; b.click(); return true; })()""")
            log(f"клик «Start Mock Interview»: {ok}")
            await cdp.shot("01-started")

            await wait_ring("Speaking", 90, "Генри заговорил")
            await cdp.shot("02-henry-speaking")

            if not await wait_ring("Listening", 240, "микрофон открыт (echo-защита отпустила)"):
                result["verdict"] = "mic-never-opened"
                return
            await cdp.shot("03-listening")

            dur = await cdp.js("window.__speak ? window.__speak() : null")
            log(f"кандидат отвечает: {dur} с звука подано в поток")

            got_thinking = await wait_ring("Thinking", 120, "VAD закрыл запись, ответ ушёл в STT+LLM")
            st = await state()
            await cdp.shot("04-mid-turn")
            log(f"micLog: {st['micLog']}")
            log("текст на экране перед закрытием:\n" + st["body"][:900])

            if not got_thinking:
                result["verdict"] = "no-turn-started"
                result["ui"] = st["body"][:900]
                return

            log(">>> ЗАКРЫВАЮ ВКЛАДКУ посередине хода, без End session")
            closed_at = time.time()
            try:
                await cdp.call("Page.close")
            except Exception as e:
                log(f"Page.close: {e}")
            result["closed_at"] = closed_at
            result["verdict"] = "closed-mid-turn"

        await asyncio.sleep(8)
    finally:
        after = api_get("/sessions/interviews")
        newest = after["items"][0] if after["items"] else None
        result.update(before=before["total"], after=after["total"], newest=newest)
        if newest:
            try:
                d = api_get(f"/sessions/interviews/{newest['id']}")
                tr = d.get("transcript") or d.get("turns") or []
                result["turns"] = [{"role": x.get("role"), "text": (x.get("text") or "")[:200]}
                                   for x in tr] if isinstance(tr, list) else str(d)[:400]
            except Exception as e:
                result["turns"] = f"ошибка: {e}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        log("Chromium закрыт")


if __name__ == "__main__":
    asyncio.run(main())
