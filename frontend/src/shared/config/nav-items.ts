import type { PageMeta } from "../types/page-meta";

export type NavItem = PageMeta & {
  to: string;
};

export const primaryNavItems: NavItem[] = [
  { to: "/dashboard", title: "Dashboard", description: "Cross-module overview" },
  { to: "/news", title: "News", description: "Intelligence workbench" },
  { to: "/macro", title: "Macro", description: "Indicators and comparisons" },
  { to: "/market", title: "Market", description: "Signals and watchlists" },
  { to: "/events", title: "Events", description: "Timeline and watch windows" },
  { to: "/push", title: "Push Center", description: "Templates and schedules" },
];

export const secondaryNavItems: NavItem[] = [
  { to: "/settings", title: "Settings", description: "Preferences and system defaults" },
];
