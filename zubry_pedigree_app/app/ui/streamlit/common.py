"""
Wspólne ustawienia wyglądu, zapamiętywanie wczytanej bazy między krokami
oraz skróty do bloków „Pomoc” na stronie.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from app.analytics.line_membership import compute_all_line_memberships
from app.data.dataset_loader import dataframe_app_schema_columns
from app.data.validator import validate_loaded_dataset
from app.ui import help_content as hc
from app.ui.theme import Theme
from app.ui.typography import apply_matplotlib_fonts, css_font_family

THEME = Theme()

# Podgląd JPEG/PNG w UI — szerokość ≈ 1/n naturalnej (np. 5 → pięciokrotnie mniejszy).
IMAGE_DISPLAY_SCALE: int = 5


def show_image_at_scale(
    image_path: str | Path,
    *,
    scale: int = IMAGE_DISPLAY_SCALE,
    center: bool = True,
) -> None:
    """Wyświetla obraz zmniejszony co najmniej ``scale``× względem rozmiaru pliku."""
    from PIL import Image

    path = Path(image_path)
    if not path.is_file():
        st.warning(f"Brak obrazu: `{path}`")
        return

    scale = max(1, int(scale))
    img = Image.open(path)
    w, h = img.size
    new_w, new_h = max(1, w // scale), max(1, h // scale)
    if (new_w, new_h) != (w, h):
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    if center and scale > 1:
        pad = (scale - 1) // 2
        _l, mid, _r = st.columns([pad, 1, pad])
        with mid:
            st.image(img, width=new_w)
    else:
        st.image(img, width=new_w)


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
        header[data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu,
        footer {{
            display: none !important;
        }}
        [data-testid="stAppViewContainer"] {{
            background-color: {THEME.APP_BG};
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
        /* Nawigacja: pionowy przebieg kroków zamiast surowej listy radio */
        [data-testid="stSidebar"] div[role="radiogroup"] {{
            position: relative;
            gap: 0.26rem;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label {{
            position: relative;
            min-height: 2.62rem;
            padding: 0.42rem 0.5rem 0.42rem 2.42rem;
            border-radius: 8px;
            margin-bottom: 0.1rem;
            transition: background-color 0.15s ease, box-shadow 0.15s ease;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
            display: none !important;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label::before {{
            position: absolute;
            left: 0.54rem;
            top: 0.58rem;
            z-index: 1;
            width: 1.22rem;
            height: 1.22rem;
            border-radius: 999px;
            background: {THEME.ENTRY_BG};
            border: 1px solid {THEME.BORDER_SUBTLE};
            color: {THEME.MUTED};
            display: grid;
            place-items: center;
            font-size: 0.68rem;
            font-weight: 700;
            line-height: 1;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label::after {{
            content: "";
            position: absolute;
            left: 1.13rem;
            top: 1.86rem;
            bottom: -0.5rem;
            width: 1px;
            background: {THEME.BORDER_SUBTLE};
            opacity: 0.55;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:last-child::after {{
            display: none;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(1)::before {{ content: "1"; }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(2)::before {{ content: "2"; }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(3)::before {{ content: "3"; }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(4)::before {{ content: "4"; }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(5)::before {{ content: "5"; }}
        [data-testid="stSidebar"] div[role="radiogroup"] label p {{
            line-height: 1.32;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
            background-color: {THEME.TAB_ACTIVE_BG} !important;
            font-weight: 600;
            color: {THEME.TAB_TEXT} !important;
            box-shadow: inset 0 0 0 1px {THEME.BORDER_SUBTLE};
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before {{
            background: {THEME.EDGE_PLOT};
            border-color: {THEME.EDGE_PLOT};
            color: {THEME.ENTRY_BG};
            box-shadow: 0 0 0 3px rgba(61, 99, 77, 0.13);
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(3):has(input:checked) {{
            background-color: #d8dfd9 !important;
            color: {THEME.MUTED} !important;
            box-shadow: inset 0 0 0 1px #c4cec6;
        }}
        [data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(3):has(input:checked)::before {{
            background: #9aaa9e;
            border-color: #9aaa9e;
            color: #f4f8f4;
            box-shadow: none;
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
        .stMarkdown code {{
            background-color: #edf5ef !important;
            color: {THEME.LINK} !important;
            border: 1px solid rgba(53, 93, 71, 0.18);
            border-radius: 5px;
            padding: 0.08rem 0.32rem;
            font-size: 0.88em;
            font-weight: 650;
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
            border-radius: 7px !important;
            min-height: 2.42rem;
            box-shadow: 0 1px 3px rgba(30, 43, 36, 0.06);
            transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
        }}
        .stButton > button:hover {{
            background-color: {THEME.BUTTON_BG2} !important;
            border-color: {THEME.ACCENT} !important;
            box-shadow: 0 2px 7px rgba(30, 43, 36, 0.12);
        }}
        .stButton > button:active,
        .stDownloadButton > button:active,
        [data-testid="stFileUploaderDropzone"] button:active {{
            cursor: progress !important;
            filter: saturate(0.88) brightness(0.96);
        }}
        .stDownloadButton > button {{
            background-color: {THEME.BUTTON_BG2} !important;
            color: {THEME.TEXT} !important;
            border: 1px solid {THEME.ACCENT} !important;
            border-radius: 7px !important;
            min-height: 2.34rem;
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
            font-weight: 700 !important;
            box-shadow: 0 2px 10px rgba(61, 99, 77, 0.16);
        }}
        div[data-testid="stBaseButton-primary"] > button:hover,
        button[kind="primary"]:hover {{
            background-color: {THEME.LINK} !important;
            border-color: {THEME.LINK} !important;
        }}
        .st-key-huba_clear_catalog_btn button {{
            background-color: #eadbd2 !important;
            border-color: #b78b73 !important;
            color: #4f3024 !important;
        }}
        .st-key-huba_clear_catalog_btn button:hover {{
            background-color: #dfc7ba !important;
            border-color: {THEME.ACCENT} !important;
            color: #3d231a !important;
        }}
        html:has(button:disabled),
        html:has([aria-disabled="true"]),
        html:has(img[alt="Running..."]) {{
            cursor: progress !important;
        }}
        html:has(button:disabled) *,
        html:has([aria-disabled="true"]) *,
        html:has(img[alt="Running..."]) * {{
            cursor: progress !important;
        }}
        .stButton > button:disabled,
        .stDownloadButton > button:disabled,
        [data-testid="stFileUploaderDropzone"][aria-disabled="true"] {{
            opacity: 0.66;
            filter: saturate(0.86);
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
            min-height: 4.25rem;
        }}
        [data-testid="stFileUploader"] section:hover {{
            border-color: {THEME.ACCENT} !important;
            background-color: #f7faf7 !important;
        }}
        [data-testid="stFileUploaderDropzoneInstructions"] svg {{
            color: {THEME.COMPLETENESS_ACCENT} !important;
            opacity: 0.9;
        }}
        [data-testid="stFileUploaderDropzoneInstructions"] span,
        [data-testid="stFileUploaderDropzoneInstructions"] div {{
            color: {THEME.TEXT} !important;
        }}
        [data-testid="stFileUploaderDropzoneInstructions"] span:last-child {{
            color: {THEME.MUTED} !important;
        }}
        [data-testid="stFileUploaderDropzone"] button {{
            background-color: {THEME.EDGE_PLOT} !important;
            color: {THEME.ENTRY_BG} !important;
            border: 1px solid {THEME.EDGE_PLOT} !important;
            box-shadow: 0 1px 6px rgba(30, 43, 36, 0.12);
        }}
        [data-testid="stFileUploaderDropzone"] button:hover {{
            background-color: {THEME.LINK} !important;
            border-color: {THEME.LINK} !important;
        }}
        [data-testid="stAlertContainer"] {{
            border-radius: 10px !important;
            border: 1px solid {THEME.BORDER_SUBTLE} !important;
            box-shadow: none !important;
        }}
        [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {{
            background-color: {THEME.TREE_BG} !important;
        }}
        [data-testid="stAlertContentInfo"] {{
            color: {THEME.LINK} !important;
        }}
        [data-testid="stAlertContentInfo"] > div {{
            background-color: {THEME.TREE_BG} !important;
        }}
        [data-testid="stAlertContentInfo"] p {{
            color: {THEME.LINK} !important;
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


# Ta sama rodzina co w CSS (np. do inline HTML w streamlit_app)
FONT_FAMILY_CSS = css_font_family()

# Eksport help_content dla sekcji (stopka strony / sidebar gdy używane)
GLOSSARY = hc.GLOSSARY
SECTION_VALIDATION = hc.SECTION_VALIDATION
SECTION_REFERENCES = hc.SECTION_REFERENCES
