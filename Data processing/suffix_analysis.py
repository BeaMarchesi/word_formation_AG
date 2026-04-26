import pandas as pd
import unicodedata

df = pd.read_csv('kb.csv')

lemmas = df['lemma_raw']

def strip_diacritics(text: str) -> str:
    """Remove ALL combining diacritics (category Mn), return plain base letters."""
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC",
        "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn"),
    )

matches = []
derivation = []
meaning = []
url = []
pos = []

for i in range(len(df)):
    if strip_diacritics(lemmas[i]).endswith(('τηρ', 'τωρ')) and len(lemmas[i]) > 3:
        matches.append(lemmas[i])
        derivation.append(df['derivation_raw'][i])
        meaning.append(df['meaning'][i])
        url.append(df['url'][i])
        pos.append(df['part_of_speech'][i])

df_build = []
df_build.extend([matches, derivation, meaning, url, pos])

matches1 = []
derivation1 = []
meaning1 = []
url1 = []
pos1 = []
