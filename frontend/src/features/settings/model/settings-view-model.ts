import { primaryNavItems, secondaryNavItems } from "../../../shared/config/nav-items";
import { NEWS_MODE_OPTIONS } from "../../../shared/hooks/use-news-mode";

export type SettingsDraft = {
  defaultRoute: string;
  defaultNewsMode: string;
  showMarketTicker: boolean;
};

export function buildSettingsViewModel(draft: SettingsDraft) {
  return {
    pageTitle: "Settings",
    pageDescription: "Workspace defaults that shape the shell, route entrypoint, and news fetch mode.",
    sections: [
      {
        id: "workspace",
        title: "Workspace preferences",
        description: "Persist the shell defaults used when the workbench opens without explicit URL state.",
      },
      {
        id: "current",
        title: "Current defaults",
        description: "A compact summary of the defaults the shell will pick up next.",
      },
    ],
    defaultRouteOptions: [...primaryNavItems, ...secondaryNavItems].map((item) => ({
      value: item.to,
      label: item.title,
      description: item.description,
    })),
    newsModeOptions: NEWS_MODE_OPTIONS,
    summaryRows: [
      { label: "Default landing page", value: draft.defaultRoute },
      { label: "Default news mode", value: draft.defaultNewsMode },
      { label: "Market ticker", value: draft.showMarketTicker ? "Visible" : "Hidden" },
    ],
  };
}
