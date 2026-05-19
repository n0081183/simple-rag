export const en = {
  app: {
    name: "SIWZ-RAG Lite",
    tagline: "Cortex requirement verification",
  },
  nav: {
    verify: "Verify requirements",
    kb: "Knowledge base",
    settings: "Settings",
  },
  verify: {
    title: "Requirement verification",
    subtitle: "Upload SIWZ/RFP or paste requirements, then review and verify against Cortex documentation.",
    upload: "Upload PDF or DOCX",
    paste: "Paste requirements",
    pastePlaceholder: "Paste requirement text or supplement uploaded document…",
    product: "Cortex product",
    autoDetect: "Auto-detect product",
    autoDetectWarning:
      "Automatic product matching — requires verification by a Cortex specialist before submitting the report.",
    extract: "Extract requirements",
    review: "Review extracted requirements",
    runVerification: "Run verification",
    emptyTitle: "No requirements yet",
    emptyDescription: "Upload a document or paste text to begin extraction.",
  },
  kb: {
    title: "Build / update knowledge base",
    subtitle: "Sync Cortex documentation on a remote GPU pod and download a portable index.",
    stepCredentials: "RunPod credentials",
    stepScope: "Sync scope",
    stepProgress: "Progress",
    apiKey: "RunPod API key",
    podId: "Pod ID / SSH host",
    testConnection: "Test connection",
    start: "Start sync",
    incremental: "Incremental (skip unchanged)",
    fullRebuild: "Full rebuild",
    releaseNotes: "Release notes (not recommended)",
    noKb: "No knowledge base loaded",
    noKbHint: "Run a sync to enable verification against live documentation.",
  },
  settings: {
    title: "Settings",
    language: "Interface language",
    theme: "Theme",
    themeLight: "Light",
    themeDark: "Dark",
    themeSystem: "System",
    llm: "LLM quality",
    llmLocal: "Local (Ollama, offline)",
    llmCloud: "Cloud API (premium)",
  },
  common: {
    loading: "Loading…",
    error: "An error occurred",
    save: "Save",
    cancel: "Cancel",
  },
} as const;

export type TranslationKeys = {
  [K in keyof typeof en]: {
    [P in keyof (typeof en)[K]]: string;
  };
};
