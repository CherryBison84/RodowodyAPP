"""Sekcje UI Streamlit (jedna zakładka = jeden moduł)."""

from app.ui.streamlit.sections.analysis import section_analysis_inbred, section_analysis_mating
from app.ui.streamlit.sections.breeding import section_breeding_placeholder
from app.ui.streamlit.sections.loading import section_loading
from app.ui.streamlit.sections.persons import section_persons
from app.ui.streamlit.sections.pedigree import section_pedigree
from app.ui.streamlit.sections.population import section_population
from app.ui.streamlit.sections.reports import section_reports
from app.ui.streamlit.sections.settings import section_settings

__all__ = [
    "section_analysis_inbred",
    "section_analysis_mating",
    "section_breeding_placeholder",
    "section_loading",
    "section_persons",
    "section_pedigree",
    "section_population",
    "section_reports",
    "section_settings",
]
