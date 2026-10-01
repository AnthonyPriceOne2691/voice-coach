#!/usr/bin/env python
"""Порог тишины из Settings в настоящем браузере: пауза посреди фразы.

Что проверяет: ползунок «Silence before end-of-turn» доходит до VAD страницы.
Реплика кандидата — две половины фразы с паузой PAUSE_S между ними. Прогон
идёт дважды: порог выше паузы (запись обязана пережить паузу и закрыться
ОДИН раз, после второй половины) и порог ниже паузы (запись закрывается на
паузе, вторая половина в ход не попадает).

Что настоящее: Chromium, страница приложения, её VAD, MediaRecorder, WebSocket,
whisper. Что имитировано: только источник звука (как в `stand.py`), плюс
перехват `WebSocket.send` — по нему видно, КОГДА страница закрыла реплику.

Каждый прогон начинает новую сессию: порог применяется со следующего старта.
Исходное значение порога возвращается в базу в конце прогона.
"""

import asyncio
import base64
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request
import wave

import websockets

S = pathlib.Path(__file__).parent
ROOT = S.parents[2]
OUT = pathlib.Path(os.environ.get("BROWSER_EVAL_OUT", S / "out"))
OUT.mkdir(parents=True, exist_ok=True)
CHROME = os.environ.get("CHROME_BIN") or str(
    pathlib.Path.home()
    / "Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64"
    / "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)
PORT = 9223  # не 9222: стенд `stand.py` может быть открыт рядом
APP = os.environ.get("APP_URL", "http://localhost:5273") + "/"
API = os.environ.get("API_URL", "http://127.0.0.1:8000")

PAUSE_S = 2.5
FIRST = "I built an internal tool for speech."
SECOND = "Then I made it stream every sentence to the speaker."
# порог, мс → обязана ли реплика пережить паузу
CASES = [(3000, True), (800, False)]
# Закрытие реплики ждём в момент «конец речи + порог». Допуск покрывает шаг
# опроса VAD (50 мс), хвост тишины, который Piper оставляет в конце половины
# фразы, и задержку аудиотракта. Умолчание 2 s от обоих порогов дальше допуска,
# поэтому без проводки настройки краснеют ОБА случая, а не один.
TOLERANCE_S = 0.4


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def api(path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method="PATCH" if body is not None else "GET",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def make_wav() -> pathlib.Path:
    """Две половины фразы голосом Piper и тишина PAUSE_S между ними, 16 кГц моно."""
    from piper import PiperVoice, SynthesisConfig

    target = OUT / "pause.wav"
    if target.is_file():
        return target
    voice = PiperVoice.load(str(ROOT / "data/models/piper/en_US-ryan-medium.onnx"))
    parts = []
    for i, text in enumerate((FIRST, SECOND)):
        raw = OUT / f"pause_part{i}.wav"
        with wave.open(str(raw), "wb") as w:
            voice.synthesize_wav(text, w, syn_config=SynthesisConfig(length_scale=1.0))
        parts.append(raw)
    gap = OUT / "pause_gap.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-t", str(PAUSE_S),
         "-i", "anullsrc=r=16000:cl=mono", str(gap)],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(parts[0]), "-i", str(gap),
         "-i", str(parts[1]), "-filter_complex",
         "[0:a]aresample=16000,aformat=channel_layouts=mono[a];"
         "[2:a]aresample=16000,aformat=channel_layouts=mono[c];"
         "[a][1:a][c]concat=n=3:v=0:a=1",
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(target)],
        check=True,
    )
    log(f"синтезирована реплика с паузой {PAUSE_S} с: {target.name}")
    return target


def first_half_s() -> float:
    """Длительность первой половины фразы — до паузы."""
    with wave.open(str(OUT / "pause_part0.wav"), "rb") as w:
        return w.getnframes() / w.getframerate()


