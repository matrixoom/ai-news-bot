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
  { to: "/event-outlook", title: "Event Outlook", description: "Technology, policy, and finance event calendar" },
  { to: "/notes", title: "Notes", description: "Workspace notes" },
  { to: "/push", title: "Push Center", description: "Templates and schedules" },
  { to: "/market-data", title: "Market Data", description: "Commodities, precious metals, and stock indices" },
  { to: "/trend-models", title: "Trend Models", description: "AI trend analysis and forecasting" },
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
      {
        to: "/macro-data?tab=expectations",
        title: "预期",
        ariaLabel: "Macro Data > 预期",
        description: "Bond yields, exchange rate, and credit spread",
      },
      {
        to: "/macro-data?tab=employment",
        title: "就业",
        ariaLabel: "Macro Data > 就业",
        description: "Unemployment insurance fund expense",
      },
    ],
    defaultExpanded: true,
  },
  {
    id: "push",
    item: moduleRootNavItems[3],
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
  {
    id: "market-data",
    item: moduleRootNavItems[4],
    children: [
      {
        to: "/market-data?tab=commodities",
        title: "商品",
        ariaLabel: "Market Data > 商品",
        description: "WTI原油、布伦特原油",
      },
      {
        to: "/market-data?tab=precious_metals",
        title: "贵金属",
        ariaLabel: "Market Data > 贵金属",
        description: "黄金、白银、铜",
      },
      {
        to: "/market-data?tab=stock_market",
        title: "股票市场",
        ariaLabel: "Market Data > 股票市场",
        description: "股指数据（待补充）",
      },
      {
        to: "/market-data?tab=real_estate",
        title: "房地产",
        ariaLabel: "Market Data > 房地产",
        description: "70城二手房价格指数",
      },
    ],
    defaultExpanded: true,
  },
  {
    id: "event-outlook",
    item: moduleRootNavItems[1],
    children: [
      {
        to: "/event-outlook?tab=domestic",
        title: "国内",
        ariaLabel: "Event Outlook > 国内",
        description: "China-region technology, policy, and finance events",
      },
      {
        to: "/event-outlook?tab=international",
        title: "国际",
        ariaLabel: "Event Outlook > 国际",
        description: "Global technology, policy, and finance events",
      },
      {
        to: "/event-outlook?tab=events",
        title: "事件列表",
        ariaLabel: "Event Outlook > 事件列表",
        description: "Structured events extracted from research materials",
      },
      {
        to: "/event-outlook?tab=topic-trace",
        title: "主题溯源",
        ariaLabel: "Event Outlook > 主题溯源",
        description: "Topic evolution with evidence-backed stages",
      },
      {
        to: "/event-outlook?tab=event-graph",
        title: "关系网络",
        ariaLabel: "Event Outlook > 关系网络",
        description: "Event relationship analysis canvas",
      },
    ],
    defaultExpanded: true,
  },
  {
    id: "notes",
    item: moduleRootNavItems[2],
    children: [],
    defaultExpanded: false,
  },
  {
    id: "trend-models",
    item: moduleRootNavItems[5],
    children: [],
    defaultExpanded: false,
  },
];
