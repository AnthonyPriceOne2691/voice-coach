import type { ReactNode } from "react";

import { formatSessionSpan } from "../lib/format";
import type { TalkListItem } from "../types/api";

type Span = Pick<TalkListItem, "started_at" | "ended_at" | "duration_sec" | "status">;

/**
 * Голова строки History — когда шла сессия и чем кончилась, плюс таблетки.
 *
 * Общая у интервью и разговора: вторая копия этой разметки — clone-пара для jscpd
 * (снимок 0) и два места, где «not finished» разъехалось бы молча (L16).
 */
export function SessionWhen({ item, children }: { item: Span; children?: ReactNode }) {
  return (
    <div>
      <div className="row-when">
        {formatSessionSpan(item.started_at, item.ended_at, item.duration_sec)}
      </div>
      <div className="row-sub">
        <span>{item.status === "completed" ? "Completed" : "Interrupted"}</span>
        {children}
      </div>
    </div>
  );
}
