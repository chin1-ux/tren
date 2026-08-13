/**
 * Feature flags — flip these to enable/disable in-development features.
 * These flags hide UI elements without deleting any route or component files.
 * Set to true to re-enable.
 */
export const FEATURES = {
  GENERATE_ENABLED: false,
  IDEAS_ENABLED: false,
  DEALS_ENABLED: false,
  INSTAGRAM_OAUTH_ENABLED: false,
  CALENDAR_ENABLED: false,
} as const;
