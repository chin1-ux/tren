/**
 * Indian Audio Semantic Identification Engine
 * 
 * Multi-tiered deterministic classifier to detect Indian origin audios
 * (Bollywood, South Indian, Punjabi, Indian Indie, Indian Devotional, Indian Instrumentals)
 * even when Romanized in English script or mislabeled as 'en' or 'instrumental'.
 */

// 1. Unicode Script Ranges for Indian Languages
const INDIAN_SCRIPT_REGEX = /[\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F]/;

// 2. High-Confidence Indian Artists, Singers, Composers, and Producers
const INDIAN_ARTISTS_SET = new Set([
  // Hindi / Bollywood / Pop
  "arijit singh", "arijit", "jubin nautiyal", "jubin", "neha kakkar", "tony kakkar", "sonu nigam",
  "shreya ghoshal", "shreya", "sunidhi chauhan", "sunidhi", "pritam", "armaan malik", "amal mallik",
  "amaal mallik", "badshah", "honey singh", "yo yo honey singh", "raftaar", "mc stan", "divine",
  "emiway", "king", "anuv jain", "darshan raval", "jasleen royal", "jasleen", "b praak", "jaani",
  "tanishk bagchi", "tanishk", "sachin jigar", "sachin-jigar", "amit trivedi", "vishal shekhar",
  "vishal dadlani", "shekhar ravjiani", "shankar mahadevan", "shankar ehsaan loy", "udit narayan",
  "kumar sanu", "alka yagnik", "kavita krishnamurthy", "lata mangeshkar", "asha bhosle", "kishore kumar",
  "mohammed rafi", "rafi", "m.m. keeravani", "keeravani", "payal dev", "rochak kohli", "mithoon",
  "ankit tiwari", "himesh reshammiya", "atif aslam", "rahat fateh ali khan", "rahat fateh",
  "nusrat fateh ali khan", "nusrat", "ali zafar", "mohit chauhan", "javed ali", "kk", "kay kay",
  "lucky ali", "pankaj udhas", "jagjit singh", "anuradha paudwal", "sadhana sargam", "alisha chinai",
  "babul supriyo", "shaan", "palash sen", "zubeen garg", "kumaar", "shaarib toshi", "ansh chahal",
  "sadhu tiwari", "aishwarya majmudar", "aghori muzik", "antara nandy", "sharvi yadav",
  "stebin ben", "asees kaur", "dhvani bhanushali", "tulsi kumar", "parampara tandon", "sachet tandon",
  "sachet-parampara", "shilpa rao", "monali thakur", "neeti mohan", "jonita gandhi",

  // South Indian (Tamil, Telugu, Malayalam, Kannada)
  "kavya ajit", "anirudh ravichander", "anirudh", "a.r. rahman", "ar rahman", "rahman", "a r rahman",
  "harris jayaraj", "yuvan shankar raja", "yuvan", "g.v. prakash", "gv prakash", "d. imman", "imman",
  "santhosh narayanan", "vidyasagar", "ilayaraja", "ilaiyaraaja", "s.p. balasubrahmanyam", "spb",
  "k.j. yesudas", "kj yesudas", "yesudas", "chithra", "k.s. chithra", "sujatha", "swarnalatha",
  "s. janaki", "sid sriram", "pradeep kumar", "haricharan", "karthik", "naresh iyer", "vijay yesudas",
  "shaan rahman", "sushin shyam", "gopi sundar", "jakes bejoy", "heshem abdul wahab", "hesaham abdul",
  "deepak dev", "m. jayachandran", "stephen devassy", "devi sri prasad", "dsp", "thaman s", "thaman",
  "mickey j meyer", "mani sharma", "sai abhyankkar", "dhibu ninan thomas", "ravi basrur", "arjun janya",
  "v. harikrishna", "charan raj", "b. ajaneesh loknath", "vasuki vaibhav", "gana muthu", "vishnu edavan",
  "mohanlal", "mammootty", "dulquer", "fahadh", "vijay", "suriya", "dhanush", "rajinikanth",
  "kamal haasan", "allu arjun", "mahesh babu", "ram charan", "prabhas", "pawan kalyan", "chiranjeevi",
  "yash", "sudeep", "darshan", "puneeth", "sanjith hegde", "vijay prakash", "rajeesh k chandu",
  "vineeth sreenivasan", "kalabhavan mani",

  // Punjabi & Regional
  "diljit dosanjh", "diljit", "ap dhillon", "karan aujla", "shubh", "sidhu moose wala", "sidhu moosewala",
  "ammy virk", "harrdy sandhu", "harvy sandhu", "guru randhawa", "jass manak", "parmish verma",
  "mankirt aulakh", "kulwinder billa", "amrit maan", "tarsem jassar", "satinder sartaaj", "babbu maan",
  "jordan sandhu", "cheema y", "gur sidhu", "dhanda nyoliwala", "sukhe", "arjan dhillon", "navaan sandhu",
  "prem dhillon", "hustinder", "sukha", "manni sandhu", "korala maan", "balkar sidhu", "nirvair pannu",
  "rajvir jawanda", "gagan kokri", "harjit harman", "maninder buttar", "ninja", "sippy gill", "sharry mann",
  "sunanda sharma", "daler mehndi", "mika singh", "gurdas maan", "surjit bindrakhia",
  "masoom sharma", "renuka panwar", "sapna choudhary", "pranjal dahiya", "ashu twinkle",
  "osman mir", "kirtidan gadhavi", "aditya gadhvi", "kaushik bharwad", "kinjal dave", "geeta rabari",
  "pawan singh", "khesari lal", "khesari", "shilpi raj", "manoj tiger", "pramod premi", "tuntun yadav",
  "neelkamal singh", "samar singh", "arvind akela kallu", "dinesh lal yadav nirahua",

  // Record Labels & Channel Entities
  "t-series", "tseries", "zee music company", "zee music", "sony music india", "sony music",
  "yrf", "tips official", "tips music", "saregama", "speed records", "white hill music",
  "aditya music", "lahari music", "think music", "times music", "desi music factory",
  "vyrl originals", "svf music", "geetha arts", "mythri movie makers", "anand audio"
]);

