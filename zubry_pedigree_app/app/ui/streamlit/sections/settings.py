"""
Drobne ustawienia bieżącej pracy w przeglądarce (np. dodatkowe podpisy przy wykresach).
"""

from __future__ import annotations

import streamlit as st

from app.ui import help_content as hc
from app.ui.streamlit import common as sc


def section_settings() -> None:
    st.markdown("### Ustawienia (sesja)")
    sc.help_expander("Ustawienia sesji Streamlit", hc.SECTION_SETTINGS)
    st.caption("W Streamlit ustawienia są trzymane w tej sesji przeglądarki.")
    st.checkbox(
        "Domyślnie: rozwinięte bloki „Interpretacja wykresu” w zakładce Populacja",
        value=True,
        key="st_verbose_pop_captions",
    )
