export type TrendCategory =
  | "Dance"
  | "Scenic"
  | "Fashion"
  | "Travel"
  | "Food"
  | "Comedy"
  | "Devotional"
  | "Festival"
  | "Motivation"
  | "Fitness"
  | "Study"
  | "Narrative"
  | "Text Overlay"
  | "Viral";

export interface Trend {
  id: string;
  song: string;
  artist: string;
  hoursLeft: number;
  viralMultiplier: number;
  contentType: string;
  contentTypeEmoji: string;
  category: TrendCategory;
  language?: string;
  languageEmoji?: string;
  isDance: boolean;
  isNarrativeEdit: boolean;
  idealContentDescription: string;
  cameraStyle: string;
  hashtags: string[];
}

export const mockTrends: Trend[] = [
  {
    id: "1",
    song: "Espresso",
    artist: "Sabrina Carpenter",
    hoursLeft: 18,
    viralMultiplier: 12,
    contentType: "Scenic",
    contentTypeEmoji: "🎬",
    category: "Scenic",
    isDance: false,
    isNarrativeEdit: true,
    idealContentDescription: "Slow cinematic clips of morning coffee rituals, golden hour light through windows, hands stirring foam.",
    cameraStyle: "Handheld with slow push-ins, shallow depth of field.",
    hashtags: ["#espresso", "#morningvibes", "#aesthetic", "#reels"],
  },
  {
    id: "2",
    song: "Aaj Ki Raat",
    artist: "Sachin-Jigar",
    hoursLeft: 6,
    viralMultiplier: 28,
    contentType: "Dance",
    contentTypeEmoji: "💃",
    category: "Dance",
    language: "Hindi",
    languageEmoji: "🌍",
    isDance: true,
    isNarrativeEdit: false,
    idealContentDescription: "Group dance with the signature hook step at the chorus drop. Bright outfits, festive setting.",
    cameraStyle: "Static wide shot, then cut to close-up on hook step.",
    hashtags: ["#aajkiraat", "#stree2", "#danceindia", "#hookstep"],
  },
  {
    id: "3",
    song: "Beautiful Things",
    artist: "Benson Boone",
    hoursLeft: 36,
    viralMultiplier: 8,
    contentType: "Travel",
    contentTypeEmoji: "✈️",
    category: "Travel",
    isDance: false,
    isNarrativeEdit: true,
    idealContentDescription: "Montage of travel moments — boarding passes, mountain peaks, candid laughter, sunsets over water.",
    cameraStyle: "Mix of POV and wide drone-style shots, quick cuts on beat.",
    hashtags: ["#travel", "#wanderlust", "#beautifulthings", "#reels"],
  },
  {
    id: "4",
    song: "Bachpan Ka Pyaar",
    artist: "Sahdev Dirdo",
    hoursLeft: 12,
    viralMultiplier: 15,
    contentType: "Dance",
    contentTypeEmoji: "💃",
    category: "Dance",
    language: "Kannada",
    languageEmoji: "🌍",
    isDance: true,
    isNarrativeEdit: false,
    idealContentDescription: "Solo dance with playful lip-sync, school-throwback aesthetic, simple footwork.",
    cameraStyle: "Front-facing phone camera, mid-shot framing.",
    hashtags: ["#bachpankapyaar", "#nostalgia", "#dancereel", "#kannada"],
  },
  {
    id: "5",
    song: "Paint The Town Red",
    artist: "Doja Cat",
    hoursLeft: 24,
    viralMultiplier: 10,
    contentType: "Fashion",
    contentTypeEmoji: "👗",
    category: "Fashion",
    isDance: false,
    isNarrativeEdit: true,
    idealContentDescription: "Outfit transitions in bold red looks, mirror flips, confident walk-toward-camera shots.",
    cameraStyle: "Vertical mirror selfies, snap transitions on the beat.",
    hashtags: ["#ootd", "#redaesthetic", "#fashionreel", "#fyp"],
  },
  {
    id: "6",
    song: "Cinnamon Girl",
    artist: "Lana Del Rey",
    hoursLeft: 48,
    viralMultiplier: 6,
    contentType: "Food",
    contentTypeEmoji: "🍳",
    category: "Food",
    isDance: false,
    isNarrativeEdit: true,
    idealContentDescription: "Warm, slow food shots — cinnamon dusting, dough kneading, steam rising from a fresh bake.",
    cameraStyle: "Overhead static + slow tilt-downs, warm color grade.",
    hashtags: ["#foodreel", "#bakingtiktok", "#cozyvibes", "#aesthetic"],
  },
  {
    id: "7",
    song: "Tum Hi Ho",
    artist: "Arijit Singh",
    hoursLeft: 9,
    viralMultiplier: 22,
    contentType: "Viral",
    contentTypeEmoji: "🔥",
    category: "Viral",
    language: "Hindi",
    languageEmoji: "🌍",
    isDance: false,
    isNarrativeEdit: true,
    idealContentDescription: "Emotional photo montage with text overlays — moments with loved ones, candid smiles, slow fades.",
    cameraStyle: "Still photos with subtle Ken Burns zoom, soft transitions.",
    hashtags: ["#tumhiho", "#emotional", "#reels", "#trendingnow"],
  },
];

export const trendCategories: ("All" | TrendCategory)[] = [
  "All", "Dance", "Scenic", "Fashion", "Travel", "Food", "Viral",
];