SHIM = """
(() => {
  const B64 = "%s";
  const bytes = Uint8Array.from(atob(B64), c => c.charCodeAt(0));
  const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  window.__sent = [];
  const send = WebSocket.prototype.send;
  WebSocket.prototype.send = function (data) {
    try {
      const m = JSON.parse(data);
      if (m.type === "utterance_end") window.__sent.push(performance.now());
    } catch (e) {}
    return send.call(this, data);
  };
  navigator.mediaDevices.getUserMedia = async (c) => {
    if (!c || !c.audio) return real(c);
    const ctx = new AudioContext();
    await ctx.resume();
    const buf = await ctx.decodeAudioData(bytes.buffer.slice(0));
    const dest = ctx.createMediaStreamDestination();
    window.__speak = () => {
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(dest);
      src.start();
      window.__spokeAt = performance.now();
      return buf.duration;
    };
    return dest.stream;
  };
})();
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

    async def js(self, expr):
        r = await self.call("Runtime.evaluate", expression=expr,
                            returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("text"))
        return r.get("result", {}).get("value")


def launch():
    args = [CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
            f"--user-data-dir={OUT}/chrome-profile-silence",
            "--use-fake-ui-for-media-stream",
            "--autoplay-policy=no-user-gesture-required",
            "--no-first-run", "--no-default-browser-check", "--disable-gpu", APP]
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def page_target():
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as r:
                for t in json.load(r):
                    if t["type"] == "page" and APP.rstrip("/") in t.get("url", ""):
                        return t
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("страница не появилась")


async def wait_ring(cdp, needle, limit):
    end = time.time() + limit
    while time.time() < end:
        ring = await cdp.js("(document.querySelector('[role=status]') || {}).textContent || ''")
        if needle.lower() in ring.lower():
            return True
        await asyncio.sleep(0.5)
    return False


async def one_case(wav_b64: str, threshold_ms: int, must_survive: bool) -> dict:
    api("/settings", {"silence_threshold_ms": threshold_ms})
    log(f"порог {threshold_ms} мс записан в Settings; новая сессия")
    proc = launch()
    result: dict = {"threshold_ms": threshold_ms}
    try:
        t = page_target()
        async with websockets.connect(t["webSocketDebuggerUrl"], max_size=None) as ws:
            cdp = CDP(ws)
            await cdp.call("Page.enable")
            await cdp.call("Runtime.enable")
            await cdp.call("Page.addScriptToEvaluateOnNewDocument", source=SHIM % wav_b64)
            await cdp.call("Page.reload")
            await asyncio.sleep(2.5)
            clicked = await cdp.js("""(() => {
                const b = document.querySelector('[data-testid="start-interview"]')
                  || [...document.querySelectorAll('button')]
                       .find(x => /^start/i.test(x.textContent.trim()));
                if (!b) return false; b.click(); return true; })()""")
            if not clicked:
                result["verdict"] = "start-button-not-found"
                return result
            if not await wait_ring(cdp, "Listening", 240):
                result["verdict"] = "mic-never-opened"
                return result
            duration = await cdp.js("window.__speak()")
            # реплика + самый длинный порог + запас на опрос VAD
            await asyncio.sleep(duration + max(c[0] for c in CASES) / 1000 + 1.5)
            spoke_at = await cdp.js("window.__spokeAt")
            sent = await cdp.js("window.__sent")
            closes = [round((x - spoke_at) / 1000, 2) for x in sent]
            result.update(audio_s=round(duration, 2), utterance_end_at_s=closes)
            # Первое закрытие ДО конца звука = пауза оборвала реплику, вторая
            # половина в ход не попала. После конца звука = реплика пережила паузу.
            result["survived_pause"] = bool(closes) and closes[0] >= duration
            expected = (duration if must_survive else first_half_s()) + threshold_ms / 1000
            result["expected_close_s"] = round(expected, 2)
            on_time = bool(closes) and abs(closes[0] - expected) <= TOLERANCE_S
            result["verdict"] = "PASS" if on_time else "FAIL"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    return result


async def main() -> int:
    wav = make_wav()
    wav_b64 = base64.b64encode(wav.read_bytes()).decode()
    original = api("/settings")["silence_threshold_ms"]
    log(f"исходный порог в Settings: {original} мс")
    results = []
    try:
        for threshold_ms, must_survive in CASES:
            results.append(await one_case(wav_b64, threshold_ms, must_survive))
    finally:
        api("/settings", {"silence_threshold_ms": original})
        log(f"порог возвращён: {original} мс")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r.get("verdict") == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
