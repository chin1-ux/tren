"""
ORDER 24: Artist-to-Language Static Mapping.
Seeded with near-certain Indian regional and global music artists to enable instant, zero-cost classification.
No Golden Checkpoint files touched.
"""

ARTIST_LANGUAGE_MAP = {
    # --- Punjabi (pa) ---
    "Jass Bajwa": "pa",
    "Cheema Y": "pa",
    "Gur Sidhu": "pa",
    "Gurdas Maan": "pa",
    "Miss Pooja": "pa",
    "Yo Yo Honey Singh": "pa",
    "Sidhu Moose Wala": "pa",
    "Karan Aujla": "pa",
    "Diljit Dosanjh": "pa",
    "Sharry Mann": "pa",
    "Amrinder Gill": "pa",
    "Gippy Grewal": "pa",
    "Kaka": "pa",
    "Kulwinder Billa": "pa",
    "Mankirt Aulakh": "pa",
    "Parmish Verma": "pa",
    "Tarsem Jassar": "pa",
    "Kulwant Khang": "pa",
    "Gulab Sidhu": "pa",
    "Jasmeen Akhtar": "pa",
    "Billa Sonipat Ala": "pa",
    "Gabbar Sangrur": "pa",

    # --- Tamil (ta) ---
    "Sai Abhyankkar": "ta",
    "Anirudh Ravichander": "ta",
    "G.V. Prakash Kumar": "ta",
    "Chitra": "ta",
    "K. S. Chithra": "ta",
    "Ilaiyaraaja": "ta",
    "D. Imman": "ta",
    "Anthony Daasan": "ta",
    "Gana Muthu": "ta",

    # --- Hindi (hi) ---
    "Arijit Singh": "hi",
    "Kishore Kumar": "hi",
    "Rahat Fateh Ali Khan": "hi",
    "Ajay-Atul": "hi",
    "Ajay Gogavale": "hi",
    "Mohit Chauhan": "hi",
    "Shreya Ghoshal": "hi",
    "Jatin-Lalit": "hi",
    "Udit Narayan": "hi",
    "Alka Yagnik": "hi",
    "Shankar-Ehsaan-Loy": "hi",
    "KK": "hi",
    "Sukhwinder Singh": "hi",
    "Mahalaxmi Iyer": "hi",
    "Shankar Mahadevan": "hi",
    "Geeta Rabari": "gu",  # Gujarati
    "Badshah": "hi",
    "Neha Kakkar": "hi",
    "Sonu Nigam": "hi",
    "Kumar Sanu": "hi",
    "Lata Mangeshkar": "hi",
    "Mohammed Rafi": "hi",
    "Anu Malik": "hi",
    "Pritam": "hi",
    "Mithoon": "hi",
    "Vishal-Shekhar": "hi",
    "Sachin-Jigar": "hi",
    "Ankit Tiwari": "hi",
    "Jubin Nautiyal": "hi",
    "Darshan Raval": "hi",
    "B Praak": "hi",

    # --- Korean (ko) ---
    "BTS": "ko",
    "BLACKPINK": "ko",
    "NewJeans": "ko",
    "Stray Kids": "ko",
    "IVE": "ko",
    "TWICE": "ko",
    "TWS": "ko",
    "BESTie": "ko",
    "Girls' Generation": "ko",
    "SEVENTEEN": "ko",
    "ENHYPEN": "ko",
    "TXT": "ko",
    "ATEEZ": "ko",

    # --- Telugu (te) ---
    "Devi Sri Prasad": "te",
    "Thaman S": "te",
    "M.M. Keeravaani": "te",

    # --- Kannada (kn) ---
    "Ravi Basrur": "kn",
    "Arjun Janya": "kn",

    # --- Marathi (mr) ---
    "Ajay Atul": "mr",
    "Seema Mishra": "mr",
    "Reshma Sonawane": "mr",

    # --- English / Global (en) ---
    "Katy Perry": "en",
    "Mariah Carey": "en",
    "The Weeknd": "en",
    "Lana Del Rey": "en",
    "Shaggy": "en",
    "Cody Johnson": "en",
    "Darlene Love": "en",
    "Michael Jackson": "en",
    "Britney Spears": "en",
    "Boney M.": "en",
    "Dean Martin": "en",
    "Eminem": "en",
    "Lady Gaga": "en",
    "Taylor Swift": "en",
    "Drake": "en",
    "Bruno Mars": "en",
    "Ed Sheeran": "en",
    "Justin Bieber": "en",
    "Ariana Grande": "en",
    "Dua Lipa": "en",
    "Billie Eilish": "en",
    "Post Malone": "en",
    "Coldplay": "en",
    "Imagine Dragons": "en",
    "OneRepublic": "en",
    "Maroon 5": "en",
    "Adele": "en",
    "Rihanna": "en",
    "Beyoncé": "en",
    "Sia": "en"
}

def get_artist_language(artist: str) -> str | None:
    """
    Look up exact or primary artist name in the static artist language map.
    Returns standard 2-letter ISO code if near-certain match, else None.
    """
    if not artist:
        return None
    artist_str = str(artist).strip()
    
    # Direct match
    if artist_str in ARTIST_LANGUAGE_MAP:
        return ARTIST_LANGUAGE_MAP[artist_str]
        
    # Check key substring in artist string for multi-artist credits (e.g. "Yo Yo Honey Singh, Neha Kakkar")
    for key, lang in ARTIST_LANGUAGE_MAP.items():
        if key.lower() in artist_str.lower():
            return lang
            
    return None
