// Уровень выбранного входа на время проверки («Test» на экране настроек).
// Поток живёт ровно столько, сколько идёт проверка: экран настроек не должен
// держать индикатор записи macOS зажжённым всё время, пока он открыт.

import { useEffect, useState } from "react";

import { openMicrophone, stopStream } from "../lib/mic";
import { rmsDbfs } from "../lib/vad";

// Тот же шаг, что у голосового цикла: полоска должна показывать ровно то, по
// чему потом будет решать VAD, иначе проверка обманет (порог −50 dBFS).
const SAMPLE_MS = 50;
const FFT_SIZE = 2048;

const GONE = "That microphone is not there any more — showing the system default instead.";
const BLOCKED = "No microphone access — allow it in the browser to test the input.";

interface MicLevel {
  level: number;
  /** Что пошло не так; `null` — идёт нормальная проверка. */
  problem: string | null;
}

/** Держит открытым выбранный вход, пока `testing`, и меряет его уровень. */
export function useMicLevel(deviceId: string | null, testing: boolean): MicLevel {
  const [level, setLevel] = useState(-Infinity);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    if (!testing) return;
    setProblem(null);
    // Замыкание живёт дольше эффекта: пользователь успевает выключить проверку
    // или сменить устройство, пока браузер спрашивает разрешение.
    const opening = { cancelled: false };
    let stream: MediaStream | null = null;
    let context: AudioContext | null = null;
    let timer: number | null = null;

    const run = async () => {
      const opened = await openMicrophone(deviceId);
      if (opening.cancelled) return stopStream(opened.stream);
      if (opened.fellBackToDefault) setProblem(GONE);
      stream = opened.stream;
      context = new AudioContext();
      const analyser = context.createAnalyser();
      analyser.fftSize = FFT_SIZE;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Float32Array(analyser.fftSize);
      timer = window.setInterval(() => {
        analyser.getFloatTimeDomainData(samples);
        setLevel(rmsDbfs(samples));
      }, SAMPLE_MS);
    };

    void run().catch(() => setProblem(BLOCKED));

    return () => {
      opening.cancelled = true;
      if (timer !== null) window.clearInterval(timer);
      stopStream(stream);
      void context?.close();
      setLevel(-Infinity);
    };
  }, [deviceId, testing]);

  return { level, problem };
}
