"""
Generowanie dłuższych opisów tekstowych (raportów) dla osobnika lub populacji do skopiowania lub zapisu.
"""

from __future__ import annotations

import streamlit as st

from app.analytics.population_genetics import compute_population_genetics_stats
from app.ui import help_content as hc
from app.ui.streamlit import common as sc


def section_reports() -> None:
    st.markdown("### Raporty")
    sc.help_expander("Raporty — co zawierają", hc.SECTION_REPORTS)
    st.caption("Podgląd tekstowy; pełny eksport DOCX/PDF jest w wersji Tk.")
    df_std = st.session_state.get("df_std")
    people = st.session_state.get("people")
    rep = st.session_state.get("validation_report")
    lines = ["WisentPedigree Pro+ — raport (Streamlit)", "", f"Źródło danych: {st.session_state.get('source', '-')}", ""]
    if rep is not None:
        lines.append("=== Walidacja ===")
        lines.append(rep.to_text())
        lines.append("")
    if df_std is not None and people:
        try:
            stats = compute_population_genetics_stats(
                df_std=df_std,
                people=people,  # type: ignore[arg-type]
                max_generations_back=4,
                calc_f=True,
                calc_completeness=True,
                calc_founders=True,
                calc_lines=True,
            )
            lines.append("=== Populacja (skrót) ===")
            lines.append(f"n={stats.n}, mean F={stats.inbreeding.mean_F:.6f}, mean PCI={stats.completeness.mean_PCI:.4f}")
        except Exception as e:
            lines.append(f"Błąd metryk: {e}")
    text = "\n".join(lines)
    st.text_area("Podgląd", text, height=320)
    st.download_button("Pobierz raport (.txt)", data=text, file_name="raport_wisent.txt", mime="text/plain")
