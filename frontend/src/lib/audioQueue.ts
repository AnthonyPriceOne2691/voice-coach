// Sequential playback queue for streamed WAV chunks (doc 07: AudioContext queue).

export function base64ToArrayBuffer(b64: string): ArrayBuffer {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

export class AudioQueue {
  private nextStartTime = 0;
  private pending = 0;

  constructor(
    private readonly context: AudioContext,
    private readonly onDrained: () => void,
  ) {}

  async enqueue(chunkBase64: string): Promise<void> {
    if (!chunkBase64) return;
    this.pending += 1;
    const buffer = await this.context.decodeAudioData(base64ToArrayBuffer(chunkBase64));
    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.context.destination);
    const startAt = Math.max(this.context.currentTime, this.nextStartTime);
    this.nextStartTime = startAt + buffer.duration;
    source.onended = () => {
      this.pending -= 1;
      if (this.pending === 0) this.onDrained();
    };
    source.start(startAt);
  }
}
