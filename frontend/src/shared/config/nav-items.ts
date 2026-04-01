import type { PageMeta } from "../types/page-meta";

export type NavItem = PageMeta & {
  to: string;
  ariaLabel?: string;
};

export type ModuleDirectory = {
  id: string;
  item: NavItem;
  children: NavItem[];
  defaultExpanded?: boolean;
};

export const dashboardNavItem: NavItem = {
  to: "/dashboard",
  title: "Dashboard",
  description: "Cross-module overview",
};

export const moduleRootNavItems: NavItem[] = [
  { to: "/news", title: "News", description: "Intelligence workbench" },
  { to: "/macro", title: "Macro", description: "Indicators and comparisons" },
  { to: "/market", title: "Market", description: "Signals and watchlists" },
  { to: "/events", title: "Events", description: "Timeline and watch windows" },
  { to: "/push", title: "Push Center", description: "Templates and schedules" },
];

export const primaryNavItems: NavItem[] = [dashboardNavItem, ...moduleRootNavItems];

export const secondaryNavItems: NavItem[] = [
  { to: "/status", title: "Status", description: "Freshness and source health" },
  { to: "/settings", title: "Settings", description: "Preferences and system defaults" },
];

export const moduleDirectories: ModuleDirectory[] = [
  {
    id: "news",
    item: moduleRootNavItems[0],
    children: [
      {
        to: "/news?tab=channels",
        title: "Topics",
        ariaLabel: "News > Topics",
        description: "Technology, finance, and policy channels",
      },
      {
        to: "/news?tab=sources",
        title: "Sources",
        ariaLabel: "News > Sources",
        description: "Upstream state and mode options",
      },
      {
        to: "/news?tab=brief",
        title: "Brief",
        ariaLabel: "News > Brief",
        description: "Compact daily summary",
      },
    ],
    defaultExpanded: false,
  },
  {
    id: "macro",
    item: moduleRootNavItems[1],
    children: [
      {
        to: "/macro?tab=overview",
        title: "Overview",
        ariaLabel: "Macro > Overview",
        description: "Pair-level summary",
      },
      {
        to: "/macro?tab=compare",
        title: "Compare",
        ariaLabel: "Macro > Compare",
        description: "Side-by-side pairs",
      },
      {
        to: "/macro?tab=sources",
        title: "Sources",
        ariaLabel: "Macro > Sources",
        description: "Official source register",
      },
    ],
    defaultExpanded: false,
  },
  {
    id: "market",
    item: moduleRootNavItems[2],
    children: [
      {
        to: "/market?tab=overview",
        title: "Overview",
        ariaLabel: "Market > Overview",
        description: "Signal overview",
      },
      {
        to: "/market?tab=signals",
        title: "Signals",
        ariaLabel: "Market > Signals",
        description: "Signal matrix",
      },
      {
        to: "/market?tab=watchlist",
        title: "Watchlist",
        ariaLabel: "Market > Watchlist",
        description: "Focus names",
      },
    ],
    defaultExpanded: false,
  },
  {
    id: "events",
    item: moduleRootNavItems[3],
    children: [
      {
        to: "/events?tab=week",
        title: "近一周",
        ariaLabel: "Events > 近一周",
        description: "7-day event window",
      },
      {
        to: "/events?tab=month",
        title: "近1个月",
        ariaLabel: "Events > 近1个月",
        description: "30-day event window",
      },
      {
        to: "/events?tab=halfyear",
        title: "近6个月",
        ariaLabel: "Events > 近6个月",
        description: "6-month event window",
      },
    ],
    defaultExpanded: false,
  },
  {
    id: "push",
    item: moduleRootNavItems[4],
    children: [
      {
        to: "/push?tab=overview",
        title: "Overview",
        ariaLabel: "Push Center > Overview",
        description: "Config and preview",
      },
      {
        to: "/push?tab=schedules",
        title: "Schedules",
        ariaLabel: "Push Center > Schedules",
        description: "Run schedule rules",
      },
      {
        to: "/push?tab=history",
        title: "History",
        ariaLabel: "Push Center > History",
        description: "Recent run records",
      },
    ],
    defaultExpanded: false,
  },
];
