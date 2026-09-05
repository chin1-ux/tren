/**
 * Canonical niche identifiers for the Trendrop classification system.
 *
 * This is the single source of truth for niche IDs used across the app.
 * The list is intentionally small and stable — it maps to backend
 * trend-classification buckets. Adding a niche here is a product decision
 * that requires corresponding backend support.
 *
 * Each consuming file may compose its own display shape (labels, emojis,
 * hooks) from these identifiers.
 */
export const CANONICAL_NICHES = [
  "dance",
  "fashion",
  "travel",
  "food",
  "comedy",
  "motivation",
  "fitness",
  "current_affairs",
  "devotional",
  "tech",
  "narrative_edit",
  "romance_relationship",
  "all",
] as const;

export type NicheId = (typeof CANONICAL_NICHES)[number];

/** Display labels for each canonical niche. */
export const NICHE_LABELS: Record<NicheId, string> = {
  dance: "Dance",
  fashion: "Fashion",
  travel: "Travel",
  food: "Food",
  comedy: "Comedy",
  motivation: "Motivation",
  fitness: "Fitness",
  current_affairs: "Current Affairs",
  devotional: "Devotional",
  tech: "Tech",
  narrative_edit: "Creative Edit",
  romance_relationship: "Romance & Relationships",
  all: "All",
};
