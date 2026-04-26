import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from tqdm import tqdm
from pathlib import Path
import unicodedata
import re

#--------------------------- Data cleaning --------------------------------

_KEEP_MARKS: frozenset[str] = frozenset({
    "\u0313",  # smooth breathing (psili)
    "\u0314",  # rough breathing (dasia)
    "\u0301",  # acute accent
    "\u0300",  # grave accent
    "\u0342",  # circumflex (perispomeni)
    "\u0308",  # diaeresis
    "\u0345",  # iota subscript (ypogegrammeni)
})

_COMBINING_TO_BETA: dict[str, str] = {
    "\u0313": ")",
    "\u0314": "(",
    "\u0301": "/",
    "\u0300": "\\",
    "\u0342": "=",
    "\u0308": "+",
    "\u0345": "|",
}
_GREEK_BASE_TO_BETA: dict[str, str] = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e",
    "ζ": "z", "η": "h", "θ": "q", "ι": "i", "κ": "k",
    "λ": "l", "μ": "m", "ν": "n", "ξ": "c", "ο": "o",
    "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t",
    "υ": "u", "φ": "f", "χ": "x", "ψ": "y", "ω": "w",
}
_DIACRITIC_ORDER: list[str] = [
    "\u0313", "\u0314", "\u0301", "\u0300", "\u0342", "\u0308", "\u0345",
]

_BC_DIACRITICS_RE = re.compile(r"[)(\\\/=+|*]")

def clean_text(text: str | None) -> str | None:
    """
    Keep only characters in the main Greek Unicode blocks
    (U+0370–U+03FF and U+1F00–U+1FFF) plus whitespace.
    """
    if not text:
        return text
    return re.sub(r"[^\u0370-\u03FF\u1F00-\u1FFF\s]", "", str(text)).strip()


def strip_diacritics(text: str) -> str:
    """Remove ALL combining diacritics (category Mn), return plain base letters."""
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC",
        "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn"),
    )

def normalize_greek(text: str | None) -> str | None:
    """
    Normalize Greek Unicode text:
      - Decomposes to NFD.
      - Strips breve (U+0306) and macron (U+0304).
      - Keeps breathing marks, accents, diaeresis, and iota subscript.
      - Recomposes to NFC.
    """
    if not text:
        return text
    text = str(text)
    decomposed = unicodedata.normalize("NFD", text)
    filtered = [
        ch for ch in decomposed
        if unicodedata.combining(ch) == 0 or ch in _KEEP_MARKS
    ]
    return unicodedata.normalize("NFC", "".join(filtered))

def greek_unicode_to_betacode(text: str) -> str:
    """Convert a Greek Unicode string to TLG-style Beta Code."""
    nfd = unicodedata.normalize("NFD", text)
    result: list[str] = []
    i = 0
    while i < len(nfd):
        ch = nfd[i]
        j = i + 1
        combining: list[str] = []
        while j < len(nfd) and unicodedata.category(nfd[j]).startswith("M"):
            combining.append(nfd[j])
            j += 1
        lower_ch = ch.lower()
        if lower_ch in _GREEK_BASE_TO_BETA:
            beta_base = _GREEK_BASE_TO_BETA[lower_ch]
            is_upper = unicodedata.category(ch) == "Lu"
            diacritics = "".join(
                _COMBINING_TO_BETA[c]
                for c in _DIACRITIC_ORDER
                if c in combining
            )
            if is_upper:
                result.append("*" + diacritics + beta_base.upper())
            else:
                result.append(beta_base + diacritics)
        elif ch == "·":
            result.append(":")
        elif ch == ";":
            result.append("?")
        elif not unicodedata.category(ch).startswith("M"):
            result.append(ch)
        i = j
    return "".join(result)

#--------------------------- Data extraction --------------------------------

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "GreekSuffixExtractor/1.0 (research tool; contact: you@example.com)"
})

KNOWN_POS = {
    "Noun", "Verb", "Adjective", "Adverb", "Participle",
    "Pronoun", "Preposition", "Conjunction", "Interjection",
    "Numeral", "Article", "Determiner", "Particle",
    "Proper_noun", "Number", "Prefix", "Suffix", "Phrase",
    "Contraction", "Letter", "Symbol"
}

CACHE_DIR = Path("wiktionary_cache")
CACHE_DIR.mkdir(exist_ok=True)

def deduplicate(lst: list) -> list:
    """Remove duplicates from a list while preserving order."""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def get_cached_html(lemma: str) -> str | None:
    cache_file = CACHE_DIR / f"{lemma}.html"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    return None


def save_cached_html(lemma: str, html: str) -> None:
    cache_file = CACHE_DIR / f"{lemma}.html"
    cache_file.write_text(html, encoding="utf-8")


