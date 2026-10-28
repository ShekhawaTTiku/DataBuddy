type Preferences = { dark: boolean; sidebar: boolean; analysisTab: string };
const key = "databuddy.preferences.v1";
const tabs = ["Chart", "Result data", "Calculation"];

export function readPreferences(): Preferences {
  const defaults = { dark: false, sidebar: true, analysisTab: "Chart" };
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return {
      dark: typeof value?.dark === "boolean" ? value.dark : defaults.dark,
      sidebar:
        typeof value?.sidebar === "boolean" ? value.sidebar : defaults.sidebar,
      analysisTab: tabs.includes(value?.analysisTab)
        ? value.analysisTab
        : defaults.analysisTab,
    };
  } catch {
    return defaults;
  }
}

export function savePreferences(value: Preferences) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* Display preferences remain usable without browser storage. */
  }
}
