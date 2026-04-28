import { primaryNavItems, secondaryNavItems } from "../../../shared/config/nav-items";

export type SettingsDraft = {
  defaultRoute: string;
};

export function buildSettingsViewModel(draft: SettingsDraft) {
  return {
    pageTitle: "Settings",
    pageDescription: "Workspace defaults that shape the shell route entrypoint.",
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
    summaryRows: [
      { label: "Default landing page", value: draft.defaultRoute },
    ],
  };
}