def parse_page(html: str) -> tuple[list[str], list[str]]:
    """
    Parse a Wiktionary REST API HTML page and extract suffixes and POS tags
    from the Ancient Greek section only.

    Suffixes are normalized to unicode and stripped of diacritics.
    Both lists are deduplicated (order-preserving).

    Returns:
        (suffixes, pos_tags) — deduplicated lists of strings, empty if nothing found.
    """
    soup = BeautifulSoup(html, "html.parser")

    raw_suffixes = [
        a["title"]
        for i_tag in soup.select("i.Polyt")
        if (a := i_tag.find("a")) and a.get("title", "").startswith("-")
    ]

    # Normalize → strip diacritics → deduplicate
    processed_suffixes = deduplicate([
        strip_diacritics(normalize_greek(s)) for s in raw_suffixes
    ])

    pos_tags = []
    in_greek_section = False

    for tag in soup.find_all(["h2", "h3", "h4"]):
        if tag.name == "h2":
            in_greek_section = (tag.get("id") == "Ancient_Greek")
            continue

        if not in_greek_section:
            continue

        if tag.name in ("h3", "h4"):
            tag_id = tag.get("id", "")
            base_id = tag_id.rstrip("_0123456789").rstrip("_")
            if base_id in KNOWN_POS:
                pos_tags.append(base_id.replace("_", " "))

    return processed_suffixes, deduplicate(pos_tags)


def extract_pos_only(html: str) -> list[str]:
    """
    Scan ALL headings in the page and return any heading id that matches a
    known POS. Used as a fallback when the standard parse returns an empty
    POS list. Result is deduplicated (order-preserving).
    """
    soup = BeautifulSoup(html, "html.parser")
    pos_tags = []
    for tag in soup.find_all(["h2", "h3", "h4"]):
        tag_id = tag.get("id", "")
        base_id = tag_id.rstrip("_0123456789").rstrip("_")
        if base_id in KNOWN_POS:
            pos_tags.append(base_id.replace("_", " "))
    return deduplicate(pos_tags)


def fetch_wiktionary(lemma: str, delay: float = 0.5) -> str | None:
    cached = get_cached_html(lemma)
    if cached is not None:
        return cached

    time.sleep(delay)
    url = f"https://en.wiktionary.org/api/rest_v1/page/html/{lemma}"
    try:
        response = SESSION.get(url, timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except (requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError):
        return None

    html = response.text
    save_cached_html(lemma, html)
    return html


def enrich_df(df: pd.DataFrame, delay: float = 0.5) -> pd.DataFrame:
    """
    Iterate over df['lemma_raw'], fetch Wiktionary data for each lemma,
    and store results in new 'suffix', 'suffix_betacode', and 'POS_wiki' columns.
    """
    suffixes, suffix_betacodes, pos_tags = [], [], []

    for lemma in tqdm(df["lemma_raw"], desc="Fetching Wiktionary data", unit="lemma"):
        if pd.isna(lemma) or str(lemma).strip() == "":
            suffixes.append(None)
            suffix_betacodes.append(None)
            pos_tags.append(None)
        else:
            html = fetch_wiktionary(str(lemma).strip(), delay=delay)
            if html is None:
                suffixes.append(None)
                suffix_betacodes.append(None)
                pos_tags.append(None)
            else:
                s, p = parse_page(html)
                suffixes.append(s)
                # Convert each suffix in the list to betacode
                suffix_betacodes.append([greek_unicode_to_betacode(suf) for suf in s])
                pos_tags.append(p)

    df["suffix"]          = suffixes
    df["suffix_betacode"] = suffix_betacodes
    df["POS_wiki"]        = pos_tags
    return df


def fix_empty_pos(df: pd.DataFrame, delay: float = 0.5) -> pd.DataFrame:
    """
    For rows where POS_wiki is an empty list, re-fetch (or load from cache)
    and attempt a broader POS extraction across all headings.
    """
    mask = df["POS_wiki"].apply(lambda v: isinstance(v, list) and len(v) == 0)
    targets = df.loc[mask, "lemma_raw"]
    print(f"Re-processing {mask.sum()} entries with empty POS_wiki...")

    for idx, lemma in tqdm(targets.items(), desc="Fixing empty POS", unit="lemma"):
        if pd.isna(lemma) or str(lemma).strip() == "":
            continue

        html = fetch_wiktionary(str(lemma).strip(), delay=delay)
        if html is None:
            continue

        pos = extract_pos_only(html)
        if pos:
            df.at[idx, "POS_wiki"] = pos

    return df


# ── Main ────────────────────────────────────────────────────────────────────

import ast

df = pd.read_csv("brill_dictionary_processed.csv")

for col in ["suffix", "suffix_betacode", "POS_wiki"]:
    if col in df.columns:
        df[col] = df[col].apply(lambda v: ast.literal_eval(v) if isinstance(v, str) else v)

df = enrich_df(df, delay=0.5)
df = fix_empty_pos(df, delay=0.5)
df.to_csv("wiktionary_enriched.csv", index=False)

# --- unique suffixes ---

suffixes: list[str] = [
    f"{strip_diacritics(clean_text(p1))} / {p2}"
    for suff_list, bc_list in zip(df["suffix"], df["suffix_betacode"])
    for p1, p2 in zip(suff_list, bc_list)
]
suffixes.append("Any")
pd.DataFrame(sorted(set(suffixes)), columns=["suffix"]).to_csv(
    "unique_suffixes.csv", index=False
)