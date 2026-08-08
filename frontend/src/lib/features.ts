/**
 * Feature flags — flip these to enable/disable in-development features.
 * GENERATE_ENABLED = false hides the Generate tab from the bottom nav and all
 * generate CTAs throughout the app, without deleting any route or component files.
 * Set to true to re-enable.
 */
export const FEATURES = {
  GENERATE_ENABLED: false,
} as const;
