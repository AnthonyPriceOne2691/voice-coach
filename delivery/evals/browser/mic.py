#!/usr/bin/env python
"""Выбор микрофона в настоящем браузере — пункт приёмки M9 (поставка mic-device).

Зачем отдельным сценарием: jsdom не имеет ни устройств, ни разрешений, ни
`AudioContext`. Тесты проверяют вызовы к подменённому `navigator.mediaDevices`,
и остаётся ровно один вопрос, на который они ответить не могут: **как настоящий
браузер называет ошибку**, когда сохранённого входа больше нет. Весь видимый
фолбэк держится на строке `OverconstrainedError`; ошибись в ней — и вместо
сообщения человек получит молчание.

Chromium запускается с фальшивым устройством (`--use-fake-device-for-media-stream`),
поэтому стенду НЕ нужны ни ollama, ни whisper, ни Piper — только vite и backend.
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

import websockets

S = pathlib.Path(__file__).parent
OUT = pathlib.Path(os.environ.get("BROWSER_EVAL_OUT", S / "out"))
OUT.mkdir(parents=True, exist_ok=True)
APP = os.environ.get("APP_URL", "http://localhost:5273")
API = os.environ.get("API_URL", "http://127.0.0.1:8000")
CHROME = pathlib.Path(
    os.environ.get(
        "CHROME_BIN",
        str(
            pathlib.Path.home()
            / "Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64"
            / "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        ),
    )
)
PORT = 9446
GONE_ID = "definitely-not-a-real-device-id"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok' if ok else 'ПРОВАЛ'}: {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def patch_settings(payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API}/settings", data=body, method="PATCH",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


def get_settings() -> dict:
    with urllib.request.urlopen(f"{API}/settings", timeout=5) as r:
        return json.load(r)


proc = subprocess.Popen(
    [
        str(CHROME), "--headless=new", f"--remote-debugging-port={PORT}",
        f"--user-data-dir={OUT}/mic-profile", "--no-first-run", "--no-default-browser-check",
        "--disable-gpu", "--window-size=1100,900",
        # Фальшивый вход + автоматически выданное разрешение: сценарий про
        # ПОВЕДЕНИЕ экрана, а не про диалог macOS.
        "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
        f"{APP}/",
    ],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)


async def main() -> None:
    target = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as r:
                target = next(
                    (x for x in json.load(r) if x["type"] == "page" and "5273" in x.get("url", "")),
                    None,
                )
            if target:
                break
        except Exception:
            pass
        time.sleep(0.5)
    if not target:
        print("Chromium не поднялся — см. CHROME_BIN")
        failures.append("chromium")
        return

    counter = 0

    async def call(ws, method, **params):
        nonlocal counter
        counter += 1
        await ws.send(json.dumps({"id": counter, "method": method, "params": params}))
        while True:
            message = json.loads(await ws.recv())
            if message.get("id") == counter:
                return message.get("result", {})

    async def js(ws, expression, wait=False):
        r = await call(ws, "Runtime.evaluate", returnByValue=True,
                       awaitPromise=wait, expression=expression)
        return r.get("result", {}).get("value")

    async with websockets.connect(target["webSocketDebuggerUrl"], max_size=None) as ws:
        await call(ws, "Page.enable")
        await call(ws, "Runtime.enable")
        await asyncio.sleep(3)

        # --- 1. Сохранённый вход, которого нет: экран обязан СКАЗАТЬ об этом.
        patch_settings({"mic_device_id": GONE_ID})
        await js(ws, "location.reload()")
        await asyncio.sleep(3)
        await js(
            ws,
            "[...document.querySelectorAll('button')]"
            ".find(b => b.textContent.trim() === 'Settings')?.click()",
        )
        await asyncio.sleep(2)
        screen = await js(ws, "document.body.innerText")
        check("сохранённый вход показан как отсутствующий",
              "not connected" in screen, "строка «Saved microphone — not connected»")

        await js(
            ws,
            "[...document.querySelectorAll('button')]"
            ".find(b => b.textContent.trim() === 'Test')?.click()",
        )
        await asyncio.sleep(3)
        screen = await js(ws, "document.body.innerText")
        # ⚠ ГЛАВНАЯ проверка стенда: имя ошибки настоящего Chromium.
        check("пропажа входа объявлена, а не проглочена",
              "not there any more" in screen,
              "сработала ветка OverconstrainedError в openMicrophone")

        # --- 2. Реальный (фальшивый) вход выбирается и сохраняется.
        devices = await js(ws, """(async () => {
          const list = await navigator.mediaDevices.enumerateDevices();
          return JSON.stringify(list.filter(d => d.kind === 'audioinput')
            .map(d => ({id: d.deviceId, label: d.label})));
        })()""", wait=True)
        inputs = json.loads(devices or "[]")
        check("браузер отдаёт входы с именами", bool(inputs) and bool(inputs[0]["label"]),
              str([d["label"] for d in inputs]))
        if not inputs:
            return

        picked = next((d for d in inputs if d["id"] != "default"), inputs[0])
        await js(ws, f"""(() => {{
          const select = document.querySelector('.mic-picker select');
          if (!select) return false;
          const setter = Object.getOwnPropertyDescriptor(
            window.HTMLSelectElement.prototype, 'value').set;
          setter.call(select, {json.dumps(picked["id"])});
          select.dispatchEvent(new Event('change', {{ bubbles: true }}));
          return true;
        }})()""")
        await asyncio.sleep(2)
        saved = get_settings()["mic_device_id"]
        check("выбор доехал до базы", saved == picked["id"], f"{saved!r}")

        # --- 3. Проверка уровня: поток открыт на выбранном входе и слышит.
        await js(
            ws,
            "[...document.querySelectorAll('button')]"
            ".find(b => b.textContent.trim() === 'Test')?.click()",
        )
        # ⚠ Шаг опроса 0.3 s выбран НЕ на глаз. Фальшивый вход Chromium — это
        # гудок с периодом ровно 1 s, и опрос с шагом 0.5 s попадает в одну и ту
        # же фазу каждый раз: первый прогон стенда дал 20 замеров подряд «silent»
        # при работающей полоске (замерено отдельно: −10…−121 dBFS). Дробный шаг
        # обходит фазу по кругу. Оракул, который врёт от совпадения периодов,
        # хуже отсутствующего.
        heard = False
        seen: list[str] = []
        for _ in range(20):
            await asyncio.sleep(0.3)
            meter = await js(ws, "document.querySelector('.mic-meter')?.title ?? 'НЕТ ПОЛОСКИ'")
            status = await js(ws, "document.querySelector('.mic-meter-status')?.textContent ?? ''")
            seen.append(meter)
            if status.strip() == "hearing you":
                heard = True
                print(f"     уровень: {meter}")
                break
        check("полоска слышит выбранный вход", heard, "" if heard else f"замеры: {seen[:6]}")

        shot = await call(ws, "Page.captureScreenshot", format="png")
        (OUT / "mic-settings.png").write_bytes(base64.b64decode(shot["data"]))
        print(f"снимок: {OUT.name}/mic-settings.png")

        # Вернуть настройку в исходное — стенд не оставляет следов в базе.
        patch_settings({"mic_device_id": None})


try:
    asyncio.run(main())
finally:
    proc.terminate()

print("\nИТОГ:", "PASS" if not failures else f"FAIL ({', '.join(failures)})")
sys.exit(0 if not failures else 1)
