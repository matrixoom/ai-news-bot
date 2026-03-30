export type DashboardResponse = {
  hero: {
    eyebrow: string;
    title: string;
    summary: string;
  };
  stats: Array<{
    id: string;
    label: string;
    value: string;
    change: string;
  }>;
  brief: {
    title: string;
    summary: string;
    ctaLabel: string;
    ctaHref: string;
  };
  modules: Array<{
    id: string;
    title: string;
    summary: string;
    ctaLabel: string;
    ctaHref: string;
  }>;
};

export type DashboardViewModel = {
  hero: {
    eyebrow: string;
    title: string;
    summary: string;
  };
  stats: Array<{
    id: string;
    label: string;
    value: string;
    change: string;
  }>;
  brief: {
    title: string;
    summary: string;
    ctaLabel: string;
    ctaHref: string;
  };
  moduleSectionTitle: string;
  modules: Array<{
    id: string;
    title: string;
    summary: string;
    ctaLabel: string;
    ctaHref: string;
  }>;
};
