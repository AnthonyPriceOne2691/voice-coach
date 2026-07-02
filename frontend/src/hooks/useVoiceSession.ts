// WebSocket + mic capture + VAD + playback — the Phase 1 voice loop client side.

import { useCallback, useRef, useState } from "react";
import { AudioQueue } from "../lib/audioQueue";
import { SilenceDetector, rmsDbfs } from "../lib/vad";
import { clientMessage, parseServerMessage, type SessionState } from "../types/messages";

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
  const refs = useRef<SessionRefs>({
    ws: null,
    stream: null,
    recorder: null,
    audioContext: null,
    vadTimer: null,
    detector: new SilenceDetector(),
    queue: null,
    serverState: "idle",
  });

  const startRecorder = useCallback(() => {
    const r = refs.current;
    if (!r.stream || r.recorder?.state === "recording") return;
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
    const samples = new Uint8Array(analyser.fftSize);
    r.vadTimer = window.setInterval(() => {
      if (r.serverState !== "listening") return; // mic paused while agent speaks (doc 15)
      analyser.getByteTimeDomainData(samples);
      const event = r.detector.update(rmsDbfs(samples), performance.now());
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

  const handleMessage = useCallback(
    (raw: string) => {
      const message = parseServerMessage(raw);
      if (!message) return;
      const r = refs.current;
      if (message.type === "state") {
        r.serverState = message.payload.value;
        setState(message.payload.value);
        if (message.payload.value === "listening") startRecorder();
      } else if (message.type === "transcript") {
        setTranscript((prev) => [...prev, message.payload]);
      } else if (message.type === "audio") {
        void r.queue?.enqueue(message.payload.chunk_base64);
      } else if (message.type === "error") {
        setError(`${message.payload.code}: ${message.payload.message}`);
        if (!message.payload.recoverable) setActive(false);
      } else if (message.type === "session_ended") {
        setActive(false);
        setState("idle");
      }
    },
    [startRecorder],
  );

  const start = useCallback(async () => {
    setError(null);
    setTranscript([]);
    const r = refs.current;
    r.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    r.audioContext = new AudioContext();
    r.queue = new AudioQueue(r.audioContext, () => {});
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${location.host}/ws/session`);
    r.ws = ws;
    ws.onmessage = (event) => handleMessage(String(event.data));
    ws.onopen = () => {
      ws.send(clientMessage("hello"));
      ws.send(clientMessage("start_interview"));
    };
    ws.onerror = () => setError("WebSocket connection failed — is the backend running?");
    setActive(true);
    startVadLoop();
  }, [handleMessage, startVadLoop]);

  const end = useCallback(() => {
    const r = refs.current;
    r.ws?.send(clientMessage("end_session", { reason: "user" }));
    if (r.vadTimer !== null) window.clearInterval(r.vadTimer);
    r.recorder?.state === "recording" && r.recorder.stop();
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
    });
    setActive(false);
    setState("idle");
  }, []);

  return { state, transcript, error, active, start, end };
}
