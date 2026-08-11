// WebSocket + mic capture + VAD + playback — the Phase 1 voice loop client side.

import { useCallback, useRef, useState } from "react";
import { AudioQueue } from "../lib/audioQueue";
import { SilenceDetector, rmsDbfs } from "../lib/vad";
import { clientMessage, parseServerMessage, type SessionState } from "../types/messages";

export interface SessionEnded {
  session_kind: "interview" | "review";
  session_id: string;
  next_action: "offer_review" | "generate_summary" | "none";
}

export interface TranscriptEntry {
  role: "user" | "agent";
  text: string;
}

interface SessionRefs {
  ws: WebSocket | null;
  stream: MediaStream | null;
  recorder: MediaRecorder | null;
  audioContext: AudioContext | null;
  vadTimer: number | null;
  detector: SilenceDetector;
  queue: AudioQueue | null;
  serverState: SessionState;
  playing: boolean; // agent audio still coming out of the speakers
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

export function useVoiceSession() {
  const [state, setState] = useState<SessionState>("idle");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState(false);
  const [micLevel, setMicLevel] = useState(-Infinity); // dBFS, for the level meter
  const [playingUi, setPlayingUi] = useState(false); // agent audio audible right now
  const [ended, setEnded] = useState<SessionEnded | null>(null);
  const refs = useRef<SessionRefs>({
    ws: null,
    stream: null,
    recorder: null,
    audioContext: null,
    vadTimer: null,
    detector: new SilenceDetector(),
    queue: null,
    serverState: "idle",
    playing: false,
  });

  const startRecorder = useCallback(() => {
    const r = refs.current;
    // Mic only when the server listens AND agent audio finished playing —
    // otherwise VAD picks up the agent's own voice from the speakers.
    if (!r.stream || r.playing || r.serverState !== "listening") return;
    if (r.recorder?.state === "recording") return;
    const recorder = new MediaRecorder(r.stream, { mimeType: "audio/webm;codecs=opus" });
    const chunks: Blob[] = [];
    recorder.ondataavailable = (event) => chunks.push(event.data);
    recorder.onstop = async () => {
      const audio = await blobToBase64(new Blob(chunks, { type: "audio/webm" }));
      r.ws?.send(clientMessage("utterance_end", { audio_base64: audio, mime: "audio/webm" }));
    };
    recorder.start();
    r.recorder = recorder;
    r.detector.reset();
  }, []);

  const startVadLoop = useCallback(() => {
    const r = refs.current;
    if (!r.audioContext || !r.stream) return;
    const analyser = r.audioContext.createAnalyser();
    analyser.fftSize = 2048;
    r.audioContext.createMediaStreamSource(r.stream).connect(analyser);
    const samples = new Float32Array(analyser.fftSize);
    r.vadTimer = window.setInterval(() => {
      analyser.getFloatTimeDomainData(samples);
      const dbfs = rmsDbfs(samples);
      setMicLevel(dbfs);
      if (r.serverState !== "listening" || r.playing) return; // mic paused while agent speaks
      const event = r.detector.update(dbfs, performance.now());
      if (event === "utterance_end" && r.recorder?.state === "recording") {
        r.recorder.stop();
        r.recorder = null;
      } else if (event === "discarded" && r.recorder?.state === "recording") {
        r.recorder.ondataavailable = null;
        r.recorder.onstop = null;
        r.recorder.stop();
        r.recorder = null;
        startRecorder();
      }
    }, 50);
  }, [startRecorder]);

  // Разбор входящих сообщений разложен по одному обработчику на тип. Раньше это
  // была одна цепочка if/else с цикломатической сложностью 11 при пороге 10
  // (гейт сложности, ts-половина). Ветвление осталось ровно одно — switch по
  // типу; всё, что делает КАЖДЫЙ тип, живёт в своей функции и читается целиком.

  const onServerState = useCallback(
    (value: SessionState) => {
      refs.current.serverState = value;
      setState(value);
      // Микрофон открывается только здесь: сервер сказал, что слушает.
      if (value === "listening") startRecorder();
    },
    [startRecorder],
  );

  const onAudioChunk = useCallback((chunk: string) => {
    const r = refs.current;
    if (chunk) {
      r.playing = true;
      setPlayingUi(true);
    }
    void r.queue?.enqueue(chunk);
  }, []);

  const onServerError = useCallback(
    (payload: { code: string; message: string; recoverable: boolean }) => {
      setError(`${payload.code}: ${payload.message}`);
      if (!payload.recoverable) setActive(false);
    },
    [],
  );

  const onSessionEnded = useCallback((payload: SessionEnded) => {
    setActive(false);
    setState("idle");
    setEnded(payload);
  }, []);

  const handleMessage = useCallback(
    (raw: string) => {
      const message = parseServerMessage(raw);
      if (!message) return;
      switch (message.type) {
        case "state":
          return onServerState(message.payload.value);
        case "transcript":
          return setTranscript((prev) => [...prev, message.payload]);
        case "audio":
          return onAudioChunk(message.payload.chunk_base64);
        case "error":
          return onServerError(message.payload);
        case "session_ended":
          return onSessionEnded(message.payload as SessionEnded);
      }
    },
    [onServerState, onAudioChunk, onServerError, onSessionEnded],
  );

  const start = useCallback(
    async (review?: { interviewId: string }) => {
      setError(null);
      setTranscript([]);
      setEnded(null);
      const r = refs.current;
      r.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      r.audioContext = new AudioContext();
      r.queue = new AudioQueue(r.audioContext, () => {
        // Agent finished speaking through the speakers — now it's safe to open the mic.
        r.playing = false;
        setPlayingUi(false);
        r.detector.reset();
        startRecorder();
      });
      const protocol = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${protocol}://${location.host}/ws/session`);
      r.ws = ws;
      ws.onmessage = (event) => handleMessage(String(event.data));
      ws.onopen = () => {
        ws.send(clientMessage("hello"));
        if (review) {
          ws.send(clientMessage("start_review", { interview_id: review.interviewId }));
        } else {
          ws.send(clientMessage("start_interview"));
        }
      };
      ws.onerror = () => setError("WebSocket connection failed — is the backend running?");
      ws.onclose = (event) => {
        if (!event.wasClean) setError("Connection lost — restart the backend and try again.");
        setActive(false);
        setState("idle");
      };
      setActive(true);
      startVadLoop();
    },
    [handleMessage, startVadLoop, startRecorder],
  );

  const end = useCallback(() => {
    const r = refs.current;
    r.ws?.send(clientMessage("end_session", { reason: "user" }));
    if (r.vadTimer !== null) window.clearInterval(r.vadTimer);
    if (r.recorder?.state === "recording") r.recorder.stop();
    r.stream?.getTracks().forEach((track) => track.stop());
    void r.audioContext?.close();
    r.ws?.close();
    Object.assign(refs.current, {
      ws: null,
      stream: null,
      recorder: null,
      audioContext: null,
      vadTimer: null,
      queue: null,
      serverState: "idle",
      playing: false,
    });
    setActive(false);
    setState("idle");
  }, []);

  // What the user should see: while agent audio is audible, we are "speaking",
  // no matter that the server already flipped to "listening".
  const uiState: SessionState = playingUi ? "speaking" : state;

  return { state: uiState, transcript, error, active, micLevel, ended, start, end };
}
