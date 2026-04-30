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

export const moduleRootNavItems: NavItem[] = [
  { to: "/push", title: "Push Center", description: "Templates and schedules" },
];

export const primaryNavItems: NavItem[] = [...moduleRootNavItems];

export const secondaryNavItems: NavItem[] = [
  { to: "/settings", title: "Settings", description: "Preferences and system defaults" },
];

export const moduleDirectories: ModuleDirectory[] = [
  {
    id: "push",
    item: moduleRootNavItems[0],
    children: [
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
