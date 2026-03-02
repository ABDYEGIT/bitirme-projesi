"""
SAP Open SQL Generator - Stil Modulu.
"""
import streamlit as st


def inject_sap_css():
    """SAP agent icin ozel CSS enjekte eder."""
    st.markdown("""
    <style>
    /* Sidebar branding */
    [data-testid="stSidebar"]::before {
        content: "SAP SQL";
        display: block;
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: 4px;
        color: #FF5722;
        text-align: center;
        padding: 22px 0 4px 0;
        border-bottom: 2px solid rgba(255,87,34,0.3);
        margin-bottom: 4px;
    }
    [data-testid="stSidebar"]::after {
        content: "Open SQL Generator";
        display: block;
        font-size: 0.72rem;
        color: rgba(250,250,250,0.45);
        text-align: center;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        padding-bottom: 18px;
        margin-bottom: 8px;
    }

    /* Code block styling */
    .stCodeBlock {
        border: 1px solid rgba(255,87,34,0.2);
        border-radius: 8px;
    }

    /* Chat message styling */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.05);
        margin-bottom: 0.5rem;
    }

    /* Metadata cards */
    .metadata-card {
        background: rgba(255,87,34,0.06);
        border: 1px solid rgba(255,87,34,0.12);
        border-radius: 8px;
        padding: 8px 12px;
        margin: 4px 0;
        font-size: 0.85rem;
    }
    .metadata-card .table-name {
        color: #FF8A65;
        font-weight: 700;
        font-family: 'Consolas', monospace;
    }
    .metadata-card .field-count {
        color: rgba(250,250,250,0.5);
    }

    /* Status badges */
    .status-ok {
        color: #4CAF50;
        font-weight: 600;
    }
    .status-err {
        color: #f44336;
        font-weight: 600;
    }

    /* Hide deploy menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0E1117;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255,87,34,0.3);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255,87,34,0.5);
    }
    </style>
    """, unsafe_allow_html=True)
