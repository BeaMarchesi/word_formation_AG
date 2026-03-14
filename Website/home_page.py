import streamlit as st
from style import apply_style
from utils import BRAND_COLOR, render_sidebar_logos

apply_style()

LOGO_PATH = 'Website/Images/logo_larl_rosso.png'
LOGO_LINK = 'https://linguisticapavia.cdl.unipv.it/it'
st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)


# ── Title ─────────────────────────────────────────────────────────────────────

st.markdown(
    f"<h1 style='text-align: center; color: {BRAND_COLOR};'>Word Formation in Ancient Greek</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: grey; font-size: 0.95rem;'>"
    "A morphological database of the Ancient Greek lexicon"
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── About ─────────────────────────────────────────────────────────────────────

st.markdown(
    f"<h3 style='color: {BRAND_COLOR};'>About</h3>",
    unsafe_allow_html=True,
)
st.markdown("""
This interface provides structured access to a knowledge base of **133,000+ Ancient Greek lemmas**,
annotated for morphological structure, derivational history, and part of speech.
Each entry is linked to the corresponding LSJ (*Liddell–Scott–Jones Greek–English Lexicon*) entry
for full lexicographic reference.

The database distinguishes between **composition** (two or more independent bases)
and **derivation** (a single base with affixal morphology), and records prefixes and suffixes
in both normalised Greek and betacode transcription to support flexible querying.
""")

st.divider()

# ── Search modes ──────────────────────────────────────────────────────────────

st.markdown(
    f"<h3 style='color: {BRAND_COLOR};'>Search modes</h3>",
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🔍 Search by lemma**")
    st.markdown(
        "Retrieve the full morphological record for a specific lemma. "
        "Accepts both Unicode Greek and betacode input. Homographs are listed separately."
    )
    st.markdown("**📂 Search by part of speech and affix**")
    st.markdown(
        "Filter the lexicon by any combination of part of speech, prefix, and suffix "
        "to retrieve all matching derived or compound forms."
    )

with col2:
    st.markdown("**🔗 Search by lemma and part of speech**")
    st.markdown(
        "Given a base lemma, retrieve all words in which it appears as an etymological component, "
        "with optional filtering by part of speech and by word-formation type "
        "(composition vs. derivation)."
    )
    st.markdown("**🧩 Search by lemma and affix**")
    st.markdown(
        "Combine an etymological base with one or more affixes to retrieve words "
        "formed by a specific morphological pattern."
    )

st.divider()

# ── Data & methodology note ───────────────────────────────────────────────────

st.markdown(
    f"<h3 style='color: {BRAND_COLOR};'>Data and methodology</h3>",
    unsafe_allow_html=True,
)
st.markdown("""
Morphological annotations follow the conventions of the LARL research group
at the University of Pavia. Etymological segmentation is based on
the *Dictionnaire étymologique de la langue grecque* (Chantraine) and the LSJ,
with computational disambiguation of ambiguous formations.
Betacode encoding follows the TLG standard.

Results can be exported as CSV for use in external corpus tools or spreadsheet software.
""")

st.divider()

st.markdown(
    "<p style='text-align: center; color: grey; font-size: 0.85rem;'>"
    "LARL — Laboratorio di Linguistica e Archeologia del Mondo Romano e della Grecia Antica · "
    "Università degli Studi di Pavia"
    "</p>",
    unsafe_allow_html=True,
)