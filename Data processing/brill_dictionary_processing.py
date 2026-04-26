"""
brill_dictionary_processing.py
--------------------------------
Parses the Brill XML dictionary, extracts lemmas and their derivations,
and produces three CSVs:
  - brill_dictionary_processed.csv  (one row per lemma)
  - unique_bases.csv                (unique compositional or derivational components)
  - unique_prefixes.csv             (unique prefixes)

After parsing all XML files, a post-processing pass recursively expands
any derivation component that is itself a lemma in the database, so that
e.g. ἀναρπάζω → ['ἀνα', 'ἁρπάζω'] instead of staying as a single token.
"""

from __future__ import annotations

import re
import regex
import unicodedata
from pathlib import Path

import pandas as pd
from lxml import etree


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PREFIXES: list[str] = [
    "ἀ", "ἁ", "ἀμφι", "ἀνα", "ἀντι", "ἀπο",
    "δια", "δίς", "δυσ", "ἐγ", "εἰσ", "ἐκ", "ἐμ", "ἐν",
    "ἐξ", "ἐπ", "ἐπι", "ἐσ", "εὐ", "κατα", "μετα",
    "ξυγ", "ξυν", "παρα", "περι", "προ", "προσ", "πρός",
    "συ", "συγ", "συλ", "συμ", "συν", "συρ", "ὑπερ", "ὑπο"
]

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


# ---------------------------------------------------------------------------
# Text normalisation helpers
# ---------------------------------------------------------------------------

def strip_diacritics(text: str) -> str:
    """Remove ALL combining diacritics (category Mn), return plain base letters."""
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC",
        "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn"),
    )


def _normalise_sigmas(text: str) -> str:
    """Collapse final sigma (ς) to medial sigma (σ) for comparison purposes."""
    return text.replace("ς", "σ")


# Built after strip_diacritics is defined
_PREFIX_LIST_STRIPPED: set[str] = {
    _normalise_sigmas(strip_diacritics(p)) for p in PREFIXES
}


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


def clean_text(text: str | None) -> str | None:
    """
    Keep only characters in the main Greek Unicode blocks
    (U+0370–U+03FF and U+1F00–U+1FFF) plus whitespace.
    """
    if not text:
        return text
    return re.sub(r"[^\u0370-\u03FF\u1F00-\u1FFF\s]", "", str(text)).strip()


# ---------------------------------------------------------------------------
# Beta Code conversion
# ---------------------------------------------------------------------------

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


def betacode_strip_diacritics(bc: str) -> str:
    """Remove Beta Code diacritic symbols, keeping only base letters."""
    return _BC_DIACRITICS_RE.sub("", bc)


def column_to_betacode(words: list[str]) -> list[str]:
    """Convert a list of Greek Unicode words to bare Beta Code (no diacritics)."""
    return [betacode_strip_diacritics(greek_unicode_to_betacode(w)) for w in words]


# ---------------------------------------------------------------------------
# Lemma / derivation field helpers
# ---------------------------------------------------------------------------

def move_leading_number(line: str | float) -> str | float:
    """
    Some lemmas are numbered like "1. λόγος". Move the number to the end:
    "λόγος 1".
    """
    if pd.isna(line):
        return line
    line = str(line).strip()
    match = re.match(r"^(\d+)\.\s*(.+)$", line)
    if match:
        number, text = match.groups()
        return f"{text} {number}"
    return line


def derivation_raw_column(line: str | float) -> list[str]:
    """
    Split the derivation string on ',' and ';', keep only parts that contain
    at least one Greek character, strip all non-Greek characters from those.
    If a segment contains 'see', 'cf.', '.', or '?', only the portion before
    it is kept (if that portion contains Greek characters).
    Returns an empty list for NaN / empty input.
    """
    if pd.isna(line):
        return []
    line = str(line).strip()
    if not line:
        return []

    # Truncate the entire line at the first occurrence of 'see', 'cf.', '.', or '?'
    line = re.split(r"see|cf\.|\.|\?", line, maxsplit=1)[0]

    parts = []
    for segment in re.split(r"[,;]", line):
        # keep only if there's at least one Greek Unicode character
        if not re.search(r"[\u0370-\u03FF\u1F00-\u1FFF]", segment):
            continue
        # strip everything that isn't a Greek character or space
        cleaned = re.sub(r"[^\u0370-\u03FF\u1F00-\u1FFF\s]", "", segment).strip()
        cleaned = normalize_greek(re.sub(r"\s+", " ", cleaned))
        if cleaned:
            parts.append(cleaned)
    return parts

