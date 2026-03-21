"""Zakładka: lista osobników."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ui import help_content as hc
from app.ui.streamlit import common as sc


def section_persons(df_std: pd.DataFrame) -> None:
    st.markdown("### Osobniki")
    sc.help_expander("Osobniki — jak czytać tabelę", hc.SECTION_PERSONS)
    lm = st.session_state.get("line_memberships") or {}
    base = df_std.copy()
    base["id"] = base["id"].astype(str)

    def _row_line(pid: str) -> str:
        m = lm.get(pid)
        if m is None:
            return "NA"
        return f"S:{m.sire_founder_id or 'NA'} / D:{m.dam_founder_id or 'NA'}"

    base["linia (sire/dam)"] = base["id"].map(lambda x: _row_line(str(x)))

    sort_col = st.selectbox("Sortuj po kolumnie", options=list(base.columns), index=0, key="p_sort")
    asc = st.toggle("Rosnąco (A→Z / małe→duże)", value=True, key="p_asc")
    preview_n = st.slider("Liczba wierszy podglądu", 25, 500, 250, 25, key="p_n")
    view = base.sort_values(by=[sort_col], ascending=bool(asc)).head(preview_n)
    st.dataframe(view, width="stretch", height=420)
