const THEME_STORAGE_KEY = "geoview-theme";
const DEFAULT_THEME = "light";
const AVAILABLE_THEMES = new Set(["light", "dark"]);
const THEME_CHANGE_EVENT = "geoview-theme-change";

function normalizeTheme(theme) {
  return AVAILABLE_THEMES.has(theme) ? theme : DEFAULT_THEME;
}

export function getStoredTheme() {
  try {
    return normalizeTheme(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch (error) {
    return DEFAULT_THEME;
  }
}

export function getCurrentTheme() {
  if (typeof document === "undefined") {
    return DEFAULT_THEME;
  }

  return normalizeTheme(document.documentElement.dataset.theme);
}

export function applyTheme(theme) {
  if (typeof document === "undefined") {
    return DEFAULT_THEME;
  }

  const nextTheme = normalizeTheme(theme);
  const root = document.documentElement;

  root.dataset.theme = nextTheme;
  root.style.colorScheme = nextTheme;

  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
  } catch (error) {
    // Ignore persistence issues and keep the live theme applied.
  }

  window.dispatchEvent(
    new CustomEvent(THEME_CHANGE_EVENT, {
      detail: {
        theme: nextTheme,
      },
    })
  );

  return nextTheme;
}

export function initializeTheme() {
  return applyTheme(getStoredTheme());
}

export function toggleTheme() {
  return applyTheme(getCurrentTheme() === "dark" ? "light" : "dark");
}

export { DEFAULT_THEME, THEME_STORAGE_KEY, THEME_CHANGE_EVENT };
