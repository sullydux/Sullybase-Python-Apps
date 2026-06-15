#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import math
import re
import json
import hashlib
import string
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import ssl
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

APP_TITLE   = "Password Analyzer"
CACHE_FILE  = None  # disk caching disabled by design; keep password-derived data out of files

MIN_WORD_LEN   = 3
MAX_CANDIDATES = 60
LOOKUP_TIMEOUT = 5
MAX_THREADS    = 12

CLASSICAL_GUESSES_PER_SEC = 1e10
QUANTUM_ORACLE_CALLS_PER_SEC = 1e10  # comparison model, not a hardware forecast
LOG2_GROVER_CONSTANT = math.log2(math.pi / 4.0)

# Cache TTLs in seconds
TTL_DICT_HIT  = 90 * 86400   # 90 days
TTL_DICT_MISS =  7 * 86400   # 7 days
TTL_HIBP      =  1 * 86400   # 1 day

DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
HIBP_RANGE_URL     = "https://api.pwnedpasswords.com/range/{}"

LEET_TABLE = str.maketrans({
    "4": "a", "@": "a", "8": "b", "3": "e",
    "1": "l", "0": "o", "$": "s", "5": "s",
    "7": "t", "+": "t", "!": "i", "9": "g",
})

SESSION_CACHE: dict = {}

