from __future__ import annotations

import re
from pathlib import Path
import streamlit as st

from app.data.dataset_loader import load_dataset_from_bytes
from app.data.dataset_loader import load_default_bison_report
from app.pedigree.ancestor_pedigree import (
    build_people_map,
    ensure_people_for_nodes,
    get_ancestor_levels_and_edges,
)
from app.visualizations.ancestor_plot import plot_ancestor_pedigree
from app.analytics.inbreeding_wright import wright_inbreeding_F


def run_streamlit_direct() -> None:
    st.set_page_config(page_title="WisentPedigree Pro+", layout="wide")
    st.title("WisentPedigree Pro+")

    # Logo (umieszczone pod tytułem).
    _logo_path = Path(__file__).resolve().parents[2] / "logo.png"
    if _logo_path.exists():
        try:
            st.image(str(_logo_path), width=90)
        except Exception:
            pass

    @st.cache_data(show_spinner=False)
    def _load_default_cached():
        return load_default_bison_report()

    default_loaded = False
    df_std_default = None
    info_default = None
    try:
        df_std_default, info_default = _load_default_cached()
        default_loaded = True
    except Exception as e:
        default_loaded = False
        default_error = str(e)
    else:
        default_error = ""

    uploaded = st.file_uploader("Wgraj plik CSV lub Excel", type=["csv", "xlsx", "xls"])
    if uploaded is None:
        if not default_loaded or df_std_default is None:
            if default_error:
                st.warning(f"Nie udało się wczytać domyślnej bazy: {default_error}")
            st.info("Wgraj plik, a potem wygenerujemy wykres rodowodu (przodków).")
            return
        df_std, info = df_std_default, info_default
        st.success(f"Wczytano domyślną bazę: {info.rows} wierszy, {info.columns} kolumn.")
    else:
        try:
            data = uploaded.read()
            filename = uploaded.name
            df_std, info = load_dataset_from_bytes(data=data, filename=filename)
        except Exception as e:
            st.error(f"Błąd wczytywania: {e}")
            return

    people = build_people_map(df_std)

    # Jeśli to była domyślna baza, komunikat był wyżej; nie dublujemy.
    if uploaded is not None:
        st.success(f"Wczytano: {info.rows} wierszy, {info.columns} kolumn.")
    st.dataframe(df_std.head(250), use_container_width=True)

    # Informacja o zakresie ID (Number) w wczytanej bazie.
    ids = df_std["id"].dropna().astype(str) if not df_std.empty else df_std.get("id", [])
    if ids is not None and len(ids) > 0:
        def _id_sort_key(s: str) -> tuple[int, str]:
            m = re.match(r"^(\\d+)([A-Za-z]*)$", s)
            if not m:
                return (10**30, s)
            return (int(m.group(1)), m.group(2) or "")

        min_id = min(ids.tolist(), key=_id_sort_key)
        max_id = max(ids.tolist(), key=_id_sort_key)
        st.caption(f"Zakres ID (Number): min {min_id}, max {max_id}")

    if not df_std.empty:
        with_parents = df_std[df_std["father_id"].notna() | df_std["mother_id"].notna()]
        default_row = with_parents.iloc[0] if not with_parents.empty else df_std.iloc[0]
        default_id = str(default_row["id"])
    else:
        default_id = ""

    tab_anc, tab_inb = st.tabs(["Przodkowie", "Inbred (F)"])

    with tab_anc:
        person_id_anc = st.text_input("ID (Number)", value=default_id, key="anc_id")
        depth_anc = st.slider("Max pokoleń", min_value=0, max_value=10, value=4, step=1, key="anc_depth")
        readable_anc = st.checkbox("Tryb czytelny (mniej etykiet)", value=True, key="anc_readable")

        if st.button("Generuj przodków", type="primary", key="anc_btn"):
            if not person_id_anc.strip():
                st.error("Podaj ID (Number).")
                return
            if str(person_id_anc).strip() not in people:
                st.error("Nie ma takiego ID w wczytanych danych.")
                return

            levels, edges = get_ancestor_levels_and_edges(
                person_id=str(person_id_anc).strip(), depth=int(depth_anc), people=people
            )
            if not levels:
                st.error("Nie znaleziono ID lub brak przodków w podanym limicie.")
                return

            people_all = ensure_people_for_nodes(levels=levels, people=people)
            fig = plot_ancestor_pedigree(
                person_id=str(person_id_anc).strip(),
                levels=levels,
                edges=edges,
                people=people_all,
                readable_mode=bool(readable_anc),
            )

            if len(levels) <= 1 or len(edges) == 0:
                person = people.get(str(person_id_anc).strip())
                st.warning(
                    "W tym ID nie znaleźliśmy przodków w podanym limicie (brak krawędzi). "
                    "Jeśli `Father` i `Mother` są nieznane (brak ID rodziców), traktujemy osobnika jako founder i w wykresie pojawia się tylko on."
                    f" Father: {getattr(person, 'father_id', None)}"
                    f" Mother: {getattr(person, 'mother_id', None)}"
                    f" Węzły: {len(levels)}, krawędzie: {len(edges)}."
                )

            st.pyplot(fig, use_container_width=True)

    with tab_inb:
        person_id_inb = st.text_input("ID (Number)", value=default_id, key="inb_id")
        depth_inb = st.slider("Max pokoleń", min_value=0, max_value=10, value=4, step=1, key="inb_depth")
        unbounded_inb = st.checkbox("Bez ograniczenia (do founderów)", value=False, key="inb_unbounded")

        if st.button("Policz F (Wright)", type="primary", key="inb_btn"):
            if not person_id_inb.strip():
                st.error("Podaj ID (Number).")
                return
            if str(person_id_inb).strip() not in people:
                st.error("Nie ma takiego ID w wczytanych danych.")
                return

            if unbounded_inb:
                f_res = wright_inbreeding_F(
                    person_id=str(person_id_inb).strip(),
                    people=people,
                    max_generations_back=None,
                )
            else:
                f_res = wright_inbreeding_F(
                    person_id=str(person_id_inb).strip(),
                    people=people,
                    max_generations_back=int(depth_inb),
                )
            st.subheader(f"Inbred (Wright F): {f_res.F:.6f}")
            st.caption(
                "Jak liczony jest inbred (Wright F): "
                "F(i)=Phi(sire(i), dam(i)); Phi liczymy rekurencyjnie po ścieżkach rodowodowych. "
                "Brak rodziców traktujemy jako founder (Phi=0 dla par). "
                "W trybie bez ograniczenia pokoleń schodzimy aż do founderów w dostępnych danych."
            )

            st.caption(
                f"max pokoleń (ścieżki n1+n2) użyte w obliczeniach={f_res.used_generations}. "
                f"Father={f_res.father_id} ({f_res.father_name}); "
                f"Mother={f_res.mother_id} ({f_res.mother_name})."
            )

            # --- Wykres: diagnostyka F vs max pokoleń ---
            try:
                import matplotlib.pyplot as plt
            except Exception:
                plt = None

            if plt is not None:
                # Wykres jest diagnostyczny; ograniczamy zakres dla wydajności.
                max_trace_depth = min(20, int(f_res.used_generations)) if unbounded_inb else int(depth_inb)
                depths = list(range(0, max_trace_depth + 1))
                Fs = []
                for d in depths:
                    Fs.append(
                        wright_inbreeding_F(
                            person_id=str(person_id_inb).strip(),
                            people=people,
                            max_generations_back=int(d),
                        ).F
                    )

                fig, ax = plt.subplots(figsize=(7.5, 3.6))
                ax.plot(depths, Fs, marker="o", linewidth=2, color="#2a6fdb")
                ax.set_title(f"Inbred (Wright F) - diagnostyka (ID {person_id_inb})")
                ax.set_xlabel("max pokoleń")
                ax.set_ylabel("F")
                ax.grid(True, alpha=0.25)

                if unbounded_inb and f_res.used_generations > max_trace_depth:
                    ax.annotate(
                        f"F unbounded={f_res.F:.3f}\n(dopóki do founderów: {f_res.used_generations})",
                        xy=(max_trace_depth, Fs[-1] if Fs else 0.0),
                        xytext=(10, 10),
                        textcoords="offset points",
                        fontsize=9,
                        ha="left",
                        va="bottom",
                    )

                st.pyplot(fig, use_container_width=True)

            if abs(f_res.F) < 1e-12:
                st.caption(
                    "W tym limicie pokoleń wynik wyszedł 0 (brak współpochodzenia rodziców w zakresie)."
                )


if __name__ == "__main__":
    run_streamlit_direct()

