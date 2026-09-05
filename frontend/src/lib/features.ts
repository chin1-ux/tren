/**
 * Feature flags — flip these to enable/disable in-development features.
 * These flags hide UI elements without deleting any route or component files.
 * Set to true to re-enable.
 */
export const FEATURES = {
  GENERATE_ENABLED: true,
  IDEAS_ENABLED: true,
  DEALS_ENABLED: false,
  MARKETPLACE_ENABLED: false,
  INSTAGRAM_OAUTH_ENABLED: false,
  CALENDAR_ENABLED: true,
} as const;
