import streamlit as st


YORGLASS_COLORS = {
    "brand": "#FF5722",
    "brand_dark": "#E64A19",
    "brand_light": "#FF8A65",
    "blue": "#2196F3",
    "orange": "#FF9800",
    "green": "#4CAF50",
    "red": "#F44336",
    "purple": "#9C27B0",
    "cyan": "#00BCD4",
    "pink": "#E91E63",
    "grey": "#9E9E9E",
    "bg_dark": "#0E1117",
    "bg_card": "#1A1D23",
}


def inject_custom_css():
    st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(255,87,34,0.10) 0%, rgba(255,87,34,0.03) 100%);
        border: 1px solid rgba(255,87,34,0.18);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.2);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(255,87,34,0.25);
        border-color: rgba(255,87,34,0.35);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        opacity: 0.75;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
    }

    .main h2 {
        border-bottom: 3px solid #FF5722;
        padding-bottom: 10px;
        margin-top: 2.5rem !important;
        margin-bottom: 1.2rem !important;
    }
    .main h3 {
        color: #FF8A65;
        font-weight: 600;
        margin-top: 1.5rem !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E2229 0%, #0E1117 100%);
    }
    [data-testid="stSidebar"]::before {
        content: "YORGLASS";
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
        content: "Finansal Analiz Sistemi";
        display: block;
        font-size: 0.72rem;
        color: rgba(250,250,250,0.45);
        text-align: center;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        padding-bottom: 18px;
        margin-bottom: 8px;
    }

    hr {
        border: none !important;
        border-top: 1px solid rgba(255,87,34,0.15) !important;
        margin: 2rem 0 !important;
    }

    [data-testid="stExpander"] {
        border: 1px solid rgba(255,87,34,0.12);
        border-radius: 10px;
        background: rgba(255,87,34,0.02);
        overflow: hidden;
    }
    [data-testid="stExpander"] summary {
        font-weight: 600;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        overflow: hidden;
    }

    .stProgress > div > div > div {
        background: linear-gradient(90deg, #FF5722, #FF8A65) !important;
    }

    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #FF5722 0%, #E64A19 100%);
        border: none;
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.5px;
        padding: 0.5rem 1.2rem;
        transition: all 0.3s ease;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        background: linear-gradient(135deg, #E64A19 0%, #D84315 100%);
        box-shadow: 0 4px 16px rgba(255,87,34,0.4);
        transform: translateY(-1px);
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #FF5722 !important;
    }

    [data-testid="stChatMessage"] {
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.05);
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background: rgba(14,17,23,0.95);
        backdrop-filter: blur(10px);
    }

    .stSelectbox [data-baseweb="select"] {
        border-radius: 8px;
    }
    .stTextInput input {
        border-radius: 8px;
    }
    .stNumberInput input {
        border-radius: 8px;
    }

    [data-testid="stAlert"] {
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)


def get_plotly_template():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="sans-serif",
            color="#FAFAFA",
            size=13,
        ),
        title=dict(
            font=dict(size=16, color="#FAFAFA"),
            x=0.02,
            xanchor="left",
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.1)",
            linecolor="rgba(255,255,255,0.1)",
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.1)",
            linecolor="rgba(255,255,255,0.1)",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=12),
        ),
        hoverlabel=dict(
            bgcolor="#1A1D23",
            font_size=13,
            font_color="#FAFAFA",
            bordercolor="#FF5722",
        ),
        margin=dict(l=60, r=20, t=50, b=50),
    )


def apply_chart_style(fig, **kwargs):
    template = get_plotly_template()
    template.update(kwargs)
    fig.update_layout(**template)
    return fig


def render_page_header(title, description=None):
    st.markdown(f"""
    <div style="
        padding: 0 0 15px 0;
        margin-bottom: 20px;
        border-bottom: 2px solid rgba(255,87,34,0.2);
    ">
        <h1 style="
            margin: 0 0 8px 0;
            font-size: 2rem;
            font-weight: 700;
        ">{title}</h1>
        {f'<p style="color: rgba(250,250,250,0.6); font-size: 1rem; margin: 0;">{description}</p>' if description else ''}
    </div>
    """, unsafe_allow_html=True)


def render_info_box(text, box_type="info"):
    colors = {
        "info": ("#2196F3", "rgba(33,150,243,0.08)", "rgba(33,150,243,0.25)"),
        "warning": ("#FF9800", "rgba(255,152,0,0.08)", "rgba(255,152,0,0.25)"),
        "success": ("#4CAF50", "rgba(76,175,80,0.08)", "rgba(76,175,80,0.25)"),
        "danger": ("#F44336", "rgba(244,67,54,0.08)", "rgba(244,67,54,0.25)"),
    }
    accent, bg, border = colors.get(box_type, colors["info"])
    st.markdown(f"""
    <div style="
        padding: 16px 20px;
        border-left: 4px solid {accent};
        background: {bg};
        border: 1px solid {border};
        border-left: 4px solid {accent};
        border-radius: 0 10px 10px 0;
        margin: 12px 0;
        font-size: 0.95rem;
        line-height: 1.5;
    ">{text}</div>
    """, unsafe_allow_html=True)


def render_nav_card(title, icon, items):
    items_html = "".join(
        f'<li style="margin: 4px 0; color: rgba(250,250,250,0.7); font-size: 0.88rem;">{item}</li>'
        for item in items
    )
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(255,87,34,0.06) 0%, rgba(255,87,34,0.02) 100%);
        border: 1px solid rgba(255,87,34,0.12);
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        transition: all 0.3s ease;
    ">
        <div style="font-size: 1.6rem; margin-bottom: 8px;">{icon}</div>
        <h4 style="color: #FF8A65; margin: 0 0 10px 0; font-size: 1rem;">{title}</h4>
        <ul style="list-style: none; padding: 0; margin: 0;">
            {items_html}
        </ul>
    </div>
    """, unsafe_allow_html=True)
