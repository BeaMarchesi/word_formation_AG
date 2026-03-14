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

'''
def add_sidebar_logos():
    with open("/Users/beatrice/Desktop/PycharmProjects/Tesi IUSS/Images/logo_larl_rosso.png", "rb") as f:
        logo1 = base64.b64encode(f.read()).decode()

    with open("/Users/beatrice/Desktop/PycharmProjects/Tesi IUSS/Images/logo_larl_rosso.png", "rb") as f:
        logo2 = base64.b64encode(f.read()).decode()

    st.sidebar.markdown(
        f"""
        <style>
        .sidebar-logos {{
            position: fixed;
            bottom: 20px;
            left: 0;
            width: 100%;
            text-align: center;
        }}
        .sidebar-logos img {{
            margin-bottom: 10px;
        }}
        </style>

        <div class="sidebar-logos">
            <img src="data:image/png;base64,{logo1}" width="140"><br>
            <img src="data:image/png;base64,{logo2}" width="120">
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        """
        <style>
        .sidebar-content {
            display: flex;
            flex-direction: column;
            height: 100%;
        }

        .sidebar-top {
            flex-grow: 1;
        }

        .sidebar-logos {
            text-align: center;
            padding-bottom: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Wrap sidebar content
    st.sidebar.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-top">', unsafe_allow_html=True)

    # ---- your normal sidebar content happens here ----
    # (navigation, selectboxes, etc.)

    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # ---- Logos at bottom ----
    st.sidebar.markdown(
        """
        <div class="sidebar-logos">
            <img src="logo1.png" width="130"><br><br>
            <img src="logo2.png" width="120">
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

'''