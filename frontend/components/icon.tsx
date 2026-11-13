import type { CSSProperties } from "react";

export type IconName = "activity" | "home" | "plus" | "chart" | "meal" | "pill" | "bell" | "settings" | "user" | "users" | "arrow" | "shield" | "clock" | "search" | "logout" | "check" | "moon" | "heart" | "message";

const paths: Record<IconName, React.ReactNode> = {
  activity: <><path d="M3 12h4l3-8 4 16 3-8h4" /></>,
  home: <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-8H9v8H4a1 1 0 0 1-1-1Z" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  chart: <><path d="M4 3v17h17M8 14l4-5 4 3 5-7" /></>,
  meal: <><path d="M5 3v7m3-7v7M2 3v7c0 3 6 3 6 0M5 13v8M19 3c-4 3-4 10 0 10h2V3Zm2 10v8" /></>,
  pill: <><path d="m14 4-10 10a4.25 4.25 0 0 0 6 6L20 10a4.25 4.25 0 0 0-6-6ZM9 9l6 6" /></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
  settings: <><path d="m9 3-1 3-3 1-2 4 2 2v3l4 3 3-1 3 1 4-3v-3l2-2-2-4-3-1-1-3Z" /><circle cx="12" cy="11" r="3" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21v-2a8 8 0 0 1 16 0v2" /></>,
  users: <><circle cx="9" cy="8" r="3.5" /><path d="M2 21v-2a7 7 0 0 1 14 0v2M17 4a4 4 0 0 1 0 8M22 21v-2a7 7 0 0 0-4-6" /></>,
  arrow: <><path d="M4 12h16m-6-6 6 6-6 6" /></>,
  shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z" /><path d="m8 12 3 3 5-6" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 6v6l4 2" /></>,
  search: <><circle cx="10" cy="10" r="6" /><path d="m15 15 6 6" /></>,
  logout: <><path d="M10 3H4v18h6M8 12h13m-5-5 5 5-5 5" /></>,
  check: <><path d="m4 12 5 5L20 6" /></>,
  moon: <><path d="M21 13a9 9 0 0 1-10-10 9 9 0 1 0 10 10Z" /></>,
  heart: <><path d="M20 5a5 5 0 0 0-8 1 5 5 0 0 0-8-1c-6 6 8 16 8 16S26 11 20 5Z" /></>,
  message: <><path d="M21 4H3v13h5l4 4 4-4h5Z" /><path d="M7 8h10M7 12h7" /></>,
};

export function Icon({ name, size = 20, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="ui-icon" style={style}>{paths[name]}</svg>;
}
