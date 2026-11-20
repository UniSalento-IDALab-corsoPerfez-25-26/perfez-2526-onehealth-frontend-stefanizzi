"""Provide the latest available data by source, with its own date range."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.data_quality_catalog import CATALOG
from app.dashboard.weather_context import weather_note

ROOT = Path(__file__).resolve().parents[2]
FIRST_YEAR = 2024
RECENT_DATASETS = {
    "Esposizioni annuali ARPA": "Esposizioni storiche con controlli di qualità",
    "Misure di stazione ARPA 2026 · primo semestre": "Misure RRQA del primo semestre 2026",
    "Meteorologia annuale ERA5-Land": "Meteorologia storica",
    "Meteorologia ERA5-Land 2026 · parziale": "Meteorologia ASL 2026 parziale",
    "Popolazione per ASL": "Popolazione ASL aggiornata",
    "Popolazione per comune": "Popolazione comunale aggiornata",
    "Ricoveri per ASL": "Ricoveri HFA",
    "Mortalità HFA per ASL": "Mortalità HFA",
    "Decessi comunali ISTAT": "Decessi comunali ISTAT",
    "Incidenza e prevalenza comunali": "Incidenza e prevalenza delle quattro patologie",
}
CATALOG_BY_NAME = {item.name: item for item in CATALOG}


@st.cache_data(max_entries=len(RECENT_DATASETS), show_spinner=False)
def read_recent_source(path: Path, modified_ns: int) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False) if path.suffix == ".csv" else pd.read_parquet(path)


def source_frame(path: Path) -> pd.DataFrame:
    return read_recent_source(path, path.stat().st_mtime_ns)


def year_series(frame: pd.DataFrame) -> pd.Series:
    if "measurement_date" in frame:
        return pd.to_datetime(frame["measurement_date"], errors="coerce").dt.year
    return pd.to_numeric(frame["year"] if "year" in frame else frame["anno"], errors="coerce")


def period_label(frame: pd.DataFrame, years: pd.Series) -> str:
    if {"period_start", "period_end"}.issubset(frame):
        dates = pd.to_datetime(frame["period_start"], errors="coerce"), pd.to_datetime(frame["period_end"], errors="coerce")
    elif "measurement_date" in frame:
        dates = (pd.to_datetime(frame["measurement_date"], errors="coerce"),) * 2
    elif "periodo" in frame and "mese" in frame:
        months = pd.to_datetime(frame["periodo"], errors="coerce")
        first, last = months.min(), months.max()
        if pd.notna(first) and pd.notna(last):
            return f"{first:%m/%Y} – {last:%m/%Y}"
        dates = (months,) * 2
    else:
        first, last = years.min(), years.max()
        if pd.isna(first) or pd.isna(last):
            return "—"
        return str(int(first)) if first == last else f"{int(first)}–{int(last)}"
    first, last = dates[0].min(), dates[1].max()
    return f"{first:%d/%m/%Y} – {last:%d/%m/%Y}" if pd.notna(first) and pd.notna(last) else "—"


def render_recent_data() -> None:
    st.subheader("Dati recenti dal 2024")
    st.write("Controlla fino a quando sono disponibili i dati di ciascuna fonte. Scegli un archivio e un territorio per vedere le righe disponibili e, per i decessi, il grafico mensile del comune.")
    st.caption("Ogni fonte ha il proprio periodo di disponibilità. Le misure e la meteorologia del 2026 coprono periodi parziali. I decessi comunali ISTAT possono essere revisionati.")
    overview = []
    available = {}
    for label, name in RECENT_DATASETS.items():
        dataset = CATALOG_BY_NAME[name]
        path = ROOT / dataset.path
        try:
            data = source_frame(path)
            years = year_series(data)
        except FileNotFoundError:
            overview.append({"Archivio": label, "Periodo disponibile": "File assente"})
            continue
        except (OSError, ValueError, KeyError):
            overview.append({"Archivio": label, "Periodo disponibile": "File non leggibile o schema variato"})
            continue
        recent = data.loc[years.ge(FIRST_YEAR)].copy()
        overview.append({"Archivio": label, "Fonte": dataset.source, "Periodo disponibile": period_label(data, years),
                         "Righe dal 2024": len(recent)})
        if not recent.empty:
            available[label] = (dataset, recent)
    st.dataframe(pd.DataFrame(overview), hide_index=True, use_container_width=True)

    if not available:
        st.info("Nessuna osservazione dal 2024 disponibile in questa installazione.")
        return

    selected = st.selectbox("Archivio da consultare", list(available))
    dataset, frame = available[selected]
    note = weather_note(dataset)
    if note:
        st.caption(note)
    years = year_series(frame)
    columns = st.columns(2)
    year = columns[0].selectbox("Anno", ["Tutti", *sorted(int(year) for year in years.dropna().unique())], key=f"recent_year_{selected}")
    if year != "Tutti":
        frame = frame.loc[years.eq(year)]
    location = "Tutti"
    if dataset.territory and dataset.territory in frame:
        territory = frame[dataset.territory].astype("string")
        label = {"asl": "ASL", "source_station_id": "Stazione"}.get(dataset.territory, "Codice comune")
        location = columns[1].selectbox(label, ["Tutti", *sorted(territory.dropna().unique())], key=f"recent_territory_{selected}")
        if location != "Tutti":
            frame = frame.loc[territory.eq(location).fillna(False)]
    if "pollutant_code" in frame:
        pollutant = st.selectbox("Inquinante", ["Tutti", *sorted(frame["pollutant_code"].dropna().unique())], key=f"recent_pollutant_{selected}")
        if pollutant != "Tutti":
            frame = frame.loc[frame["pollutant_code"].eq(pollutant)]
    st.caption(f"Periodo della selezione: {period_label(frame, year_series(frame))} · {len(frame):,} righe. La tabella mostra al massimo 500 righe.")
    if "decessi_totali" in frame and "periodo" in frame and location != "Tutti":
        fig = px.line(frame.sort_values("periodo"), x="periodo", y="decessi_totali", markers=True,
                      labels={"periodo": "Mese", "decessi_totali": "Decessi osservati"})
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(frame.head(500), hide_index=True, use_container_width=True)
