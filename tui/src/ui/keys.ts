export type KeyAction =
  | "quit"
  | "start"
  | "stop"
  | "focus_next"
  | "focus_prev"
  | "toggle_log"
  | "save";

export type KeyEventLike = {
  key?: string;
  name?: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
};

export function mapKey(ev: KeyEventLike): KeyAction | null {
  const k = (ev.key || ev.name || "").toLowerCase();
  if (ev.ctrl && k === "c") return "quit";
  if (k === "q" || k === "escape") return "quit";
  if (k === "enter") return "start";
  if (k === "tab") return ev.shift ? "focus_prev" : "focus_next";
  if (k === "l") return "toggle_log";
  if (k === "s") return "save";
  if (k === "x") return "stop";
  return null;
}
