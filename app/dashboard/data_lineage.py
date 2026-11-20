"""Display project provenance for the artifacts users inspect in the dashboard."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app.dashboard.data_quality_catalog import CATALOG

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "data/manifests/one_health/latest_manifest.json"
RESEARCH_CATALOG = "reports/research/master_research_panel_v1/source_catalog.json"


def read_metadata(relative_path: str, default):
    try:
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def render_data_lineage() -> None:
    st.subheader("Tracciabilità del dato")
    st.write(
        "Segui il percorso dalle fonti ai file usati dalla dashboard. Scegli un’area e un archivio per verificare "
        "quale file è presente e quali informazioni sulla sua origine sono state registrate."
    )
    group = st.selectbox("Area", list(dict.fromkeys(item.group for item in CATALOG)), key="lineage_group")
    candidates = {item.name: item for item in CATALOG if item.group == group}
    item = candidates[st.selectbox("Archivio", list(candidates), key="lineage_dataset")]
    path = ROOT / item.path
    st.caption(f"Fonti: {item.source} · Frequenza: {item.frequency}")
    st.code(item.path, language=None)
    if path.is_file():
        try:
            with path.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            st.caption(f"SHA-256 del file presente: {digest}")
        except OSError:
            st.warning("File presente, ma non leggibile.")
    else:
        st.warning("File assente in questa installazione.")

    if item.name == "Estensione priorità 2024":
        st.markdown("**Percorso dei dati 2024**")
        st.write("L’aggregazione dei casi e dei denominatori comunali è stata verificata sui totali ASL del 2023. I totali 2024 sono poi stati collegati alle esposizioni ARPA qualificate per ASL.")
        st.dataframe(pd.DataFrame({"File di ingresso": [
            "data/processed/one_health/master_research_panel_v1/master_health_municipal_2020_2024.csv",
            "data/processed/demography/population_municipality_2024_2026.parquet",
            "data/processed/one_health/research/environmental_exposure_2010_2025_QC_v1.parquet",
            "data/processed/one_health/one_health_master_2021_2023.parquet",
        ], "Uso": ["Casi e denominatori 40+", "Corrispondenza comune–ASL", "Esposizioni annuali", "Verifica di coerenza 2023"]}),
            hide_index=True, width="stretch")
    elif group == "DSS":
        st.markdown("**Percorso dei dati ASL**")
        st.markdown("Dati AReSS, ISTAT e ARPA Puglia → normalizzazione e aggregazione per ASL → integrazione per anno → Master Dataset → quadro e graduatoria.")
        manifest = read_metadata(MANIFEST, {})
        output = manifest.get("dataset", {})
        if output.get("path"):
            st.caption(f"Il manifesto della pipeline riguarda {output['path']}, prodotto della fase di integrazione precedente alla costruzione del Master Dataset.")
            st.caption(f"Versione della pipeline registrata: {manifest.get('pipeline_version', '—')} · Generato (UTC): {manifest.get('generated_at_utc', '—')}")
            st.dataframe(pd.DataFrame([
                {"File di ingresso": f.get("path"), "SHA-256 registrato": f.get("sha256")}
                for f in manifest.get("source_files", [])
            ]), hide_index=True, width="stretch")
        else:
            st.info("Il manifesto della pipeline non è disponibile in questa installazione.")
    else:
        st.markdown("**Percorso dei dati di ricerca**")
        st.markdown("Archivi delle fonti → preparazione e controlli → prodotti per scala territoriale e temporale → consultazione o analisi.")
        catalog = read_metadata(RESEARCH_CATALOG, [])
        entry = next((entry for entry in catalog if entry.get("path") == item.path), None)
        if entry and entry.get("sha256"):
            st.caption(f"SHA-256 registrato nel catalogo di ricerca: {entry['sha256']}")
        else:
            st.caption("Per questo file non risulta un checksum registrato nel catalogo di ricerca consultato.")
