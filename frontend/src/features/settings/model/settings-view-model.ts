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
    ],
    defaultRouteOptions: [...primaryNavItems, ...secondaryNavItems].map((item) => ({
      value: item.to,
      label: item.title,
      description: item.description,
    })),
  };
}
