import { useEffect, useState } from "react";

export type ThemePreference = "light" | "dark";

const THEME_STORAGE_KEY = "dashboard-theme";

export function useThemePreference() {
  const [theme, setTheme] = useState<ThemePreference>(readInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", theme);
    root.style.colorScheme = theme;

    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Ignore storage failures and keep the in-memory theme state working.
    }
  }, [theme]);

  return {
    theme,
    setTheme: (nextTheme: ThemePreference) => {
      setTheme(nextTheme);
    },
    toggleTheme: () => {
      setTheme((current) => (current === "light" ? "dark" : "light"));
    },
  };
}

function readInitialTheme(): ThemePreference {
  try {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === "light" || storedTheme === "dark") {
      return storedTheme;
    }
  } catch {
    // Ignore storage failures and fall back to the calm default.
  }

  return "light";
}
