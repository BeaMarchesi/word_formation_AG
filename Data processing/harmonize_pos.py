import pandas as pd

# ── Configuration ──────────────────────────────────────────────────────────────

MERGE_ON = "lemma_raw"

UNIFIED_VOCAB = {
    "Noun", "Verb", "Adjective", "Adverb", "Pronoun",
    "Preposition", "Conjunction", "Interjection", "Numeral",
    "Determiner", "Particle", "Affix", "Symbol", "Other",
}

# Wiktionary tag mapping
TOOL1_TO_UNIFIED: dict[str, str] = {
    "Noun":        "Noun",
    "Verb":        "Verb",
    "Adjective":   "Adjective",
    "Adverb":      "Adverb",
    "Participle":  "Verb",
    "Pronoun":     "Pronoun",
    "Preposition": "Preposition",
    "Conjunction": "Conjunction",
    "Interjection":"Interjection",
    "Numeral":     "Numeral",
    "Number":      "Numeral",
    "Article":     "Determiner",
    "Determiner":  "Determiner",
    "Particle":    "Particle",
    "Proper noun": "Proper noun",
    "Prefix":      "Affix",
    "Suffix":      "Affix",
    "Letter":      "Other",
    "Symbol":      "Symbol",
    "Phrase":      "Phrase",
    "Contraction": "Contraction",
}

# odyCy tag mapping
TOOL2_TO_UNIFIED: dict[str, str] = {
    "NOUN":  "Noun",
    "PROPN": "Proper noun",
    "VERB":  "Verb",
    "AUX":   "Verb",
    "ADJ":   "Adjective",
    "NUM":   "Numeral",
    "DET":   "Determiner",
    "PRON":  "Pronoun",
    "ADV":   "Adverb",
    "CCONJ": "Conjunction",
    "SCONJ": "Conjunction",
    "ADP":   "Preposition",
    "INTJ":  "Interjection",
    "PART":  "Particle",
    "PUNCT": "Punctuation",
    "X": ""
}
# ── Core functions ─────────────────────────────────────────────────────────────

def normalise_tag(raw_tag: str,
                  mapping: dict[str, str],
                  unknown: str = "Other") -> str:
    """Map a single raw tag to the unified vocabulary."""
    return mapping.get(raw_tag, unknown)


def normalise_tag_list(raw_tags: list[str],
                       mapping: dict[str, str],
                       unknown: str = "Other") -> list[str]:
    """
    Normalise a list of raw tags, deduplicate while preserving order.
    (Two different fine-grained tags may collapse to the same unified label.)
    """
    seen = set()
    result = []
    for tag in raw_tags:
        unified = normalise_tag(tag, mapping, unknown)
        if unified not in seen:
            seen.add(unified)
            result.append(unified)
    return result


def merge_pos_dataframes(df1: pd.DataFrame,
                         df2: pd.DataFrame,
                         merge_on: str | list[str] = MERGE_ON) -> pd.DataFrame:

    df1 = df1.copy().rename(columns={'POS_wiki': "pos_tool1_raw"})
    df2 = df2.copy().rename(columns={'part_of_speech': "pos_tool2_raw"})

    # Suffix _t2 on tool2 columns that clash with tool1 (other than merge key)
    merged = pd.merge(df1, df2, on=merge_on, how="outer", suffixes=("", "_t2"))

    def compute_unified(row) -> list[str]:
        tool1_raw = row["pos_tool1_raw"]
        tool2_raw = row["pos_tool2_raw"]

        if isinstance(tool1_raw, list) and len(tool1_raw) > 0:
            return normalise_tag_list(tool1_raw, TOOL1_TO_UNIFIED)
        if pd.notna(tool2_raw):
            return [normalise_tag(str(tool2_raw), TOOL2_TO_UNIFIED)]
        return []

    merged["pos_unified"] = merged.apply(compute_unified, axis=1)

    # Drop all tool2-only columns (_t2 suffix) and the two raw pos columns
    t2_cols = [c for c in merged.columns if c.endswith("_t2")]
    merged = merged.drop(columns=["pos_tool1_raw", "pos_tool2_raw"] + t2_cols)

    # Rename pos_unified back to the original pos column name
    merged = merged.rename(columns={"pos_unified": 'part_of_speech'})

    return merged


def coverage_report(merged: pd.DataFrame) -> pd.DataFrame:
    """
    Print a summary of tag origins and the distribution of unified tags
    (counting each tag once per token even if it appears in a list).
    """
    total = len(merged)
    from_tool1 = merged["pos_tool1_raw"].apply(
        lambda x: isinstance(x, list) and len(x) > 0
    ).sum()
    from_tool2_only = total - from_tool1

    print(f"Total tokens                    : {total}")
    print(f"Covered by tool1 (trusted)      : {from_tool1} ({from_tool1/total:.1%})")
    print(f"Filled by tool2 only (fallback) : {from_tool2_only} ({from_tool2_only/total:.1%})")
    print()

    # Count ambiguous tokens (more than one reading in unified output)
    ambiguous = merged["pos_unified"].apply(lambda x: len(x) > 1).sum()
    print(f"Tokens with multiple readings   : {ambiguous} ({ambiguous/total:.1%})")
    print()

    # Tag frequency (explode lists, count each tag occurrence)
    tag_counts = (
        merged["pos_unified"]
        .explode()
        .value_counts()
        .rename_axis("tag")
        .reset_index(name="count")
    )
    tag_counts["pct"] = (tag_counts["count"] / total * 100).round(1)
    print(tag_counts.to_string(index=False))
    return tag_counts


# ── Example usage ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import ast

    tool1_data = pd.read_csv('wiktionary_enriched.csv')
    tool2_data = pd.read_csv('odycy.csv')

    tool1_data["POS_wiki"] = tool1_data["POS_wiki"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )

    result = merge_pos_dataframes(tool1_data, tool2_data)
    result.to_csv('merged_pos.csv', index=False)

    print("=== Merged dataframe ===")
    print(result.to_string(index=False))
    print()

    print("=== Coverage & distribution ===")
    coverage_report(result)