def https_context() -> ssl.SSLContext:
    """
    Use certifi when available. This fixes common macOS Python installs where
    urllib cannot find a trusted CA bundle for HaveIBeenPwned.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


# ── Top ~600 common password words (offline, zero network) ──────────────────
COMMON_WORDS: frozenset = frozenset({
    # super-common single words
    "password", "passw", "passwd", "pass", "qwerty", "azerty", "dvorak",
    "login", "admin", "root", "user", "guest", "default", "test", "demo",
    "letmein", "welcome", "access", "master", "dragon", "monkey", "shadow",
    "sunshine", "princess", "batman", "superman", "iloveyou", "trustno",
    "football", "baseball", "soccer", "hockey", "basketball", "tennis",
    "apple", "orange", "banana", "lemon", "cherry", "mango", "melon",
    "love", "hate", "life", "live", "real", "true", "fake", "cool",
    "hello", "world", "earth", "fire", "water", "wind", "storm", "rain",
    "night", "light", "dark", "black", "white", "blue", "green", "red",
    "gold", "silver", "iron", "steel", "stone", "rock", "wood", "sand",
    "king", "queen", "prince", "knight", "wizard", "hunter", "ranger",
    "ninja", "ghost", "spirit", "angel", "devil", "demon", "magic",
    "lucky", "happy", "super", "ultra", "mega", "hyper", "turbo",
    "cyber", "delta", "alpha", "omega", "sigma", "gamma", "beta",
    "tiger", "eagle", "wolf", "bear", "shark", "snake", "falcon",
    "viper", "cobra", "panther", "lion", "jaguar", "cougar", "puma",
    "star", "moon", "sun", "mars", "nova", "comet", "orbit", "solar",
    "tech", "code", "data", "byte", "hack", "nerd", "geek", "matrix",
    "system", "server", "network", "cloud", "linux", "windows", "apple",
    "google", "amazon", "twitter", "github", "office", "excel", "word",
    "secret", "hidden", "private", "secure", "safe", "lock", "open",
    "power", "force", "strength", "speed", "swift", "brave", "bold",
    "smart", "quick", "sharp", "clean", "pure", "clear", "bright",
    "mike", "john", "dave", "alex", "sam", "tom", "chris", "jim",
    "bob", "joe", "max", "dan", "ben", "ryan", "sean", "adam",
    "emma", "anna", "sara", "lisa", "kate", "amy", "mary", "jane",
    "band", "music", "rock", "punk", "jazz", "soul", "bass", "drum",
    "gun", "sword", "blade", "axe", "bow", "lance", "shield", "armor",
    "hero", "villain", "boss", "game", "play", "win", "lose", "score",
    "time", "date", "year", "month", "week", "hour", "minute", "second",
    "home", "house", "door", "room", "floor", "wall", "roof", "yard",
    "car", "truck", "bike", "train", "plane", "ship", "boat", "bus",
    "work", "job", "task", "plan", "goal", "path", "road", "way",
    "dog", "cat", "fish", "bird", "horse", "cow", "pig", "duck",
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "zero", "hundred", "thousand", "million",
    "kill", "dead", "live", "born", "free", "wild", "rage", "fury",
    "ice", "snow", "cold", "hot", "warm", "cool", "dry", "wet",
    "big", "small", "tall", "short", "long", "wide", "thin", "fat",
    "new", "old", "young", "fast", "slow", "hard", "soft", "easy",
    "first", "last", "next", "best", "worst", "good", "bad", "ugly",
    "god", "lord", "king", "man", "boy", "girl", "kid", "baby",
    "team", "crew", "gang", "club", "army", "navy", "corp", "unit",
    "flash", "spark", "blaze", "flame", "ember", "ash", "dust", "smoke",
    "toxic", "venom", "acid", "chaos", "void", "abyss", "doom", "fate",
    "dream", "sleep", "wake", "hope", "fear", "pain", "joy", "rage",
    "angel", "grace", "faith", "soul", "mind", "body", "heart", "blood",
    "ocean", "river", "lake", "mountain", "valley", "forest", "desert",
    "island", "coast", "cliff", "cave", "field", "plain", "hill",
    "war", "peace", "battle", "fight", "clash", "duel", "siege", "raid",
    "ruby", "pearl", "jade", "onyx", "opal", "amber", "topaz", "coral",
    "matrix", "neo", "trinity", "morpheus", "oracle", "agent", "smith",
    "avatar", "gamer", "player", "legend", "myth", "epic", "saga",
    "death", "skull", "bone", "grave", "tomb", "ghost", "zombie", "curse",
    "love", "kiss", "hug", "rose", "heart", "cupid", "venus", "sweet",
    "coffee", "beer", "wine", "vodka", "whiskey", "rum", "gin", "soda",
    "pizza", "burger", "taco", "pasta", "sushi", "bread", "cake", "pie",
    "nike", "adidas", "puma", "reebok", "fendi", "gucci", "prada",
    "nasa", "cia", "fbi", "nsa", "swat", "seal", "delta", "ranger",
    "xmen", "avenger", "stark", "banner", "rogers", "thor", "hulk",
    "sonic", "mario", "luigi", "zelda", "link", "samus", "kirby",
    "pikachu", "eevee", "mewtwo", "charizard", "bulbasaur", "squirtle",
    "harley", "joker", "riddler", "penguin", "scarecrow", "bane",
    "winter", "spring", "summer", "autumn", "fall", "season",
    "monday", "tuesday", "friday", "saturday", "sunday", "weekend",
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december",
    "abc", "xyz", "abcd", "abcde", "abcdef",
    # compound word components & common glued-password words
    "butterfly", "rainbow", "sunlight", "moonlight", "starlight",
    "thunder", "lightning", "dragon", "unicorn", "phoenix", "mermaid",
    "butter", "flower", "sunshine", "moonshine", "firefly", "firebird",
    "bluebird", "blackbird", "blackcat", "whitecat", "hotdog", "coldplay",
    "football", "baseball", "basketball", "superhero", "superstar",
    "forever", "never", "always", "everywhere", "somewhere", "nowhere",
    "happy", "sad", "angry", "funny", "silly", "crazy", "lazy", "sexy",
    "cute", "ugly", "dark", "light", "broken", "golden", "silver",
    "master", "slave", "owner", "hunter", "killer", "fighter", "winner",
    "loser", "hacker", "cracker", "stalker", "runner", "swimmer",
    "batman", "spiderman", "ironman", "superman", "aquaman", "deadpool",
    "monkey", "donkey", "turkey", "chicken", "penguin", "dolphin",
    "sparrow", "hawk", "raven", "crow", "dove", "swan", "duck", "goose",
    "forest", "jungle", "swamp", "tundra", "glacier", "volcano",
    "castle", "palace", "tower", "bridge", "tunnel", "bunker",
    "rocket", "missile", "bullet", "arrow", "dagger", "cannon",
    "vision", "mission", "action", "motion", "emotion", "notion",
    "station", "nation", "ocean", "region", "prison", "person",
    "dragon", "dungeon", "wizard", "warrior", "paladin", "archer",
    "rogue", "mage", "cleric", "druid", "bard", "monk", "assassin",
    "legend", "hero", "villain", "nemesis", "rival", "ally", "ally",
    "magic", "spell", "curse", "charm", "rune", "potion", "scroll",
    "quest", "loot", "boss", "level", "score", "life", "health",
    "mana", "rage", "fury", "chaos", "order", "balance", "harmony",
    "echo", "shadow", "phantom", "specter", "wraith", "banshee",
    "candy", "cookie", "cupcake", "brownie", "muffin", "donut",
    "cheese", "bacon", "steak", "chicken", "salmon", "shrimp",
    "lemon", "lime", "grape", "peach", "plum", "kiwi", "melon",
    "spring", "summer", "winter", "autumn", "morning", "evening",
    "night", "midnight", "dawn", "dusk", "noon", "twilight",
    "north", "south", "east", "west", "center", "middle", "edge",
    "cyber", "pixel", "byte", "virus", "trojan", "worm", "botnet",
    "crypto", "token", "wallet", "blockchain", "mining", "hash",
    "blue", "green", "yellow", "purple", "orange", "pink", "brown",
    "crimson", "scarlet", "azure", "ivory", "ebony", "indigo",
    "brave", "noble", "loyal", "fierce", "swift", "silent", "deadly",
    "holy", "sacred", "divine", "wicked", "evil", "good", "pure",
    "alpha", "beta", "gamma", "delta", "omega", "sigma", "theta",
    "zero", "infinity", "eternal", "immortal", "mortal", "divine",
    # misc common password components
    "correct", "horse", "battery", "staple", "fox", "browser", "chrome",
    "internet", "wireless", "router", "modem", "laptop", "desktop",
    "login", "logout", "signup", "register", "forgot", "reset", "change",
    "hello", "world", "test", "temp", "sample", "example", "demo",
    "secret", "private", "public", "global", "local", "remote", "server",
    "client", "admin", "root", "guest", "user", "owner", "manager",
    "monkey", "dragon", "master", "hunter", "killer", "hacker", "gamer",
    "pretty", "beautiful", "gorgeous", "lovely", "amazing", "awesome", "great",
    "tiger", "eagle", "shark", "wolf", "bear", "snake", "lion", "hawk",
    "michael", "jennifer", "jessica", "ashley", "emily", "sarah", "daniel",
    "computer", "keyboard", "monitor", "printer", "scanner", "camera",
    "mobile", "tablet", "phone", "watch", "smart", "digital", "analog",
})

# Extra offline vocabulary: names, dates, services, pop culture, and account words
# that appear often in weak passwords. These are checked locally only.
COMMON_WORDS = COMMON_WORDS | frozenset({
    "aaron", "abby", "abigail", "andrew", "anthony", "austin", "brian",
    "brittany", "brandon", "carlos", "charles", "christopher", "david",
    "elizabeth", "ethan", "george", "hannah", "isabella", "jacob",
    "james", "jason", "joshua", "justin", "kevin", "lauren", "madison",
    "matthew", "melissa", "michelle", "nicole", "nicholas", "olivia",
    "patrick", "rachel", "rebecca", "robert", "stephen", "steven",
    "taylor", "thomas", "victoria", "william", "yankees", "cowboys",
    "lakers", "celtics", "arsenal", "chelsea", "liverpool", "barcelona",
    "pokemon", "minecraft", "fortnite", "roblox", "netflix", "spotify",
    "discord", "paypal", "venmo", "tiktok", "instagram", "facebook",
    "snapchat", "youtube", "reddit", "twitch", "steam", "xbox",
    "playstation", "nintendo", "iphone", "android", "samsung", "tesla",
    "toyota", "honda", "ford", "chevy", "mustang", "camaro",
    "service", "support", "backup", "security", "account", "profile",
    "portal", "dashboard", "database", "payment", "billing", "invoice",
    "school", "college", "student", "teacher", "family", "mother",
    "father", "sister", "brother", "friend", "forever", "birthday",
    "christmas", "holiday", "vacation", "travel", "beach", "city",
    "country", "freedom", "liberty", "victory", "justice", "honor",
    "future", "planet", "galaxy", "cosmos", "rocket", "signal",
    "random", "unique", "custom", "personal", "favorite", "number",
    "whatever", "nothing", "something", "anything", "qazwsx", "zaqwsx",
    "asdf", "zxcv", "asdfgh", "zxcvbn", "qweasd", "passcode",
    "passphrase", "changeme", "temporary", "company", "employee",
    "welcome", "started", "starter", "summer", "winter", "spring",
    "autumn", "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday",
})

# Exact normalized passwords that should fail immediately. Keep this local only.
COMMON_PASSWORD_BLOCKLIST: frozenset = frozenset({
    "password", "password1", "password12", "password123", "password1234",
    "passw0rd", "p@ssword", "p@ssw0rd", "admin", "admin1", "administrator",
    "root", "toor", "letmein", "letmein1", "welcome", "welcome1",
    "changeme", "default", "qwerty", "qwerty1", "qwerty12", "qwerty123",
    "qwerty12345", "qwertyuiop", "asdfgh", "asdfghjkl", "zxcvbn",
    "zxcvbnm", "qazwsx", "zaq12wsx", "1q2w3e", "1q2w3e4r",
    "1qaz2wsx", "abc123", "abcd1234", "abc12345", "123abc", "1234abcd",
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "000000", "111111", "121212", "123123", "654321", "696969",
    "7777777", "88888888", "987654321", "iloveyou", "iloveyou1",
    "trustno1", "monkey", "dragon", "sunshine", "princess", "football",
    "baseball", "superman", "batman", "master", "login", "guest",
    "test", "test123", "demo", "secret", "secret1", "whatever",
})

KEYBOARD_PATTERNS: tuple[str, ...] = (
    "qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890", "0987654321",
    "qazwsxedc", "zaqwsx", "1qaz2wsx", "1q2w3e4r5t", "poiuytrewq",
)

# ─────────────────────────────────────────────
#  Regex helpers
# ─────────────────────────────────────────────

_RE_LETTERS   = re.compile(r"[a-z]+")
_RE_ONLY_LTRS = re.compile(r"^[a-z]+$")
_RE_DIGITS    = re.compile(r"\d")
_RE_SYMBOL    = re.compile(rf"[{re.escape(string.punctuation)}]")
_RE_BOUNDARY  = re.compile(r"[^a-zA-Z]+")   # split on non-alpha

# ─────────────────────────────────────────────
#  Cache
# ─────────────────────────────────────────────

def load_cache() -> dict:
    """Return the process-local cache. Nothing is read from disk."""
    now = time.time()
    expired: list[str] = []
    for k, v in SESSION_CACHE.items():
        if not isinstance(v, dict) or "ts" not in v:
            continue
        ttl = TTL_HIBP
        if k.startswith("dict:"):
            ttl = TTL_DICT_HIT if v.get("result") else TTL_DICT_MISS
        if now - v["ts"] >= ttl:
            expired.append(k)
    for k in expired:
        SESSION_CACHE.pop(k, None)
    return SESSION_CACHE

def save_cache(cache: dict) -> None:
    """Disk writes are intentionally disabled by the app privacy rule."""
    return None

# ─────────────────────────────────────────────
#  Normalisation
# ─────────────────────────────────────────────

def normalize(text: str) -> str:
    return text.lower().translate(LEET_TABLE)

def letters_only(text: str) -> str:
    return re.sub(r"[^a-z]", "", normalize(text))

# ─────────────────────────────────────────────
#  Entropy
# ─────────────────────────────────────────────

def charset_size(text: str) -> int:
    size = 0
    if any(c.islower() for c in text): size += 26
    if any(c.isupper() for c in text): size += 26
    if any(c.isdigit() for c in text): size += 10
    if any(c in string.punctuation for c in text): size += len(string.punctuation)
    if any(c.isspace() for c in text): size += 1
    return max(size, 1)

def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in counts.values()) * n

def charset_entropy(text: str) -> float:
    if not text:
        return 0.0
    return math.log2(charset_size(text)) * len(text)

def entropy_metrics(text: str) -> dict:
    """
    Keep the two entropy formulas separate:
      - charset bits: brute-force upper estimate from observed character classes
      - Shannon bits: distribution estimate from repeated characters
    The score uses the lower of the two so repeats cannot look stronger than
    they are, but the UI reports both formulas independently.
    """
    charset_bits = charset_entropy(text)
    shannon_bits = shannon_entropy(text)
    effective_bits = max(min(charset_bits, shannon_bits), 0.0)
    return {
        "charset": charset_bits,
        "shannon": shannon_bits,
        "effective": effective_bits,
        "quantum_security": effective_bits / 2.0,
        "charset_size": charset_size(text),
    }

def entropy_estimate(text: str) -> float:
    return entropy_metrics(text)["effective"]

def entropy_label(bits: float, quantum: bool = False) -> str:
    thresholds = [(30, "Very weak"), (50, "Weak"), (80, "Fair"), (110, "Strong")]
    for limit, label in thresholds:
        if bits < limit:
            return label
    return "Very strong"


# ─────────────────────────────────────────────
#  Candidate extraction  (smart, privacy-safe)
# ─────────────────────────────────────────────

def _camel_split(chunk: str) -> list[str]:
    """Split 'dogCatFish' → ['dog', 'Cat', 'Fish'] etc."""
    return re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)", chunk)

# Maximum word length to look up online (keeps API calls bounded)
_MAX_WORD_LEN = 20

def _dp_segment_local(text: str) -> set[str]:
    """
    Dynamic-programming word segmentation using only the local COMMON_WORDS set.
    Returns all words found in any valid segmentation of the text.
    e.g. 'dogcatpizzataco' -> {'dog', 'cat', 'pizza', 'taco'}
    Runs entirely offline — no network.
    """
    n = len(text)
    # dp[i] = list of segmentations covering text[:i]
    dp: list[list[list[str]]] = [[] for _ in range(n + 1)]
    dp[0] = [[]]

    for i in range(n):
        if not dp[i]:
            continue
        for j in range(i + MIN_WORD_LEN, min(i + _MAX_WORD_LEN, n) + 1):
            word = text[i:j]
            if word in COMMON_WORDS:
                for seg in dp[i]:
                    dp[j].append(seg + [word])

    found: set[str] = set()
    for seg in dp[n]:
        found.update(seg)
    return found

def extract_candidates(password: str) -> list[str]:
    """
    Build candidate word substrings from a password WITHOUT ever sending the
    full password anywhere. Three-layer approach:
      1. Split on digit/symbol/space boundaries and camelCase transitions
      2. For each all-alpha chunk, run DP segmentation using local wordlist
         -- this catches glued words like 'dogcatpizzataco' with no boundaries
      3. Bounded sliding window for short chunks (catches online-only words)
    """
    candidates: set[str] = set()

    # Layer 1: boundary splits + camelCase
    alpha_chunks: list[str] = [c for c in _RE_BOUNDARY.split(password) if len(c) >= MIN_WORD_LEN]

    for raw_chunk in alpha_chunks:
        norm_chunk = normalize(raw_chunk)

        # camelCase sub-words
        for part in _camel_split(raw_chunk) + _camel_split(norm_chunk):
            p = normalize(part)
            if len(p) >= MIN_WORD_LEN:
                candidates.add(p)

        if not _RE_ONLY_LTRS.fullmatch(norm_chunk):
            # mixed chunk — strip non-alpha and recurse on letter runs
            letter_runs = _RE_LETTERS.findall(norm_chunk)
            for run in letter_runs:
                if len(run) >= MIN_WORD_LEN:
                    candidates.update(_dp_segment_local(run))
                    # also slide on it if short
                    if len(run) <= 14:
                        for i in range(len(run)):
                            for j in range(i + MIN_WORD_LEN, len(run) + 1):
                                candidates.add(run[i:j])
            continue

        # Layer 2: DP segmentation — catches glued words of any length
        # Run from every start position to catch leading garbage chars
        for start in range(min(len(norm_chunk), 8)):
            sub = norm_chunk[start:]
            if len(sub) >= MIN_WORD_LEN:
                candidates.update(_dp_segment_local(sub))

        # Layer 3: bounded sliding window for shorter chunks
        # Lets online API find words not in our local list
        cap = min(len(norm_chunk), 14)
        for i in range(cap):
            for j in range(i + MIN_WORD_LEN, cap + 1):
                sub = norm_chunk[i:j]
                if _RE_ONLY_LTRS.fullmatch(sub):
                    candidates.add(sub)

    # Filter and rank: letters-only, min length, longest first
    out = [c for c in candidates if _RE_ONLY_LTRS.fullmatch(c) and len(c) >= MIN_WORD_LEN]
    out.sort(key=lambda s: (-len(s), s))
    return out[:MAX_CANDIDATES]

def dedupe_nonoverlap(words: list[str]) -> list[str]:
    words = sorted(set(words), key=lambda w: (-len(w), w))
    picked: list[str] = []
    for w in words:
        if not any(w in p or p in w for p in picked):
            picked.append(w)
    return picked

def compact_password(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize(text))

def whole_password_forms(password: str) -> set[str]:
    norm = normalize(password)
    raw = password.lower()
    return {
        raw,
        norm,
        re.sub(r"[^a-z0-9]", "", raw),
        re.sub(r"[^a-z]", "", raw),
        compact_password(password),
        letters_only(password),
    } - {""}

def _longest_sequence(text: str, alphabet: str) -> str:
    best = ""
    for direction in (alphabet, alphabet[::-1]):
        current = ""
        prev_idx = None
        for ch in text:
            try:
                idx = direction.index(ch)
            except ValueError:
                current = ""
                prev_idx = None
                continue
            if prev_idx is not None and idx == prev_idx + 1:
                current += ch
            else:
                current = ch
            prev_idx = idx
            if len(current) > len(best):
                best = current
    return best

def repeated_units(text: str) -> list[dict]:
    compact = compact_password(text)
    findings: list[dict] = []
    if not compact:
        return findings

    for unit_len in range(1, min(10, len(compact) // 2) + 1):
        i = 0
        while i + unit_len * 2 <= len(compact):
            unit = compact[i:i + unit_len]
            repeats = 1
            pos = i + unit_len
            while compact[pos:pos + unit_len] == unit:
                repeats += 1
                pos += unit_len
            min_repeats = 3 if unit_len == 1 else 2
            if repeats >= min_repeats:
                findings.append({
                    "unit": unit,
                    "repeats": repeats,
                    "length": unit_len * repeats,
                })
                i = pos
            else:
                i += 1

    findings.sort(key=lambda d: (-d["length"], d["unit"]))
    deduped: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for item in findings:
        key = (item["unit"], item["repeats"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:8]

def detect_patterns(password: str) -> tuple[int, list[str], dict]:
    norm = normalize(password)
    compact = compact_password(password)
    reasons: list[str] = []
    details = {
        "repeated_runs": [],
        "repeated_units": repeated_units(password),
        "keyboard": [],
        "alpha_sequence": "",
        "digit_sequence": "",
    }

    for match in re.finditer(r"(.)\1{2,}", norm):
        details["repeated_runs"].append(match.group(0))

    for pattern in KEYBOARD_PATTERNS:
        for chunk in (pattern, pattern[::-1]):
            for length in range(min(len(chunk), len(compact)), 3, -1):
                for start in range(0, len(chunk) - length + 1):
                    seq = chunk[start:start + length]
                    if seq in compact:
                        details["keyboard"].append(seq)
                        break
                if details["keyboard"] and details["keyboard"][-1] in compact:
                    break

    details["keyboard"] = sorted(set(details["keyboard"]), key=lambda s: (-len(s), s))[:8]
    details["alpha_sequence"] = _longest_sequence(compact, string.ascii_lowercase)
    details["digit_sequence"] = _longest_sequence(compact, string.digits)

    score = 0
    if details["repeated_runs"]:
        longest = max(len(r) for r in details["repeated_runs"])
        score = max(score, 35 if longest >= 4 else 25)
        reasons.append(f"Repeated character run detected: {', '.join(details['repeated_runs'][:4])}.")
    if details["repeated_units"]:
        longest = details["repeated_units"][0]
        score = max(score, 70 if longest["length"] >= 8 else 50)
        reasons.append(
            f"Repeated pattern detected: '{longest['unit']}' repeated {longest['repeats']} times."
        )
    if details["keyboard"]:
        score = max(score, 75 if len(details["keyboard"][0]) >= 6 else 55)
        reasons.append(f"Keyboard pattern detected: {', '.join(details['keyboard'][:4])}.")
    if len(details["digit_sequence"]) >= 4:
        score = max(score, 70 if len(details["digit_sequence"]) >= 6 else 45)
        reasons.append(f"Sequential digits detected: {details['digit_sequence']}.")
    if len(details["alpha_sequence"]) >= 4:
        score = max(score, 60 if len(details["alpha_sequence"]) >= 6 else 40)
        reasons.append(f"Sequential letters detected: {details['alpha_sequence']}.")

    return min(score, 100), reasons, details

def detect_blocklist(password: str) -> tuple[int, list[str], dict]:
    forms = whole_password_forms(password)
    norm = normalize(password)
    compact = compact_password(password)
    raw_compact = re.sub(r"[^a-z0-9]", "", password.lower())
    reasons: list[str] = []
    details = {
        "exact": [],
        "contained": [],
        "common_years": [],
        "common_suffixes": [],
    }

    details["exact"] = sorted(forms & COMMON_PASSWORD_BLOCKLIST)
    if details["exact"]:
        reasons.append("Exact local blocklist match: " + ", ".join(details["exact"][:4]) + ".")
        return 100, reasons, details

    for item in COMMON_PASSWORD_BLOCKLIST:
        if len(item) >= 6 and (item in compact or item in raw_compact):
            details["contained"].append(item)
    details["contained"] = sorted(set(details["contained"]), key=lambda s: (-len(s), s))[:8]

    for year in re.findall(r"(?:19|20)\d{2}", raw_compact):
        if 1900 <= int(year) <= 2099:
            details["common_years"].append(year)

    if re.search(r"(?:!|@|#|\$|\*)+$", norm):
        details["common_suffixes"].append("symbol suffix")
    if re.search(r"(?:\d{1,4})$", raw_compact):
        details["common_suffixes"].append("digit suffix")

    score = 0
    if details["contained"]:
        score = max(score, 80)
        reasons.append("Contains local blocklisted password text: " + ", ".join(details["contained"][:4]) + ".")
    if details["common_years"]:
        score = max(score, 35)
        reasons.append("Contains calendar-year text often used in passwords: " + ", ".join(details["common_years"][:4]) + ".")
    if details["common_suffixes"] and (details["contained"] or any(w in compact or w in raw_compact for w in COMMON_WORDS)):
        score = max(score, 45)
        reasons.append("Uses a common word/blocklist core with a predictable suffix.")

    return min(score, 100), reasons, details

# ─────────────────────────────────────────────
#  Local word check (instant, no network)
# ─────────────────────────────────────────────

def local_hits(candidates: list[str]) -> list[str]:
    return [w for w in candidates if w in COMMON_WORDS]

# ─────────────────────────────────────────────
#  Online dictionary  (substrings only, parallel)
# ─────────────────────────────────────────────

def api_word_exists(word: str, cache: dict) -> bool:
    """
    Ask dictionaryapi.dev whether `word` is a real English word.
    `word` is always a short extracted substring — never the full password.
    Result cached with TTL.
    """
    if not _RE_ONLY_LTRS.fullmatch(word):
        return False

    key = f"dict:{word}"
    if key in cache:
        entry = cache[key]
        if isinstance(entry, dict):
            return bool(entry.get("result"))
        return bool(entry)   # legacy

    url = DICTIONARY_API_URL.format(urllib.parse.quote(word))
    req = urllib.request.Request(url, headers={"User-Agent": "PasswordAnalyzerBot/2.0"})
    found = False
    try:
        with urllib.request.urlopen(req, timeout=LOOKUP_TIMEOUT, context=https_context()) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        parsed = json.loads(data)
        found = (
            isinstance(parsed, list)
            and parsed
            and isinstance(parsed[0], dict)
            and "meanings" in parsed[0]
        )
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            return False
    except Exception:
        return False

    cache[key] = {"result": found, "ts": time.time()}
    return found

def parallel_dict_check(candidates: list[str], cache: dict) -> list[str]:
    """Run dictionary API lookups in parallel. Returns list of confirmed words."""
    found: list[str] = []
    with ThreadPoolExecutor(max_workers=min(MAX_THREADS, len(candidates) or 1)) as pool:
        futures = {pool.submit(api_word_exists, w, cache): w for w in candidates}
        for fut in as_completed(futures):
            word = futures[fut]
            try:
                if fut.result():
                    found.append(word)
            except Exception:
                pass
    return found

# ─────────────────────────────────────────────
#  HIBP k-anonymity  (SHA-1 prefix only)
# ─────────────────────────────────────────────

def hibp_breached(password: str, cache: dict) -> int | None:
    """
    Sends only the first 5 hex chars of SHA-1 to HIBP — never the full password.
    Returns breach count, 0 if clean, None on error.
    """
    sha1   = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix = sha1[:5]
    suffix = sha1[5:]

    cache_key = f"hibp:{sha1[:10]}"   # cache by 10-char prefix — safe
    if cache_key in cache:
        entry = cache[cache_key]
        if isinstance(entry, dict) and "ts" in entry:
            if time.time() - entry["ts"] < TTL_HIBP:
                return entry.get("result")
        elif not isinstance(entry, dict):
            return entry  # legacy plain int

    url = HIBP_RANGE_URL.format(prefix)
    req = urllib.request.Request(url, headers={"User-Agent": "PasswordAnalyzerBot/2.0",
                                               "Add-Padding": "true"})
    result = None
    try:
        with urllib.request.urlopen(req, timeout=LOOKUP_TIMEOUT, context=https_context()) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        result = 0
        for line in data.splitlines():
            parts = line.split(":")
            if len(parts) == 2 and parts[0].strip().upper() == suffix:
                try:
                    result = int(parts[1].strip())
                except ValueError:
                    result = 1
                break
    except Exception:
        result = None

    if result is not None:
        cache[cache_key] = {"result": result, "ts": time.time()}
    return result

# ─────────────────────────────────────────────
#  Word detection (combined local + online)
# ─────────────────────────────────────────────

def detect_words(password: str, cache: dict, use_online: bool) -> tuple[int, list[str], list[str], dict]:
    """
    Returns (dict_score, reasons, found_words, details).
    Never sends the full password to any API.
    """
    norm = normalize(password)
    candidates = extract_candidates(password)
    full_forms = whole_password_forms(password)
    reasons: list[str] = []
    found: list[str] = []
    details = {
        "candidate_count": len(candidates),
        "local_words": [],
        "online_words": [],
        "online_candidates": [],
        "privacy_skipped": [],
        "coverage": 0.0,
        "covered_chars": 0,
        "alpha_chars": len(re.sub(r"[^a-z]", "", norm)),
    }

    # ── 1. Local instant check ───────────────────────────────────────────────
    # (a) flat hits from candidates list
    loc = local_hits(candidates)
    found.extend(loc)
    details["local_words"].extend(loc)

    # (b) DP segmentation on every all-alpha chunk — catches glued words
    #     e.g. "dogcatpizzataco" -> {dog, cat, pizza, taco}
    alpha_chunks = [c for c in _RE_BOUNDARY.split(norm) if _RE_ONLY_LTRS.fullmatch(c) and len(c) >= MIN_WORD_LEN]
    for chunk in alpha_chunks:
        for start in range(min(len(chunk), 8)):
            dp_words = _dp_segment_local(chunk[start:])
            found.extend(dp_words)
            details["local_words"].extend(dp_words)

    # Also treat very-short all-alpha passwords as word-like immediately
    if _RE_ONLY_LTRS.fullmatch(norm) and len(norm) <= 5:
        found.append(norm)
        reasons.append(f"Very short alphabetic password — trivially guessable.")

    # ── 2. Online dictionary (parallel, substrings only) ────────────────────
    online_found: list[str] = []
    if use_online and candidates:
        # Only look up candidates NOT already confirmed locally
        to_check = []
        for c in candidates:
            if c in COMMON_WORDS:
                continue
            if c in full_forms:
                details["privacy_skipped"].append(c)
                continue
            to_check.append(c)
        details["online_candidates"] = to_check[:MAX_CANDIDATES]
        online_found = parallel_dict_check(to_check, cache)
        found.extend(online_found)
        details["online_words"].extend(online_found)

    found = dedupe_nonoverlap(found)
    details["local_words"] = dedupe_nonoverlap(details["local_words"])
    details["online_words"] = dedupe_nonoverlap(details["online_words"])
    details["privacy_skipped"] = sorted(set(details["privacy_skipped"]), key=lambda s: (-len(s), s))

    # ── 3. Score ─────────────────────────────────────────────────────────────
    score = 0
    if found:
        # Coverage: what fraction of the password's letters are explained by found words?
        alpha_pw = re.sub(r"[^a-z]", "", norm)
        alpha_len = max(len(alpha_pw), 1)
        covered_chars = sum(len(w) for w in found)
        coverage = min(covered_chars / alpha_len, 1.0)  # 0.0 – 1.0
        details["coverage"] = coverage
        details["covered_chars"] = min(covered_chars, alpha_len)

        # Deterministic score from coverage bands. This makes the same structure
        # land in the same bucket instead of accumulating fuzzy bonuses.
        if coverage >= 0.95:
            score = 90
        elif coverage >= 0.80:
            score = 80
        elif coverage >= 0.60:
            score = 65
        elif coverage >= 0.35:
            score = 45
        else:
            score = min(15 * len(found), 40)

        src = "local + online" if (use_online and online_found) else ("online" if online_found else "local wordlist")
        reasons.append(f"Dictionary words detected ({src}): " + ", ".join(found[:10]))
        if coverage >= 0.9:
            reasons.append(f"Password is almost entirely made of dictionary words ({int(coverage*100)}% coverage) — very guessable.")
        elif coverage >= 0.5:
            reasons.append(f"Over half the password consists of dictionary words ({int(coverage*100)}% coverage).")
    else:
        score = 0

    if details["privacy_skipped"]:
        reasons.append(
            "Privacy guard skipped online lookup for whole-password candidate(s): "
            + ", ".join(details["privacy_skipped"][:4])
            + "."
        )

    return min(score, 100), reasons, found, details

# ─────────────────────────────────────────────
#  Strength + timing
# ─────────────────────────────────────────────

def dict_label(score: float) -> str:
    if score < 20: return "Low"
    if score < 40: return "Moderate"
    if score < 70: return "High"
    return "Very high"

def risk_label(score: int) -> str:
    if score < 20: return "Low"
    if score < 45: return "Moderate"
    if score < 75: return "High"
    return "Critical"

def strength_label(entropy: float, risk_score: int, password: str, quantum: bool = False) -> str:
    """
    Strength is derived from effective entropy and explicit risk components
    (blocklist, dictionary coverage, repeated patterns, and breach status).
    """
    if quantum:
        quantum_bits = entropy / 2.0
        if risk_score >= 75 or quantum_bits < 40:   return "Weak"
        if risk_score >= 45 or quantum_bits < 80:   return "Moderate"
        if risk_score >= 20 or quantum_bits < 128:  return "Strong"
        return "Quantum-tough"
    else:
        if risk_score >= 75 or entropy < 35:  return "Weak"
        if risk_score >= 45 or entropy < 60:  return "Moderate"
        if risk_score >= 20 or entropy < 90:  return "Strong"
        return "Excellent"

def format_time(seconds: float) -> str:
    if seconds < 1:       return "< 1 second"
    if seconds < 60:      return f"{int(round(seconds))} seconds"
    m = seconds / 60
    if m < 60:            return f"{m:.1f} minutes"
    h = m / 60
    if h < 24:            return f"{h:.1f} hours"
    d = h / 24
    if d < 365:           return f"{d:.1f} days"
    y = d / 365
    if y < 1_000_000:     return f"{y:,.1f} years"
    return "> 1 million years"

def risk_search_penalty_bits(risk_score: int) -> float:
    """
    Convert explicit weaknesses into a deterministic search-space reduction.
    This keeps crack-time estimates aligned with the risk score without
    pretending weak patterns have the full raw character-search space.
    """
    if risk_score >= 75:
        return math.log2(100_000.0)
    if risk_score >= 45:
        return math.log2(1_000.0)
    return 0.0

def format_time_from_log2_ops(log2_ops: float, ops_per_second: float) -> str:
    log2_seconds = log2_ops - math.log2(ops_per_second)
    if log2_seconds < 0:
        return "< 1 second"
    million_years = 1_000_000 * 365 * 24 * 60 * 60
    if log2_seconds > math.log2(million_years):
        return "> 1 million years"
    return format_time(2 ** log2_seconds)

def work_factor_text(log2_ops: float) -> str:
    if log2_ops < 40:
        return f"{2 ** log2_ops:,.0f}"
    return f"2^{log2_ops:.1f}"

def attack_work_factors(entropy: float, risk_score: int) -> dict:
    penalty = risk_search_penalty_bits(risk_score)
    effective_space_bits = max(entropy - penalty, 0.0)
    classical_log2 = max(effective_space_bits - 1.0, 0.0)
    quantum_log2 = max((effective_space_bits / 2.0) + LOG2_GROVER_CONSTANT, 0.0)
    return {
        "risk_penalty_bits": penalty,
        "effective_space_bits": effective_space_bits,
        "classical_log2_guesses": classical_log2,
        "classical_guesses": work_factor_text(classical_log2),
        "classical_time": format_time_from_log2_ops(classical_log2, CLASSICAL_GUESSES_PER_SEC),
        "quantum_security_bits": effective_space_bits / 2.0,
        "quantum_log2_oracles": quantum_log2,
        "quantum_oracles": work_factor_text(quantum_log2),
        "quantum_time": format_time_from_log2_ops(quantum_log2, QUANTUM_ORACLE_CALLS_PER_SEC),
        "quantum_model": "Ideal Grover lower-bound at the same oracle-call rate; not a current hardware forecast.",
    }

def crack_time_text(entropy: float, risk_score: int, quantum: bool) -> str:
    factors = attack_work_factors(entropy, risk_score)
    classical = factors["classical_time"]
    if quantum:
        return f"Classical: {classical}   |   Quantum ideal Grover: {factors['quantum_time']}"
    return classical

def suggestion(password: str, entropy: float, risk_score: int, quantum: bool,
               breached: int | None, breach_status: str) -> str:
    if breached:
        return f"⚠ This password has appeared in data breaches {breached:,} times — never use it."
    if breach_status == "error":
        return "Breach check could not complete; retry when online before trusting this password."
    if quantum:
        return "Quantum mode: target about 128 quantum security bits for long-term protection; that means roughly 256 effective classical entropy bits before other weaknesses."
    if risk_score >= 75:
        return "Replace it completely; the password matches known weak structures."
    if risk_score >= 45:
        return "Avoid blocklisted words, sequences, repeats, and predictable suffixes."
    if entropy < 50:
        return "Make it longer and mix uppercase, lowercase, digits, and symbols."
    if len(password) < 14:
        return "Good start — push to 16+ characters for stronger protection."
    return "Looking strong! Use a password manager so you never reuse it."

# ─────────────────────────────────────────────
#  Main analysis
# ─────────────────────────────────────────────

def analyze(password: str,
            use_online_dict: bool = True,
            quantum: bool = False,
            check_hibp: bool = True) -> dict:

    if not password:
        return {
            "entropy": 0.0,
            "entropy_bits": {"charset": 0.0, "shannon": 0.0, "effective": 0.0, "quantum_security": 0.0, "charset_size": 1},
            "entropy_label": "Empty",
            "quantum_entropy_label": "Empty",
            "dict_score": 0, "dict_label": "None",
            "pattern_score": 0, "blocklist_score": 0, "risk_score": 0, "risk_label": "None",
            "strength": "Empty", "strength_color": "#64748b",
            "reasons": ["Enter a password to begin."],
            "time": "Unknown", "breached": None, "breach_status": "not_checked",
            "found_words": [], "attack_factors": {}, "quantum": quantum, "details": {},
        }

    cache = load_cache()
    entropy_bits = entropy_metrics(password)
    entropy = entropy_bits["effective"]

    # Dictionary / word detection
    dict_score, reasons, found_words, word_details = detect_words(password, cache, use_online_dict)

    # Local blocklist and repeated-pattern checks
    blocklist_score, blocklist_reasons, blocklist_details = detect_blocklist(password)
    pattern_score, pattern_reasons, pattern_details = detect_patterns(password)
    reasons.extend(blocklist_reasons)
    reasons.extend(pattern_reasons)


    # HIBP
    breach_status = "not_checked"
    breached: int | None = None
    breach_score = 0
    if check_hibp:
        breached = hibp_breached(password, cache)
    if not check_hibp:
        reasons.append("Breach check: not run.")
    elif breached is None:
        breach_status = "error"
        reasons.append("Breach check: offline or error — could not reach HaveIBeenPwned.")
    elif breached == 0:
        breach_status = "clean"
        reasons.append("Breach check: ✓ not found in HaveIBeenPwned (k-anonymity).")
    else:
        breach_status = "found"
        breach_score = 100
        reasons.append(f"Breach check: ✗ found in HaveIBeenPwned {breached:,} times (k-anonymity).")

    save_cache(cache)

    risk_score = max(dict_score, blocklist_score, pattern_score, breach_score)
    attack_factors = attack_work_factors(entropy, risk_score)
    strength = strength_label(entropy, risk_score, password, quantum)
    color_map = {
        "Weak": "#ef4444", "Moderate": "#f97316",
        "Strong": "#22c55e", "Excellent": "#06b6d4", "Quantum-tough": "#a78bfa",
    }
    strength_color = color_map.get(strength, "#94a3b8")

    reasons.append(suggestion(password, entropy, risk_score, quantum, breached, breach_status))

    return {
        "entropy": entropy,
        "quantum": quantum,
        "entropy_bits": entropy_bits,
        "entropy_label": entropy_label(entropy),
        "quantum_entropy_label": entropy_label(attack_factors["quantum_security_bits"]),
        "dict_score": dict_score,
        "dict_label": dict_label(dict_score),
        "pattern_score": pattern_score,
        "blocklist_score": blocklist_score,
        "risk_score": risk_score,
        "risk_label": risk_label(risk_score),
        "strength": strength,
        "strength_color": strength_color,
        "reasons": reasons,
        "time": crack_time_text(entropy, risk_score, quantum),
        "attack_factors": attack_factors,
        "breached": breached,
        "breach_status": breach_status,
        "found_words": found_words,
        "details": {
            "words": word_details,
            "blocklist": blocklist_details,
            "patterns": pattern_details,
            "privacy": {
                "disk_cache": "disabled",
                "full_password_online": "blocked",
                "hibp": "SHA-1 prefix only",
            },
        },
    }

# ─────────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────────

COLORS = {
    "bg":        "#080d18",
    "surface":   "#0f1929",
    "surface2":  "#162033",
    "border":    "#1e2d47",
    "text":      "#e2e8f0",
    "muted":     "#64748b",
    "accent":    "#38bdf8",
    "accent2":   "#818cf8",
    "weak":      "#ef4444",
    "moderate":  "#f97316",
    "strong":    "#22c55e",
    "excellent": "#06b6d4",
}

class MeterCanvas(tk.Canvas):
    """Animated horizontal strength meter."""
    def __init__(self, parent, **kw):
        kw.setdefault("bg", COLORS["surface2"])
        super().__init__(parent, height=8, highlightthickness=0, bd=0, **kw)
        self._current = 0.0
        self._target  = 0.0
        self._color   = COLORS["muted"]
        self._anim_id = None

    def set_value(self, fraction: float, color: str):
        self._target = max(0.0, min(1.0, fraction))
        self._color  = color
        self._animate()

    def _animate(self):
        if self._anim_id:
            self.after_cancel(self._anim_id)
        diff = self._target - self._current
        if abs(diff) < 0.005:
            self._current = self._target
            self._draw()
            return
        self._current += diff * 0.18
        self._draw()
        self._anim_id = self.after(16, self._animate)

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 300
        h = self.winfo_height() or 8
        # track
        self.create_rectangle(0, 0, w, h, fill=COLORS["border"], outline="")
        # fill
        if self._current > 0:
            fw = int(w * self._current)
            self.create_rectangle(0, 0, fw, h, fill=self._color, outline="")


STRENGTH_ORDER = {"Weak": 1, "Moderate": 2, "Strong": 3, "Excellent": 4, "Quantum-tough": 4}

class InfoCard(tk.Frame):
    def __init__(self, parent, title: str, subtitle: str = "", **kw):
        super().__init__(parent, bg=COLORS["surface2"],
                         highlightbackground=COLORS["border"],
                         highlightthickness=1, **kw)
        tk.Label(self, text=title, bg=COLORS["surface2"],
                 fg=COLORS["muted"], font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", padx=12, pady=(10, 0))
        self.value_lbl = tk.Label(self, text="—", bg=COLORS["surface2"],
                                  fg=COLORS["accent"], font=("Segoe UI", 17, "bold"),
                                  anchor="w")
        self.value_lbl.pack(fill="x", padx=12)
        if subtitle:
            tk.Label(self, text=subtitle, bg=COLORS["surface2"],
                     fg=COLORS["muted"], font=("Segoe UI", 8),
                     anchor="w").pack(fill="x", padx=12, pady=(0, 8))
        else:
            tk.Label(self, text="", bg=COLORS["surface2"]).pack(pady=(0, 6))

    def set(self, value: str, color: str = COLORS["accent"]):
        self.value_lbl.config(text=value, fg=color)


class PasswordAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x780")
        self.minsize(860, 680)
        self.configure(bg=COLORS["bg"])

        self._pw_var          = tk.StringVar()
        self._show_pw         = tk.BooleanVar(value=False)
        self._use_online_dict = tk.BooleanVar(value=True)
        self._quantum         = tk.BooleanVar(value=False)
        self._check_hibp      = tk.BooleanVar(value=True)
        self._realtime        = tk.BooleanVar(value=True)

        self._debounce_id: str | None = None
        self._analyzing   = False
        self._last_result : dict | None = None

        self._build_ui()
        self._pw_var.trace_add("write", self._on_pw_change)

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=COLORS["bg"], pady=20, padx=28)
        header.pack(fill="x")

        tk.Label(header, text="Password Analyzer", bg=COLORS["bg"],
                 fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(header,
                 text="Real-time strength · Online dictionary (substrings only) · "
                       "HIBP k-anonymity · No full password online or saved.",
                 bg=COLORS["bg"], fg=COLORS["muted"],
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        # ── Input card ────────────────────────────────────────────────────────
        inp = tk.Frame(self, bg=COLORS["surface2"],
                       highlightbackground=COLORS["border"],
                       highlightthickness=1)
        inp.pack(fill="x", padx=24, pady=(0, 14))

        tk.Label(inp, text="Password", bg=COLORS["surface2"],
                 fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(10, 0))

        self._entry = tk.Entry(inp, textvariable=self._pw_var, show="•",
                               font=("Segoe UI", 14), bg=COLORS["surface"],
                               fg=COLORS["text"], insertbackground=COLORS["accent"],
                               relief="flat", bd=0)
        self._entry.pack(fill="x", padx=14, ipady=8, pady=(4, 4))
        self._entry.focus_set()

        self._meter = MeterCanvas(inp, bg=COLORS["surface2"])
        self._meter.pack(fill="x", padx=0, pady=(0, 2))

        # ── Toggles row ───────────────────────────────────────────────────────
        tog = tk.Frame(inp, bg=COLORS["surface2"])
        tog.pack(fill="x", padx=14, pady=(6, 8))

        def cb(parent, text, var, cmd=None):
            return tk.Checkbutton(parent, text=text, variable=var,
                                  command=cmd,
                                  bg=COLORS["surface2"], fg=COLORS["muted"],
                                  selectcolor=COLORS["surface"],
                                  activebackground=COLORS["surface2"],
                                  activeforeground=COLORS["text"],
                                  font=("Segoe UI", 9), bd=0,
                                  highlightthickness=0)

        cb(tog, "Show password", self._show_pw, self._toggle_show).pack(side="left", padx=(0,12))
        cb(tog, "Online dictionary", self._use_online_dict).pack(side="left", padx=12)
        cb(tog, "Quantum mode",      self._quantum).pack(side="left", padx=12)
        cb(tog, "Check HIBP",        self._check_hibp).pack(side="left", padx=12)
        cb(tog, "Real-time",         self._realtime).pack(side="left", padx=12)

        self._analyze_btn = tk.Button(
            tog, text="Analyze", command=self._run_threaded,
            bg=COLORS["accent"], fg="#0f1929",
            font=("Segoe UI", 9, "bold"), relief="flat",
            activebackground=COLORS["accent2"], activeforeground=COLORS["bg"],
            padx=16, pady=4, cursor="hand2",
        )
        self._analyze_btn.pack(side="right")

        self._export_btn = tk.Button(
            tog, text="Copy report", command=self._copy_report,
            bg=COLORS["surface"], fg=COLORS["muted"],
            font=("Segoe UI", 9), relief="flat",
            padx=12, pady=4, cursor="hand2",
        )
        self._export_btn.pack(side="right", padx=(0, 8))

        # ── Metric cards ──────────────────────────────────────────────────────
        cards_row = tk.Frame(self, bg=COLORS["bg"])
        cards_row.pack(fill="x", padx=24, pady=(0, 14))

        self._card_entropy  = InfoCard(cards_row, "Effective entropy", "Lower of two formulas")
        self._card_elabel   = InfoCard(cards_row, "Entropy rating",    "Standard / Quantum")
        self._card_dict     = InfoCard(cards_row, "Risk score",        "Max local/HIBP risk 0–100")
        self._card_strength = InfoCard(cards_row, "Overall strength",  "Combined verdict")

        for c in (self._card_entropy, self._card_elabel,
                  self._card_dict, self._card_strength):
            c.pack(side="left", expand=True, fill="both", padx=(0, 10))
            c.pack_configure(padx=(0 if c is self._card_strength else 0, 8))

        cards_row.columnconfigure((0,1,2,3), weight=1)

        # ── Details pane ──────────────────────────────────────────────────────
        detail = tk.Frame(self, bg=COLORS["surface2"],
                          highlightbackground=COLORS["border"],
                          highlightthickness=1)
        detail.pack(fill="both", expand=True, padx=24, pady=(0, 14))

        hdr = tk.Frame(detail, bg=COLORS["surface2"])
        hdr.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(hdr, text="Analysis details", bg=COLORS["surface2"],
                 fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
        self._status_lbl = tk.Label(hdr, text="", bg=COLORS["surface2"],
                                    fg=COLORS["muted"], font=("Segoe UI", 9))
        self._status_lbl.pack(side="right")

        self._output = tk.Text(
            detail, bg=COLORS["surface2"], fg=COLORS["text"],
            font=("Consolas", 10), relief="flat", bd=0,
            wrap="word", padx=14, pady=8,
            insertbackground=COLORS["accent"],
            selectbackground=COLORS["border"],
        )
        self._output.pack(fill="both", expand=True)

        # Configure text tags for coloring
        self._output.tag_config("header",  foreground=COLORS["accent"],  font=("Consolas", 10, "bold"))
        self._output.tag_config("good",    foreground=COLORS["strong"])
        self._output.tag_config("bad",     foreground=COLORS["weak"])
        self._output.tag_config("warning", foreground=COLORS["moderate"])
        self._output.tag_config("muted",   foreground=COLORS["muted"])
        self._output.tag_config("word",    foreground=COLORS["accent2"])

        self._output.configure(state="disabled")
        self._set_output_text("Enter a password above and click Analyze, or enable Real-time mode.", "muted")

        # ── Footer ────────────────────────────────────────────────────────────
        foot = tk.Frame(self, bg=COLORS["bg"])
        foot.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(foot,
                 text="🔒  Dictionary API receives only extracted substrings · "
                       "HIBP receives only the first 5 hex chars of SHA-1 · "
                       "No disk cache; full password never transmitted or saved.",
                 bg=COLORS["bg"], fg=COLORS["muted"],
                 font=("Segoe UI", 8)).pack(anchor="w")

        self.bind("<Return>", lambda e: self._run_threaded())

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _toggle_show(self):
        self._entry.configure(show="" if self._show_pw.get() else "•")

    def _set_status(self, msg: str):
        self._status_lbl.config(text=msg)

    def _set_output_text(self, text: str, tag: str = ""):
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        self._output.insert("end", text, tag)
        self._output.configure(state="disabled")

    def _on_pw_change(self, *_):
        if not self._realtime.get():
            return
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        # Fast local-only preview after short delay
        self._debounce_id = self.after(350, self._run_realtime)

    def _run_realtime(self):
        """Lightweight analysis: local only (no network) for instant feedback."""
        pw = self._pw_var.get()
        if not pw:
            self._meter.set_value(0, COLORS["muted"])
            self._update_cards(None)
            return
        # Quick offline analysis
        threading.Thread(
            target=self._worker,
            args=(pw, False, self._quantum.get(), False, True),
            daemon=True,
        ).start()

    def _run_threaded(self):
        if self._analyzing:
            return
        pw = self._pw_var.get()
        if not pw:
            messagebox.showinfo(APP_TITLE, "Please enter a password.")
            return
        self._analyzing = True
        self._analyze_btn.config(state="disabled")
        self._set_status("Analyzing…")
        threading.Thread(
            target=self._worker,
            args=(pw, self._use_online_dict.get(),
                  self._quantum.get(), self._check_hibp.get(), False),
            daemon=True,
        ).start()

    def _worker(self, password, use_online, quantum, hibp, realtime):
        result = analyze(password, use_online_dict=use_online,
                         quantum=quantum, check_hibp=hibp)
        self.after(0, lambda: self._on_result(result, realtime))

    def _on_result(self, result: dict, realtime: bool):
        self._last_result = result
        self._analyzing   = False
        self._analyze_btn.config(state="normal")

        if not realtime:
            self._set_status("Done.")

        # Meter
        lvl   = STRENGTH_ORDER.get(result["strength"], 0)
        frac  = lvl / 4.0
        self._meter.set_value(frac, result["strength_color"])

        self._update_cards(result)

        if not realtime:
            self._render_detail(result)

    def _update_cards(self, r: dict | None):
        if r is None:
            for c in (self._card_entropy, self._card_elabel,
                      self._card_dict, self._card_strength):
                c.set("—", COLORS["muted"])
            return
        if r.get("quantum"):
            self._card_entropy.set(f'{r["attack_factors"]["quantum_security_bits"]:.1f} q-bits', COLORS["accent"])
            self._card_elabel.set(r["quantum_entropy_label"], COLORS["accent2"])
        else:
            self._card_entropy.set(f'{r["entropy"]:.1f} bits', COLORS["accent"])
            self._card_elabel.set(r["entropy_label"], COLORS["accent2"])
        risk_color = COLORS["weak"] if r["risk_score"] >= 75 else (
            COLORS["moderate"] if r["risk_score"] >= 45 else COLORS["accent"]
        )
        self._card_dict.set(f'{r["risk_score"]}/100', risk_color)
        self._card_strength.set(r["strength"], r["strength_color"])

    def _render_detail(self, r: dict):
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")

        def ln(text="", tag=""):
            self._output.insert("end", text + "\n", tag)

        entropy_bits = r["entropy_bits"]
        attack_factors = r.get("attack_factors", {})
        details = r.get("details", {})
        word_details = details.get("words", {})
        block_details = details.get("blocklist", {})
        pattern_details = details.get("patterns", {})

        ln(f"  Effective entropy:  {r['entropy']:.2f} bits  ({r['entropy_label']})", "header")
        ln(f"  Charset formula:    {entropy_bits['charset']:.2f} bits  log2(charset={entropy_bits['charset_size']}) × length")
        ln(f"  Shannon formula:    {entropy_bits['shannon']:.2f} bits  character-frequency estimate")
        ln("  Score rule:         effective entropy = lower of charset and Shannon formulas")
        if attack_factors:
            ln(f"  Quantum security:   {attack_factors['quantum_security_bits']:.2f} bits  ideal Grover halves the effective search space exponent")
            ln(f"  Classical work:     {attack_factors['classical_guesses']} average guesses")
            ln(f"  Grover work:        {attack_factors['quantum_oracles']} ideal oracle calls")
            if attack_factors["risk_penalty_bits"] > 0:
                ln(f"  Risk adjustment:    -{attack_factors['risk_penalty_bits']:.2f} bits from blocklist/pattern prioritization")
        ln(f"  Crack time:         {r['time']}")
        ln()
        ln("  Deterministic risk components:", "header")
        ln(f"    Dictionary words: {r['dict_score']}/100  ({r['dict_label']})")
        ln(f"    Local blocklist:  {r['blocklist_score']}/100")
        ln(f"    Repeated patterns:{r['pattern_score']}/100")
        ln(f"    Overall risk:     {r['risk_score']}/100  ({r['risk_label']})")

        breach = r["breached"]
        if r.get("breach_status") == "not_checked":
            ln("  Breach status:      Not checked", "muted")
        elif breach is None:
            ln("  Breach status:      [offline / error]", "muted")
        elif breach == 0:
            ln("  Breach status:      ✓ Not found in HaveIBeenPwned", "good")
        else:
            ln(f"  Breach status:      ✗ Found {breach:,} times in HaveIBeenPwned", "bad")

        ln()
        ln("  Privacy checks:", "header")
        ln("    Full password sent online: no")
        ln("    Full password saved after run: no")
        ln("    Disk cache: disabled")
        ln("    HIBP request: SHA-1 prefix only")
        if attack_factors:
            ln("    Quantum model: " + attack_factors["quantum_model"])
        if word_details.get("privacy_skipped"):
            ln("    Online dictionary skipped whole-password candidate(s): " +
               ", ".join(word_details["privacy_skipped"][:8]), "good")

        if r["found_words"]:
            ln()
            ln("  Words detected:", "header")
            ln("    " + "  ·  ".join(r["found_words"][:12]), "word")
            if word_details:
                ln(f"    Candidate substrings considered: {word_details.get('candidate_count', 0)}")
                ln(f"    Letter coverage by detected words: {word_details.get('covered_chars', 0)}/"
                   f"{max(word_details.get('alpha_chars', 0), 1)} "
                   f"({word_details.get('coverage', 0.0) * 100:.0f}%)")
                if word_details.get("local_words"):
                    ln("    Local wordlist hits: " + ", ".join(word_details["local_words"][:12]))
                if word_details.get("online_words"):
                    ln("    Online dictionary hits: " + ", ".join(word_details["online_words"][:12]))

        if block_details and any(block_details.values()):
            ln()
            ln("  Blocklist details:", "header")
            if block_details.get("exact"):
                ln("    Exact local blocklist match: " + ", ".join(block_details["exact"]), "bad")
            if block_details.get("contained"):
                ln("    Contains blocklisted text: " + ", ".join(block_details["contained"][:8]), "bad")
            if block_details.get("common_years"):
                ln("    Year-like tokens: " + ", ".join(block_details["common_years"][:8]), "warning")
            if block_details.get("common_suffixes"):
                ln("    Predictable suffixes: " + ", ".join(block_details["common_suffixes"]), "warning")

        if pattern_details and any(pattern_details.values()):
            ln()
            ln("  Pattern details:", "header")
            if pattern_details.get("repeated_runs"):
                ln("    Repeated character runs: " + ", ".join(pattern_details["repeated_runs"][:8]), "warning")
            if pattern_details.get("repeated_units"):
                formatted = [
                    f"{p['unit']} x{p['repeats']}" for p in pattern_details["repeated_units"][:8]
                ]
                ln("    Repeated units: " + ", ".join(formatted), "warning")
            if pattern_details.get("keyboard"):
                ln("    Keyboard sequences: " + ", ".join(pattern_details["keyboard"][:8]), "warning")
            if pattern_details.get("alpha_sequence"):
                ln("    Letter sequence: " + pattern_details["alpha_sequence"], "warning")
            if pattern_details.get("digit_sequence"):
                ln("    Digit sequence: " + pattern_details["digit_sequence"], "warning")

        ln()
        ln("  Notes:", "header")
        for note in r["reasons"]:
            if note.startswith("⚠") or "✗" in note or "Avoid" in note or "breach" in note.lower():
                tag = "bad"
            elif "✓" in note or "Good" in note or "Excellent" in note or "strong" in note.lower():
                tag = "good"
            elif "Breach check:" in note and "not found" in note.lower():
                tag = "good"
            elif "Suggestion" in note or "Looking" in note or "Use a" in note:
                tag = "warning"
            else:
                tag = ""
            ln(f"    • {note}", tag)

        self._output.configure(state="disabled")

    def _copy_report(self):
        if not self._last_result:
            messagebox.showinfo(APP_TITLE, "Run an analysis first.")
            return
        r = self._last_result
        entropy_bits = r["entropy_bits"]
        attack_factors = r.get("attack_factors", {})
        lines = [
            "=== Password Analyzer Report ===",
            f"Effective entropy: {r['entropy']:.2f} bits ({r['entropy_label']})",
            f"Charset formula:   {entropy_bits['charset']:.2f} bits",
            f"Shannon formula:   {entropy_bits['shannon']:.2f} bits",
            f"Quantum security:  {attack_factors.get('quantum_security_bits', 0.0):.2f} bits ({r.get('quantum_entropy_label', 'Unknown')})",
            f"Classical work:    {attack_factors.get('classical_guesses', 'Unknown')} average guesses",
            f"Grover work:       {attack_factors.get('quantum_oracles', 'Unknown')} ideal oracle calls",
            f"Dictionary risk:   {r['dict_score']}/100 ({r['dict_label']})",
            f"Blocklist risk:    {r['blocklist_score']}/100",
            f"Pattern risk:      {r['pattern_score']}/100",
            f"Overall risk:      {r['risk_score']}/100 ({r['risk_label']})",
            f"Strength:          {r['strength']}",
            f"Crack time:        {r['time']}",
        ]
        breach = r["breached"]
        if r.get("breach_status") == "not_checked":
            lines.append("Breach status:     Not checked")
        elif breach is None:
            lines.append("Breach status:    Unknown (offline)")
        elif breach == 0:
            lines.append("Breach status:    Not found in HaveIBeenPwned")
        else:
            lines.append(f"Breach status:    Found {breach:,} times in HaveIBeenPwned")
        if r["found_words"]:
            lines.append("Words detected:   " + ", ".join(r["found_words"]))
        lines.append("")
        lines.append("Notes:")
        for n in r["reasons"]:
            lines.append(f"  • {n}")
        lines.append("")
        if attack_factors:
            lines.append("Quantum model: " + attack_factors["quantum_model"])
        lines.append("(Full password never transmitted or saved. Disk cache disabled. Checks: local blocklists, dictionary substrings, and SHA-1 prefix k-anonymity.)")

        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        self._set_status("Report copied to clipboard.")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    try:
        app = PasswordAnalyzerApp()
        app.mainloop()
    except Exception as exc:
        try:
            messagebox.showerror(APP_TITLE, str(exc))
        except Exception:
            print(f"Fatal error: {exc}")
