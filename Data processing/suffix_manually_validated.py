import pandas as pd
import re
import unicodedata
from ast import literal_eval

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

def strip_diacritics(text: str) -> str:
    """Remove ALL combining diacritics (category Mn), return plain base letters."""
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC",
        "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn"),
    )

def clean_text(text: str | None) -> str | None:
    """
    Keep only characters in the main Greek Unicode blocks
    (U+0370–U+03FF and U+1F00–U+1FFF) plus whitespace.
    """
    if not text:
        return text
    return re.sub(r"[^\u0370-\u03FF\u1F00-\u1FFF\s]", "", str(text)).strip()

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


def safe_literal_eval(x):
    if pd.isna(x) or x == "":
        return []
    try:
        return literal_eval(x)
    except Exception:
        return []

df = pd.read_csv(
    'merged_pos.csv',
    sep=',',
    converters={
        'suffix': safe_literal_eval,
        'suffix_betacode': safe_literal_eval
    }
)
manual_suffix = pd.read_csv('suffix_analysis_thr_twr_rivisto.csv', sep=';')

clean_mask = manual_suffix['Clean'].str.strip().str.lower() == 'yes'
clean_lemmas = manual_suffix.loc[clean_mask, 'lemma']

# Identify rows in df whose lemma_raw was marked clean
df_mask = df['lemma_raw'].isin(clean_lemmas)

# Compute suffix: '- ' + last 3 chars of lemma_raw stripped of diacritics
df.loc[df_mask, 'suffix'] = df.loc[df_mask, 'lemma_raw'].apply(
    lambda w: ['- ' + strip_diacritics(w[-3:])]
)

# Compute suffix_betacode: betacode of the same last-3-chars (without '- ')
df.loc[df_mask, 'suffix_betacode'] = df.loc[df_mask, 'lemma_raw'].apply(
    lambda w: ['- ' + greek_unicode_to_betacode(strip_diacritics(w[-3:]))]
)

df["suffix"] = df["suffix"].apply(lambda x: x if isinstance(x, list) else [])
df["suffix_betacode"] = df["suffix_betacode"].apply(lambda x: x if isinstance(x, list) else [])

df.to_csv('merged_suffix.csv', index=False)

# --- unique suffixes ---

suffixes: list[str] = [
    f"-{strip_diacritics(clean_text(p1))} / {p2}"
    for suff_list, bc_list in zip(df["suffix"], df["suffix_betacode"])
    for p1, p2 in zip(suff_list, bc_list)
    if p1 is not None and p2 is not None
]

pd.DataFrame(sorted(set(suffixes)), columns=["suffix"]).to_csv(
    "unique_suffixes.csv", index=False
)