// 3. Romanized Indian Vocabulary & Phonetic Word Tokens
// Whole-word matching will be applied so English words (e.g., "humble", "illuminate") are not misflagged.
const INDIAN_WORDS_SET = new Set([
  // Pronouns & Possessives
  "tum", "hum", "mera", "meri", "mere", "tera", "teri", "tere", "tujhe", "tujhko", "mujhko",
  "apna", "apni", "apne", "humara", "tumhara", "unka", "unki", "inhe", "unhe", "main", "tu",

  // Verbs & Common Helpers
  "aana", "jaana", "aao", "jao", "dekha", "dekh", "sun", "suno", "kaho", "bol", "bolo",
  "karna", "hua", "hui", "hue", "hoga", "hogi", "hoge", "kare", "karo", "raha", "rahi", "rahe",
  "tha", "thi", "the", "hai", "hain", "nahi", "nahin", "mat", "kyun", "kahan", "kaise",
  "kabhi", "saath", "paas", "door", "phir", "aaj", "kal", "hoga", "chhod", "leke", "aaye",

  // Romantic & Emotional Themes
  "dil", "ishq", "pyar", "pyaar", "mohabbat", "deewana", "deewani", "jaan", "jaana", "zindagi",
  "khushi", "dard", "aashiqui", "sanam", "yaara", "yaar", "dosti", "dua", "mann", "khuda",
  "maula", "rooh", "nazar", "aankhen", "ankhon", "chehra", "sajna", "sajni", "makhna", "heeriye",
  "ranjha", "sohneya", "billo", "nakhra", "kudi", "munda", "jatt", "gabru", "mutiyar", "channa",
  "akhiyaan", "akhiyan", "raatan", "raataan", "kesariya", "chaleya", "kahani", "dhadkan", "ehsaas",
  "beintehaa", "humsafar", "baatein", "dastaan", "fiza", "sukoon", "junoon", "bekhabar", "deewanapan",

  // Cultural, Religious & Classical Genre Keywords
  "bhajan", "aarti", "arti", "chalisa", "kirtan", "qawwali", "ghazal", "shayari", "sufi",
  "bhangra", "garba", "dandiya", "thumri", "carnatic", "hindustani", "sitar", "tabla", "bansuri",
  "shehnai", "dhun", "jugalbandi", "mandir", "puja", "pooja", "darshan", "mata", "ganpati",
  "krishna", "kanha", "radha", "shiva", "shiv", "mahadev", "hanuman", "ram", "shri ram", "sita",
  "bajrangbali", "tiranga", "desh", "bharat", "vande", "mataram",

  // Regional Terms & Movie Industries
  "bollywood", "tollywood", "kollywood", "mollywood", "sandalwood", "bhojpuri", "haryanvi",
  "marathi", "gujarati", "punjabi", "tamil", "telugu", "malayalam", "kannada", "bengali",
  "desi", "pind", "mitran", "patola", "soch", "judai", "tasveer", "tere bin", "tum hi",

  // Specific viral titles known to leak
  "mahave", "mamave", "marjaavaan", "lut gaye", "kabir singh", "animal", "jawan", "pathaan",
  "dunki", "brahmastra", "pushpa", "rrr", "kgf", "kantara", "kalki", "leo", "jailer", "vikram"
]);

