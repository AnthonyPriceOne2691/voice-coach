import { useEffect, useState } from "react";

import { api } from "../lib/api";

/**
 * Переключатель «Live transcript» (Settings, doc 17): показывать ли транскрипт
 * ВО ВРЕМЯ сессии. Читается при входе на экран — вкладки монтируются заново,
 * поэтому изменение в Settings видно сразу по возвращении. Пока ответа нет или
 * бэкенд молчит — умолчание doc 17 (ON). Общий для интервью и разговора: у
 * переключателя должен быть читатель на КАЖДОМ экране сессии (L69, L71).
 */
export function useLiveTranscriptSetting(): boolean {
  const [show, setShow] = useState(true);
  useEffect(() => {
    let alive = true;
    api
      .getSettings()
      .then((s) => {
        if (alive) setShow(s.show_live_transcript !== false);
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);
  return show;
}
