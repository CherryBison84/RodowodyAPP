"""
Wspólne ustawienia wyglądu, zapamiętywanie wczytanej bazy między krokami
oraz skróty do bloków „Pomoc” na stronie.
"""

from __future__ import annotations

import html
import re

import pandas as pd
import streamlit as st

from app.analytics.line_membership import compute_all_line_memberships
from app.data.dataset_loader import dataframe_app_schema_columns, load_default_bison_report
from app.data.validator import validate_loaded_dataset
from app.ui import help_content as hc
from app.ui.theme import Theme
from app.ui.typography import apply_matplotlib_fonts, css_font_family

THEME = Theme()


def population_dashboard_metric(
    label: str,
    value: str,
    *,
    accent: str,
    panel_bg: str,
    help_text: str | None = None,
) -> None:
    """Jedna metryka dashboardu populacji: wartość w kolorze akcentu sekcji (jak nagłówek grupy)."""
    th = THEME
    lab = html.escape(label)
    val = html.escape(value)
    tip = html.escape(help_text) if help_text else ""
    help_badge = (
        f'<span style="cursor:help;color:{th.MUTED};font-size:0.78rem;margin-left:5px;" title="{tip}">?</span>'
        if tip
        else ""
    )
    st.markdown(
        f'<div style="background:{panel_bg};border-left:4px solid {accent};border-radius:10px;'
        f"padding:10px 14px 12px;border:1px solid rgba(30,43,36,0.1);min-height:4.6rem;\">"
        f'<div style="display:flex;align-items:baseline;flex-wrap:wrap;color:{th.MUTED};font-size:0.875rem;">'
        f"<span>{lab}</span>{help_badge}</div>"
        f'<div style="color:{accent};font-weight:700;font-size:1.48rem;line-height:1.2;margin-top:7px;'
        f'font-variant-numeric: tabular-nums;">{val}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def population_viz_tabs_css(*, widget_key: str = "pop_chart_viz_tabs") -> str:
    """
    Style zakładek wykresów populacji — kolory jak sekcje dashboardu.
    Wymaga `st.tabs(..., key=widget_key)`; Streamlit dodaje klasę `st-key-<key>`.
    """
    th = THEME
    pairs = [
        (th.EDGE_PLOT, th.PANEL_BG2),
        (th.ACCENT, th.ENTRY_BG),
        (th.LINK, th.PANEL_BG),
        (th.COMPLETENESS_ACCENT, th.TREE_BG),
        (th.EDGE_PLOT, th.TAB_BG),
    ]
    sel = f".st-key-{widget_key}"
    parts: list[str] = []
    for i, (ac, bg) in enumerate(pairs, start=1):
        parts.append(
            f"{sel} [data-baseweb=\"tab-list\"] [data-baseweb=\"tab\"]:nth-child({i}){{"
            f"background-color:{bg}!important;border-top:3px solid {ac}!important;"
            f"color:{th.TEXT}!important;}}"
            f"{sel} [data-baseweb=\"tab-list\"] [data-baseweb=\"tab\"]:nth-child({i})[aria-selected=\"true\"]{{"
            f"box-shadow:inset 0 -3px 0 {ac}!important;font-weight:600!important;}}"
        )
    return f"<style>{''.join(parts)}</style>"


def population_dashboard_group_header(
    title: str, description: str, *, accent: str, background: str
) -> None:
    """Tematyczna grupa metryk: nagłówek z kolorową krawędzią (dashboard populacji)."""
    th = THEME
    st.markdown(
        f'<div style="background:{background};border-left:4px solid {accent};padding:11px 14px 9px;'
        f"border-radius:10px;margin:14px 0 6px 0;border:1px solid rgba(30,43,36,0.11);\">"
        f'<div style="font-weight:700;font-size:1.02rem;color:{th.TEXT};letter-spacing:0.01em;">{title}</div>'
        f'<div style="font-size:0.82rem;color:{th.MUTED};margin-top:4px;line-height:1.4;">{description}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def help_expander(title: str, body: str, *, expanded: bool = False) -> None:
    """Składany blok pomocy (markdown)."""
    with st.expander(title, expanded=expanded):
        st.markdown(body)


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
        /* Nawigacja: zaznaczony punkt jak aktywna karta */
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
        /* Pobierz wykres (PNG) i inne pobrania w treści — mniejsza czcionka (~2–3 pt) */
        [data-testid="stMain"] .stDownloadButton > button,
        .stMain .stDownloadButton > button,
        section.main .stDownloadButton > button {{
            font-size: calc(1em - 2.5pt) !important;
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


def set_dataset(df_std: pd.DataFrame, source: str, *, update_import_snapshot: bool = True) -> None:
    """
    Zapisuje standaryzowany zbiór w sesji Streamlit, buduje `people` i przelicza walidację.

    Gdy ``update_import_snapshot`` jest True (domyślnie przy imporcie), zapamiętywana jest kopia
    pod przycisk „Przywróć surowy zbiór z importu” w panelu auto-poprawek.
    """
    from app.pedigree.ancestor_pedigree import build_people_map

    df_std = dataframe_app_schema_columns(df_std)
    st.session_state["df_std"] = df_std
    st.session_state["source"] = source
    if update_import_snapshot:
        st.session_state["df_std_import_snapshot"] = df_std.copy(deep=True)
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

# Eksport help_content dla sekcji (stopka strony / sidebar gdy używane)
GLOSSARY = hc.GLOSSARY
SECTION_VALIDATION = hc.SECTION_VALIDATION
SECTION_REFERENCES = hc.SECTION_REFERENCES
