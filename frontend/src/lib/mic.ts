// Микрофонные устройства: список, разрешение, открытие выбранного входа.
// Всё, что знает про `navigator.mediaDevices`, живёт здесь — голосовой цикл и
// экран настроек берут вход отсюда и не повторяют constraints по-своему.

export interface MicDevice {
  deviceId: string;
  label: string;
}

export interface OpenedMic {
  stream: MediaStream;
  /** Открыт НЕ тот вход, который просили: сохранённого устройства больше нет. */
  fellBackToDefault: boolean;
}

/** Входные устройства. До выдачи разрешения браузер отдаёт их с пустым `label`. */
export async function listMicrophones(): Promise<MicDevice[]> {
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices
    .filter((d) => d.kind === "audioinput")
    .map((d) => ({ deviceId: d.deviceId, label: d.label }));
}

/**
 * Имена скрыты, пока нет разрешения — это единственный честный признак.
 * Пустой список тоже считается скрытым: на macOS без гранта Safari отдаёт ноль
 * устройств, и «микрофонов нет» тут значило бы неправду.
 */
export function labelsHidden(devices: MicDevice[]): boolean {
  return devices.length === 0 || devices.every((d) => d.label === "");
}

/** Открыть и сразу же погасить поток — единственный способ получить имена. */
export async function requestMicAccess(): Promise<void> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  stopStream(stream);
}

export function stopStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}

/**
 * Устройства нет — в отличие от «пользователь не дал доступ».
 *
 * Разделение существенное: пропажу входа мы лечим фолбэком на системный по
 * умолчанию, а отказ в доступе фолбэком «лечить» нельзя — сессия всё равно не
 * начнётся, и подмена причины оставит человека без объяснения.
 */
function deviceIsGone(error: unknown): boolean {
  const name = (error as { name?: string } | null)?.name;
  return name === "OverconstrainedError" || name === "NotFoundError";
}

/**
 * Открыть выбранный вход. `null` — системный по умолчанию (поведение до появления
 * настройки).
 *
 * `deviceId: { exact }`, а НЕ `{ ideal }`: `ideal` при пропаже устройства молча
 * откроет другой микрофон, и человек узнает об этом по плохому распознаванию, а
 * не из интерфейса. Фолбэк здесь есть, но он возвращает флаг — и вызывающий
 * обязан сказать о нём вслух.
 */
export async function openMicrophone(deviceId: string | null): Promise<OpenedMic> {
  const media = navigator.mediaDevices;
  if (!deviceId) {
    return { stream: await media.getUserMedia({ audio: true }), fellBackToDefault: false };
  }
  try {
    const stream = await media.getUserMedia({ audio: { deviceId: { exact: deviceId } } });
    return { stream, fellBackToDefault: false };
  } catch (error) {
    if (!deviceIsGone(error)) throw error;
    return { stream: await media.getUserMedia({ audio: true }), fellBackToDefault: true };
  }
}
