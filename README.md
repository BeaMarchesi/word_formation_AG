# Word Formation in Ancient Greek

**A queryable database and web interface for Ancient Greek derivational morphology.**

This repository contains the data, processing code, and web application for a new resource dedicated to Ancient Greek word formation (derivation and composition). The resource was built by segmenting and enriching entries from the digitalized *Brill Dictionary of Ancient Greek* [Montanari, 2015] with part-of-speech tags, prefix/suffix information, and semantic data drawn from Wiktionary and the Liddell–Scott–Jones (LSJ) Lexicon via the Perseus Digital Library.

The project is presented in the paper *"Toward Ancient Greek Word Formation: Getting to the Roots, Prefixes and (even) Suffixes"*, accepted at **CLiC-it 2026** (Twelfth Italian Conference on Computational Linguistics, Palermo, Italy, September 14–16, 2026).

---

## 🔗 Go to the resource

The online query interface is available here: 
https://word-formation-ag.streamlit.app

---

## About the resource

Ancient Greek makes extensive use of prefixation, suffixation, and compounding, but — unlike many modern high-resource languages — it has so far lacked a dedicated, queryable derivational morphology resource. This project fills that gap by providing:

- A structured database linking each Brill Dictionary lemma to its **derivation base(s)** or **compounding element(s)**, when available.
- Automatically assigned **part-of-speech tags** (from Wiktionary and the [odyCy](https://centre-for-humanities-computing.github.io/odyCy/) parser).
- **Prefix** information extracted via a pre-compiled list of Ancient Greek prefixes.
- **Suffix** information extracted from Wiktionary, complemented by a manually validated case study on the *-tēr* / -*tōr* nominal suffixes.
- Basic **semantic information** (top-level senses) linked to the corresponding [LSJ](https://www.perseus.tufts.edu/) entry on Perseus, where available.
- Support for both the **Ancient Greek alphabet** and **Beta Code** input/output.

The resource is a first stage in an ongoing project; see the [paper](#how-to-cite) for a full discussion of the data collection pipeline, current coverage, and known limitations.

## Repository structure

```
├── .devcontainer/       Development container configuration
├── Data processing/     Scripts for data extraction, cleaning, and enrichment
│                        (Brill Dictionary parsing, POS tagging, prefix/suffix
│                        extraction, Beta Code conversion, LSJ sense extraction)
├── Website/             Source code for the online querying interface
└── requirements.txt     Python dependencies
```

## Main data sources

| Source | Used for |
|---|---|
| [Brill Dictionary of Ancient Greek](https://dictionaries.brillonline.com/montanari) [Montanari, 2015] | Lemmas, derivation/composition data, prefixes |
| [Wiktionary](https://en.wiktionary.org/wiki/Wiktionary:Main_Page) | POS tags, suffix information |
| [odyCy](https://centre-for-humanities-computing.github.io/odyCy/) | Automatic POS tagging for lemmas missing Wiktionary coverage |
| [LSJ Lexicon via Perseus Digital Library](https://www.perseus.tufts.edu/) | Semantic (sense) information |

## Search functionalities

The web interface offers two main query modes:

1. **Search by entry** — query by lemma, POS, prefix, and/or suffix.
2. **Search by derivation or composition** — query by base lemma/compounding element(s), base/lexeme POS, entry POS, prefix, and/or suffix, with an **advanced composition query** mode to target specific compounding-element positions (up to 6 elements).

All results can be exported as CSV files directly from the interface.

## Limitations & future work

This is a first-stage resource. Known limitations include residual POS-tagging errors, limited suffix coverage (~5% of entries), sense-extraction issues for homographs and lemmas without a direct LSJ match, and inconsistencies inherited from the source XML files. Planned future work includes systematic manual validation, expanded suffix coverage, and conversion into Linked Open Data (e.g., via OntoLex-Lemon) for interoperability with resources such as UDer, MorphyNet, and LiLa. See Section 5–6 of the paper for details.

## How to cite

If you use this resource, please cite the following works:
Paper (accepted at CLiC-it 2026; full proceedings citation — including pages and DOI — will be added once available):
bibtex
@inproceedings{marchesi2026wordformation,
  title     = {Toward Ancient {G}reek Word Formation: Getting to the Roots, Prefixes and (even) Suffixes},
  author    = {Marchesi, Beatrice and Zampetta, Silvia and Mastellari, Virginia and Brigada Villa, Luca and Luraghi, Silvia and Zanchi, Chiara},
  booktitle = {Proceedings of the Twelfth Italian Conference on Computational Linguistics (CLiC-it 2026)},
  year      = {2026},
  address   = {Palermo, Italy},
  month     = {September},
  note      = {Accepted for publication},
}
Master's thesis (the resource originates from this thesis project):
bibtex
@mastersthesis{marchesi2026thesis,
  title  = {Ancient {G}reek Word Formation},
  author = {Marchesi, Beatrice},
  school = {IUSS Pavia},
  year   = {2026},
}

## License

This resource is made available for research purposes. Please refer to the corresponding paper and contact the authors for questions regarding reuse and licensing of the underlying data.