def extract_prefixes(words: list[str]) -> list[str]:
    """
    From a list of (already normalised) Greek words, return those that
    match a known prefix (compared after diacritic-stripping) or contain
    a hyphen (indicating a combining form).
    """
    result = []
    for word in words:
        word_stripped = _normalise_sigmas(strip_diacritics(word.strip()))
        if word_stripped in _PREFIX_LIST_STRIPPED or ("-" in word and len(word) > 1):
            result.append(normalize_greek(clean_text(word.strip())))
    return result


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


def normalize_greek_in_text(text: str) -> str:
    """
    Apply normalize_greek() only to substrings written in Greek script.
    Everything else (Latin, punctuation, etc.) is preserved.
    """

    def _normalize_match(match: regex.Match) -> str:
        greek_segment = match.group(0)
        return normalize_greek(greek_segment)

    # Match sequences of Greek letters (including diacritics)
    pattern = r'\p{Script=Greek}+'

    return regex.sub(pattern, _normalize_match, text)

def parse_derivation(etym_node: etree._Element | None) -> tuple[str, list[str]]:
    if etym_node is None:
        return "", []

    etym_block = etym_node.find("block[@type='etymology']")
    if etym_block is None:
        return "", []

    text = " ".join(etym_block.itertext()).strip()
    text = re.sub(r"\s+", " ", text)
    text = normalize_greek_in_text(text)

    return text, []


def parse_lemma(xml_path: Path) -> dict[str, str | list[str]]:
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    lemma = normalize_greek(root.findtext("name") or "")
    etym_node = root.find("etymology")
    derivation, _ = parse_derivation(etym_node)  # unpack the tuple, discard the []
    derivation = re.sub(r"\n", "", derivation)

    return {"lemma": lemma, "derivation": derivation}


# ---------------------------------------------------------------------------
# Post-processing: recursive derivation expansion
#
# Called AFTER all XML files have been parsed and the full DataFrame exists,
# so that every lemma is guaranteed to be in the lookup table.
# ---------------------------------------------------------------------------

