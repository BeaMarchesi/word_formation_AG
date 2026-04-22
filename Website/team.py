import streamlit as st
from style import apply_style
from utils import BRAND_COLOR
import base64


apply_style()

LOGO_PATH = 'Website/Images/logo_larl_rosso.png'
LOGO_LINK = 'https://linguisticapavia.cdl.unipv.it/it'
st.logo(LOGO_PATH, size='large', link=LOGO_LINK, icon_image=None)


# ── Title ─────────────────────────────────────────────────────────────────────

st.markdown(
    f"<h1 style='text-align: center; color: {BRAND_COLOR};'>Team</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: grey; font-size: 0.95rem;'>"
    "The people behind the resource"
    "</p>",
    unsafe_allow_html=True,
)
st.divider()


# ── Team data ─────────────────────────────────────────────────────────────────
# Add or remove entries as needed. Fields:
#   name        : full name
#   role        : job title or academic role
#   affiliation : institution
#   email       : contact email (set to None to hide)
#   bio         : one or two sentence description (set to None to hide)
#   photo_path  : local path to portrait image (set to None to show initials placeholder)

TEAM = [
    {
        "name": "Beatrice Marchesi",
        "affiliation": "University of Pavia, IUSS Pavia",
        "email": 'beatrice.marchesi03@universitadipavia.it',
        "photo_path": 'Website/Images/IMG_7639.png',
    },
    {
        "name": "Chiara Zanchi",
        "affiliation": "University of Pavia",
        "email": "chiara.zanchi@unipv.it",
        "photo_path": None,
    },
    {
        "name": "Virginia Mastellari",
        "affiliation": "University of Pavia",
        "email": "virginia.mastellari@unipv.it",
        "photo_path": None,
    },
    {
        "name": "Silvia Zampetta",
        "affiliation": "University of Pavia",
        "email": 'silvia.zampetta01@universitadipavia.it',
        "photo_path": None,
    },
{
        "name": "Luca Brigada Villa",
        "affiliation": "University of Pavia",
        "email": 'luca.brigadavilla@unipv.it',
        "photo_path": None,
    },
{
        "name": "Silvia Luraghi",
        "affiliation": "University of Pavia",
        "email": 'luraghi@unipv.it',
        "photo_path": None,
    },
]


# ── Render cards ──────────────────────────────────────────────────────────────

def get_image_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def initials(name: str) -> str:
    parts = name.split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else parts[0][:2].upper()


def render_member(member: dict):
    card_style = (
        "background-color: #fdf5f5; border-left: 4px solid {color}; "
        "border-radius: 6px; padding: 1.2rem 1.4rem;"
    ).format(color=BRAND_COLOR)

    photo_html = ""
    if member["photo_path"]:
        img_b64 = get_image_base64(member["photo_path"])
        photo_html = (
            f"<img src='data:image/png;base64,{img_b64}' "
            "style='width:64px; height:64px; border-radius:50%; object-fit:cover; margin-bottom:0.75rem;'/>"
        )
    else:
        photo_html = (
            f"<div style='width:56px; height:56px; border-radius:50%; "
            f"background-color:{BRAND_COLOR}; color:white; font-size:1.1rem; font-weight:600; "
            "display:flex; align-items:center; justify-content:center; margin-bottom:0.75rem;'>"
            f"{initials(member['name'])}</div>"
        )

    email_html = ""
    if member["email"]:
        email_html = (
            f"<p style='font-size:0.8rem; color:grey; margin:0.1rem 0;'>"
            f"<a href='mailto:{member["email"]}' style='color:grey;'>{member['email']}</a></p>"
        )


    st.markdown(
        f"<div style='{card_style}'>"
        f"{photo_html}"
        f"<p style='font-size:1rem; font-weight:600; margin:0;'>{member['name']}</p>"
        f"<p style='font-size:0.8rem; color:grey; margin:0.1rem 0;'>{member['affiliation']}</p>"
        f"{email_html}"
        "</div>",
        unsafe_allow_html=True,
    )


cols_per_row = 2
for i in range(0, len(TEAM), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, member in enumerate(TEAM[i : i + cols_per_row]):
        with cols[j]:
            render_member(member)

        st.space()

st.markdown("<br>", unsafe_allow_html=True)
st.divider()


# ── Contributors ──────────────────────────────────────────────────────────────
# Anyone who contributed data but is not a core team member.
# Remove this section entirely if not needed.

#st.markdown(f"<h3 style='color: {BRAND_COLOR};'>Contributors</h3>", unsafe_allow_html=True)
#st.markdown("""
#We are grateful to the following people for contributing data to the resource:

#- Name Surname (Affiliation)
#""")
