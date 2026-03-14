import streamlit as st
import base64

def apply_style():
    st.markdown("""
    <style>
    
    /* ------------------ MAIN TITLE ------------------ */
    h1 {
        color: #b32c4b !important;
    }
    
    /* ------------------ MAIN TEXT ------------------ */
    body {
        color: #3b3b3b;
    }
    
    /* ------------------ SIDEBAR ------------------ */
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #3b3b3b;
    }
    
    /* Sidebar text */
    [data-testid="stSidebar"] * {
        color: white;
    }
    
    /* ------------------ SELECTBOX ------------------ */
    
    /* Main selectbox container (collapsed view) */
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background-color: #f2f2f2 !important;   /* light grey */
        color: #3b3b3b !important;              /* readable dark text */
        border-radius: 6px;
    }
    
    /* Dropdown menu background */
    div[role="listbox"] {
        background-color: #ffffff !important;
    }
    
    /* Dropdown options text */
    div[role="option"] {
        color: #3b3b3b !important;
    }
    
    /* Hover effect on options */
    div[role="option"]:hover {
        background-color: #b32c4b !important;
        color: white !important;
    }
    
    /* ------------------ DOWNLOAD BUTTON ------------------ */
    
    [data-testid="stDownloadButton"] button {
        background-color: #b32c4b !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
    }
    
    [data-testid="stDownloadButton"] button:hover {
        background-color: #8e223c !important;
        color: white !important;
    }
        
    /* ------------------ BUTTONS ------------------ */
    .stButton > button {
        background-color: #b32c4b;
        color: white;
        border-radius: 8px;
        border: none;
    }
    
    .stButton > button:hover {
        background-color: #3b3b3b;
        color: white;
    }

    button[kind="secondary"] {
        background-color: #b32c4b;
        color: white;
        border: none;
    }
    button[kind="secondary"]:hover {
        background-color: #3b3b3b;
        color: white;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)