def _build_expansion_lookup(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Build { lemma_raw → [part1, part2, ...] } for all lemmas that have a
    non-empty derivation decomposition.
    """
    lookup: dict[str, list[str]] = {}
    for _, row in df.iterrows():
        key = str(row["lemma_raw"]).strip()
        parts = row["derivation_raw"]
        if isinstance(parts, list) and parts:
            lookup[key] = parts
    return lookup


def _expand_item(item, lookup, visited=None):
    if visited is None:
        visited = frozenset()
    key = normalize_greek(clean_text(item))
    if not key or key in visited or key not in lookup:
        return [item]
    if len(lookup[key]) < 2:
        return [item]
    visited = visited | {key}
    expanded = []
    for part in lookup[key]:
        expanded.extend(_expand_item(part, lookup, visited))
    return expanded


def expand_derivations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Post-processing pass: for every row, try to expand each element of
    derivation_raw by looking it up in the full lemma table.

    Rebuilds derivation_raw, derivation_betacode, prefix, and prefix_betacode
    to keep all columns consistent.

    The derivation string is updated in-place: each base that was further
    decomposed is substituted with its expansion joined by ' + ', while the
    rest of the string (cognates, references, etc.) is left untouched.
    """
    df = df.copy()
    lookup = _build_expansion_lookup(df)

    new_derivation_raw: list[list[str]] = []
    new_derivation: list[str] = []

    for _, row in df.iterrows():
        parts: list[str] = row["derivation_raw"] if isinstance(row["derivation_raw"], list) else []
        derivation_str: str = row["derivation"] if isinstance(row["derivation"], str) else ""
        derivation_str = regex.sub(r'\s+([^\w\s])', r'\1', derivation_str)

        if not parts:
            new_derivation_raw.append(parts)
            new_derivation.append(derivation_str)
            continue

        expanded: list[str] = []
        for part in parts:
            expansion = _expand_item(part, lookup)
            expanded.extend(expansion)

            # If the part was actually expanded (not returned unchanged),
            # substitute it in the derivation string
            if expansion != [part]:
                expansion_str = ", ".join(expansion)
                # Search for the base as a substring and replace only the
                # first occurrence to avoid clobbering unrelated mentions
                pattern = rf'(?<!\p{{L}}){regex.escape(part)}(?!\p{{L}})'
                derivation_str = regex.sub(pattern, expansion_str, derivation_str, count=1)

        derivation_str = regex.sub(r'\s+([^\w\s])', r'\1', derivation_str)
        new_derivation_raw.append(expanded)
        new_derivation.append(derivation_str)

    df["derivation_raw"] = new_derivation_raw
    df["derivation"] = new_derivation

    # Rebuild all derived columns so they stay in sync
    df["derivation_betacode"] = df["derivation_raw"].apply(
        lambda lst: column_to_betacode(lst) if lst else []
    )
    df["prefix"] = df["derivation_raw"].apply(extract_prefixes)
    df["prefix_betacode"] = df["prefix"].apply(column_to_betacode)

    return df


# ---------------------------------------------------------------------------
# DataFrame builder
# ---------------------------------------------------------------------------

def build_dictionary_dataframe(xml_dir: str | Path) -> pd.DataFrame:
    """
    Parse all XML files in *xml_dir* and return a fully processed DataFrame.
    """
    rows: list[dict] = []
    for xml_file in Path(xml_dir).glob("*.xml"):
        try:
            rows.append(parse_lemma(xml_file))
        except Exception as exc:  # noqa: BLE001
            print(f"Error parsing {xml_file.name}: {exc}")

    df = pd.DataFrame(rows)

    # --- Lemma columns ---
    df["lemma"] = df["lemma"].apply(move_leading_number).apply(normalize_greek)
    df["lemma_raw"] = df["lemma"].apply(clean_text).apply(normalize_greek)
    df["lemma_betacode"] = df["lemma_raw"].apply(greek_unicode_to_betacode)
    df["lemma_betacode_raw"] = df["lemma_betacode"].apply(betacode_strip_diacritics)

    df["derivation_raw"] = df["derivation"].apply(derivation_raw_column)
    df["derivation_betacode"] = df["derivation_raw"].apply(column_to_betacode)

    # --- Prefix columns ---
    df["prefix"] = df["derivation_raw"].apply(extract_prefixes)
    df["prefix_betacode"] = df["prefix"].apply(column_to_betacode)

    # --- Query display column ---
    df["query_lemmas"] = [
        f"{strip_diacritics(greek)} / {beta}" if greek and beta else (greek or "")
        for greek, beta in zip(df["lemma_raw"], df["lemma_betacode_raw"])
    ]

    df = expand_derivations(df)

    return df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    XML_DIR = "/Users/beatrice/Desktop/PycharmProjects/Fine-tuning/Dictionaries/Dizionario_Brill"

    result = build_dictionary_dataframe(XML_DIR)
    result.to_csv("brill_dictionary_processed.csv", index=False)

    # --- unique derivational bases or compounding items---
    compounds: list[str] = [
        f"{clean_text(p1)} / {p2}"
        for raw_list, bc_list in zip(result["derivation_raw"], result["derivation_betacode"])
        for p1, p2 in zip(raw_list, bc_list)
    ]
    pd.DataFrame(sorted(set(compounds)), columns=["base"]).to_csv(
        "unique_bases.csv", index=False
    )

    # --- unique prefixes ---
    prefixes: list[str] = [
        f"{strip_diacritics(clean_text(p1))} / {p2}"
        for pref_list, bc_list in zip(result["prefix"], result["prefix_betacode"])
        for p1, p2 in zip(pref_list, bc_list)
    ]
    prefixes.append("Any")
    pd.DataFrame(sorted(set(prefixes)), columns=["prefix"]).to_csv(
        "unique_prefixes.csv", index=False
    )