// 4. Indian Language Codes
export const INDIAN_LANG_CODES = new Set([
  "hi", "hindi", "pa", "punjabi", "ta", "tamil", "te", "telugu", "ml", "malayalam",
  "kn", "kannada", "bn", "bengali", "mr", "marathi", "gu", "gujarati", "ne", "nepali",
  "bho", "bhojpuri", "hne", "mai", "or", "as", "sa", "ur"
]);

/**
 * Normalizes text to lowercase alphanumeric space-padded string
 */
function normalize(str: string): string {
  if (!str) return "";
  return str.toLowerCase().replace(/[^a-z0-9]/g, " ").replace(/\s+/g, " ").trim();
}

/**
 * Checks whether an audio track has Indian origin / Indian language characteristics.
 * Returns true if the track is Indian (should NEVER appear in Global filter).
 */
export function isIndianAudio(trend: {
  song?: string;
  artist?: string;
  rawLanguage?: string;
  language?: string;
  languageFinal?: string;
  fallbackLanguage?: string;
  discoverySource?: string;
  trendOrigin?: string;
  hashtags?: string[];
}): boolean {
  if (!trend) return false;

  // 1. Check Explicit Indian Language Codes
  const rawLang = normalize(trend.rawLanguage || "");
  const lblLang = normalize(trend.language || "");
  const finalLang = normalize(trend.languageFinal || "");
  const fbLang = normalize(trend.fallbackLanguage || "");

  if (
    INDIAN_LANG_CODES.has(rawLang) ||
    INDIAN_LANG_CODES.has(lblLang) ||
    INDIAN_LANG_CODES.has(finalLang) ||
    INDIAN_LANG_CODES.has(fbLang)
  ) {
    return true;
  }

  // 2. Check Native Indian Scripts in Song Title or Artist Name
  const rawSong = trend.song || "";
  const rawArtist = trend.artist || "";
  const rawHashtags = (trend.hashtags || []).join(" ");
  const combinedRaw = `${rawSong} ${rawArtist} ${rawHashtags}`;

  if (INDIAN_SCRIPT_REGEX.test(combinedRaw)) {
    return true;
  }

  // 3. Check Trend Origin & Indian Discovery Source
  const origin = (trend.trendOrigin || "").toUpperCase().trim();
  if (origin === "IN") {
    return true;
  }

  const src = normalize(trend.discoverySource || "");
  if (
    src.includes("india") ||
    src.includes("hindi") ||
    src.includes("punjabi") ||
    src.includes("tamil") ||
    src.includes("telugu") ||
    src.includes("malayalam") ||
    src.includes("kannada") ||
    src.includes("bhojpuri") ||
    src.includes("marathi")
  ) {
    return true;
  }

  // 4. Normalize Title & Artist for Semantic Keyword / Name Matching
  const songNorm = normalize(rawSong);
  const artistNorm = normalize(rawArtist);
  const combinedNorm = ` ${songNorm} ${artistNorm} `;

  // 4a. Check Indian Artist Names
  for (const artist of INDIAN_ARTISTS_SET) {
    if (combinedNorm.includes(` ${artist} `)) {
      return true;
    }
  }

  // 4b. Check Indian Word Tokens (word boundary matching)
  // Split title and artist into words and check presence in dictionary
  const tokens = `${songNorm} ${artistNorm}`.split(" ").filter(w => w.length >= 2);
  let indianWordMatchCount = 0;

  for (const token of tokens) {
    if (INDIAN_WORDS_SET.has(token)) {
      // Strong single-word triggers
      if (
        token === "tum" || token === "aana" || token === "mera" || token === "meri" ||
        token === "tera" || token === "teri" || token === "tujhe" || token === "apna" ||
        token === "apni" || token === "dil" || token === "ishq" || token === "pyar" ||
        token === "pyaar" || token === "mohabbat" || token === "deewana" || token === "kesariya" ||
        token === "chaleya" || token === "bhajan" || token === "aarti" || token === "chalisa" ||
        token === "bollywood" || token === "punjabi" || token === "bhangra" || token === "garba" ||
        token === "mahave" || token === "mamave" || token === "ajit" || token === "kavya" ||
        token === "jatt" || token === "sohneya" || token === "heeriye" || token === "ranjha"
      ) {
        return true;
      }
      indianWordMatchCount++;
      if (indianWordMatchCount >= 2) {
        return true;
      }
    }
  }

  // 4c. Special phrase checks for multi-word titles (e.g. "tum hi aana", "o maahi", "kal ho naa ho")
  if (
    combinedNorm.includes(" tum hi ") ||
    combinedNorm.includes(" tum hi aana ") ||
    combinedNorm.includes(" o maahi ") ||
    combinedNorm.includes(" tere bin ") ||
    combinedNorm.includes(" kavya ajit ") ||
    combinedNorm.includes(" jubin nautiyal ") ||
    combinedNorm.includes(" payal dev ")
  ) {
    return true;
  }

  return false;
}
