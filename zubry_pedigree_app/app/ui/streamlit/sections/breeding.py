"""Zakładka: plan hodowlany (placeholder)."""

from __future__ import annotations

import streamlit as st

from app.ui import help_content as hc
from app.ui.streamlit import common as sc


def section_breeding_placeholder() -> None:
    st.info(
        "Plan hodowlany — ta sekcja jest synchronizowana z wersją desktop (Tk) i wymaga dopracowania logiki hodowlanej."
    )
    sc.help_expander("Plan hodowlany (Tk vs Streamlit)", hc.SECTION_BREEDING)
