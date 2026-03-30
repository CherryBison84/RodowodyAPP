"""
Wspólne ustawienia wyglądu, zapamiętywanie wczytanej bazy między krokami
oraz skróty do bloków „Pomoc” na stronie.
"""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from app.analytics.line_membership import compute_all_line_memberships
from app.data.dataset_loader import load_default_bison_report
from app.data.validator import validate_loaded_dataset
from app.ui import help_content as hc
from app.ui.tk.theme import Theme
from app.ui.typography import apply_matplotlib_fonts, css_font_family

THEME = Theme()


def help_expander(title: str, body: str, *, expanded: bool = False) -> None:
    """Składany blok pomocy (markdown)."""
    with st.expander(title, expanded=expanded):
        st.markdown(body)


def render_main_header(*, tagline: str | None = None) -> None:
    """Nagłówek obszaru głównego — ta sama estetyka co okno desktop (leśna paleta)."""
    tag = tagline or (
        "Import → walidacja spójności → rejestr osobniczy → analiza osobnicza → "
        "pary → parametry populacji → raport"
    )
    st.markdown(
        f"""
        <div class="wp-app-header">
            <h1>WisentPedigree Pro+</h1>
            <p class="wp-tagline">{tag}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_page_style() -> None:
    """CSS: motyw leśny (Theme) + dopracowanie kontrolek Streamlit."""
    apply_matplotlib_fonts()
    ff = css_font_family()
    st.markdown(
        f"""
        <style>
        html, body, .stApp,
        .stApp [data-testid="stMarkdownContainer"],
        .stApp button, .stApp input, .stApp textarea, .stApp select {{
            font-family: {ff} !important;
        }}
        .wp-app-header {{
            background: linear-gradient(135deg, {THEME.PANEL_BG} 0%, {THEME.PANEL_BG2} 55%, {THEME.PANEL_BG} 100%);
            border: 1px solid {THEME.BORDER_SUBTLE};
            border-radius: 14px;
            padding: 1.1rem 1.35rem 1.15rem;
            margin: 0 0 1.35rem 0;
            border-left: 5px solid {THEME.EDGE_PLOT};
            box-shadow: 0 2px 14px rgba(30, 43, 36, 0.07);
        }}
        .wp-app-header h1 {{
            margin: 0 0 0.4rem 0;
            font-size: clamp(1.45rem, 2.4vw, 1.75rem);
            font-weight: 700;
            letter-spacing: -0.025em;
            color: {THEME.TEXT} !important;
            line-height: 1.15;
        }}
        .wp-app-header, .wp-app-header h1, .wp-app-header .wp-tagline {{
            font-family: {ff} !important;
        }}
        .wp-app-header .wp-tagline {{
            margin: 0;
            color: {THEME.MUTED} !important;
            font-size: 1.02rem;
            line-height: 1.55;
        }}
        .stApp {{
            background-color: {THEME.APP_BG};
            color: {THEME.TEXT};
            font-size: 1.1458rem; /* ~+1pt względem 1.0625rem */
            line-height: 1.55;
        }}
        .stApp .main .block-container,
        .stApp .main p,
        .stApp .main li,
        .stApp .main label {{
            color: {THEME.TEXT} !important;
        }}
        .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {{
            color: {THEME.TEXT} !important;
        }}
        [data-testid="stSidebar"] {{
            background-color: {THEME.PANEL_BG};
            color: {THEME.TEXT};
            border-right: 1px solid {THEME.BORDER_SUBTLE};
            box-shadow: 6px 0 28px rgba(30, 43, 36, 0.06);
        }}
        [data-testid="stSidebar"] img {{
            border-radius: 10px;
            box-shadow: 0 1px 8px rgba(30, 43, 36, 0.08);
        }}
        /* Nawigacja: zaznaczony punkt jak aktywna zakładka Tk */
        [data-testid="stSidebar"] div[role="radiogroup"] label {{
            padding: 0.32rem 0.55rem;
            border-radius: 8px;
            margin-bottom: 2px;
            transition: background-color 0.15s ease;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
            background-color: {THEME.TAB_ACTIVE_BG} !important;
            font-weight: 600;
            color: {THEME.TAB_TEXT} !important;
            box-shadow: inset 0 0 0 1px {THEME.BORDER_SUBTLE};
        }}
        .stApp .main .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            max-width: min(120rem, 100%);
        }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stMarkdown {{
            color: {THEME.TEXT} !important;
        }}
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label {{
            color: {THEME.TEXT} !important;
        }}
        h1, h2, h3, h4 {{
            color: {THEME.TEXT} !important;
        }}
        .streamlit-expanderHeader {{
            font-weight: 600;
            color: {THEME.TEXT} !important;
        }}
        [data-testid="stCaption"] {{
            color: {THEME.MUTED} !important;
        }}
        div[data-testid="stMetric"] {{
            background-color: {THEME.PANEL_BG2};
            border: 1px solid {THEME.ACCENT};
            border-radius: 8px;
            padding: 8px;
            color: {THEME.TEXT} !important;
        }}
        div[data-testid="stMetric"] label {{
            color: {THEME.MUTED} !important;
        }}
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
            color: {THEME.TEXT} !important;
        }}
        .stApp a, section[data-testid="stSidebar"] a {{
            color: {THEME.LINK} !important;
        }}
        .stMarkdown a {{
            color: {THEME.LINK} !important;
        }}
        /* Pola formularza i selecty — leśne tła (BaseWeb / domyślne inputy) */
        .stTextInput input, .stNumberInput input, .stDateInput input {{
            background-color: {THEME.ENTRY_BG} !important;
            color: {THEME.TEXT} !important;
            border-color: {THEME.BORDER_SUBTLE} !important;
            border-radius: 6px !important;
        }}
        .stTextArea textarea {{
            background-color: {THEME.ENTRY_BG} !important;
            color: {THEME.TEXT} !important;
            border-color: {THEME.BORDER_SUBTLE} !important;
            border-radius: 6px !important;
        }}
        div[data-baseweb="select"] > div {{
            background-color: {THEME.ENTRY_BG} !important;
            border-color: {THEME.BORDER_SUBTLE} !important;
            color: {THEME.TEXT} !important;
        }}
        div[data-testid="stExpander"] details {{
            background-color: {THEME.PANEL_BG};
            border: 1px solid {THEME.BORDER_SUBTLE};
            border-radius: 8px;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: {THEME.BORDER_SUBTLE} !important;
        }}
        /* Przyciski — stonowana zieleń jak mech */
        .stButton > button {{
            background-color: {THEME.BUTTON_BG} !important;
            color: {THEME.TEXT} !important;
            border: 1px solid {THEME.BORDER_SUBTLE} !important;
        }}
        .stButton > button:hover {{
            background-color: {THEME.BUTTON_BG2} !important;
            border-color: {THEME.ACCENT} !important;
        }}
        .stDownloadButton > button {{
            background-color: {THEME.BUTTON_BG2} !important;
            color: {THEME.TEXT} !important;
            border: 1px solid {THEME.ACCENT} !important;
        }}
        /* Przycisk primary (zielony akcent rodowy) */
        div[data-testid="stBaseButton-primary"] > button,
        button[kind="primary"] {{
            background-color: {THEME.EDGE_PLOT} !important;
            color: #f4f8f4 !important;
            border: 1px solid {THEME.EDGE_PLOT} !important;
        }}
        div[data-testid="stBaseButton-primary"] > button:hover,
        button[kind="primary"]:hover {{
            background-color: {THEME.LINK} !important;
            border-color: {THEME.LINK} !important;
        }}
        /* Radio / checkbox */
        .stRadio label, .stCheckbox label, .stToggle label {{
            color: {THEME.TEXT} !important;
        }}
        /* Suwaki */
        div[data-testid="stSlider"] {{
            color: {THEME.TEXT};
        }}
        /* Tabele danych — ramka jak panel leśny */
        div[data-testid="stDataFrame"] {{
            border: 1px solid {THEME.BORDER_SUBTLE};
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 1px 12px rgba(30, 43, 36, 0.05);
        }}
        /* Zakładki analiz */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
            background-color: transparent;
            border-bottom: 1px solid {THEME.BORDER_SUBTLE};
            padding-bottom: 4px;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 9px 9px 0 0;
            padding: 0.45rem 0.85rem;
            background-color: {THEME.TAB_BG};
            color: {THEME.TAB_TEXT};
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            background-color: {THEME.PANEL_BG2};
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {THEME.TAB_ACTIVE_BG} !important;
            font-weight: 600;
            color: {THEME.TAB_TEXT} !important;
            box-shadow: inset 0 -2px 0 {THEME.EDGE_PLOT};
        }}
        .stTabs [role="tab"] {{
            border-radius: 9px 9px 0 0;
        }}
        .stTabs [role="tab"][aria-selected="true"] {{
            background-color: {THEME.TAB_ACTIVE_BG} !important;
            font-weight: 600;
        }}
        /* Strefa uploadu */
        [data-testid="stFileUploader"] section {{
            background-color: {THEME.ENTRY_BG} !important;
            border: 2px dashed {THEME.BORDER_SUBTLE} !important;
            border-radius: 12px !important;
        }}
        [data-testid="stFileUploader"] section:hover {{
            border-color: {THEME.ACCENT} !important;
        }}
        /* Delikatny scrollbar (WebKit) */
        .stApp ::-webkit-scrollbar {{
            width: 10px;
            height: 10px;
        }}
        .stApp ::-webkit-scrollbar-thumb {{
            background: {THEME.BORDER_SUBTLE};
            border-radius: 8px;
            border: 2px solid {THEME.APP_BG};
        }}
        .stApp ::-webkit-scrollbar-thumb:hover {{
            background: {THEME.ACCENT};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def id_sort_key(s: str) -> tuple[int, str]:
    m = re.match(r"^(\d+)([A-Za-z]*)$", s)
    if not m:
        return (10**30, s)
    return (int(m.group(1)), m.group(2) or "")


def set_dataset(df_std: pd.DataFrame, source: str) -> None:
    from app.pedigree.ancestor_pedigree import build_people_map

    st.session_state["df_std"] = df_std
    st.session_state["source"] = source
    people = build_people_map(df_std)
    st.session_state["people"] = people
    st.session_state["validation_report"] = validate_loaded_dataset(df_std=df_std, people=people)
    try:
        st.session_state["line_memberships"] = compute_all_line_memberships(people)
    except Exception:
        st.session_state["line_memberships"] = {}


def load_default_once() -> None:
    if "df_std" in st.session_state:
        return
    try:
        df_std, _ = load_default_bison_report()
        set_dataset(df_std, "Domyślna baza")
    except Exception:
        pass


def fmt_line_block(mem: object) -> str:
    if mem is None:
        return "Sireline: NA\nDamline: NA"
    return (
        f"Sireline: {mem.sire_founder_id} ({mem.sire_founder_name or 'NA'}) [steps={mem.sire_steps}]\n"
        f"Damline: {mem.dam_founder_id} ({mem.dam_founder_name or 'NA'}) [steps={mem.dam_steps}]"
    )


# Ta sama rodzina co w CSS (np. do inline HTML w streamlit_app)
FONT_FAMILY_CSS = css_font_family()

# Eksport help_content dla sekcji (sidebar)
GLOSSARY = hc.GLOSSARY
SECTION_VALIDATION = hc.SECTION_VALIDATION
SECTION_REFERENCES = hc.SECTION_REFERENCES
