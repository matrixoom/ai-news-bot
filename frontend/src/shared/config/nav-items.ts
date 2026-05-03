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
  { to: "/macro-data", title: "Macro Data", description: "GDP, credit, leverage, and prices" },
  { to: "/push", title: "Push Center", description: "Templates and schedules" },
];

export const primaryNavItems: NavItem[] = [...moduleRootNavItems];

export const secondaryNavItems: NavItem[] = [
  { to: "/settings", title: "Settings", description: "Preferences and system defaults" },
];

export const moduleDirectories: ModuleDirectory[] = [
  {
    id: "macro-data",
    item: moduleRootNavItems[0],
    children: [
      {
        to: "/macro-data?tab=gdp",
        title: "GDP",
        ariaLabel: "Macro Data > GDP",
        description: "Nominal and real GDP",
      },
      {
        to: "/macro-data?tab=credit",
        title: "信贷",
        ariaLabel: "Macro Data > 信贷",
        description: "Household and corporate new loans, leverage, and social financing",
      },
      {
        to: "/macro-data?tab=climate",
        title: "景气",
        ariaLabel: "Macro Data > 景气",
        description: "Manufacturing and non-manufacturing PMI",
      },
      {
        to: "/macro-data?tab=trade",
        title: "外贸",
        ariaLabel: "Macro Data > 外贸",
        description: "Imports and exports",
      },
      {
        to: "/macro-data?tab=prices",
        title: "物价",
        ariaLabel: "Macro Data > 物价",
        description: "PPI and CPI",
      },
      {
        to: "/macro-data?tab=currency",
        title: "货币",
        ariaLabel: "Macro Data > 货币",
        description: "M0, M1, M2 money supply",
      },
    ],
    defaultExpanded: true,
  },
  {
    id: "push",
    item: moduleRootNavItems[1],
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
