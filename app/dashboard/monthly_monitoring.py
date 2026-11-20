"""Monthly monitoring of observed mortality and RRQA measurements."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parents[2] / "data/processed/one_health/operational"
MONTHS = dict(enumerate((
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre",
), start=1))
ISTAT_SOURCE = "https://www.istat.it/notizia/dati-di-mortalita-cosa-produce-listat/"


def render_monthly_monitoring() -> None:
    st.subheader("Monitoraggio mensile 2026")
    st.write(
        "Scegli provincia, mese e inquinante. I grafici mostrano le concentrazioni ambientali "
        "e il confronto dei decessi osservati con gli stessi mesi del 2025."
    )
    try:
        deaths = pd.read_csv(ROOT / "mortalita_mensile_province_2025_2026.csv")
        air = pd.read_csv(ROOT / "rrqa_mensile_province_2026.csv")
    except FileNotFoundError:
        st.info("Copia i due file mensili nella cartella operativa indicata nelle istruzioni.")
        return

    st.caption("Leggi prima i decessi dello stesso mese nei due anni, poi la concentrazione e la copertura "
               "delle stazioni. Cambiare inquinante aggiorna la parte sull’aria. I decessi comprendono tutte le cause.")
    a, b, c = st.columns(3)
    province = a.selectbox("Provincia", sorted(deaths["province"].unique()), key="monthly_province")
    month = b.selectbox("Mese", list(MONTHS), index=5, format_func=MONTHS.__getitem__, key="monthly_month")
    pollutant = c.selectbox("Inquinante", ["NO2", "O3", "PM10", "PM2.5"], key="monthly_pollutant")
    health = deaths.loc[deaths["province"].eq(province)].sort_values("month")
    current = health.loc[health["month"].eq(month)].iloc[0]
    a, b, c = st.columns(3)
    a.metric(f"Decessi · {MONTHS[month]} 2026", int(current["deaths_2026"]))
    b.metric(f"Decessi · {MONTHS[month]} 2025", int(current["deaths_2025"]))
    c.metric("Differenza rispetto al 2025", f"{current['deaths_2026'] - current['deaths_2025']:+d}")

    st.markdown("#### Mortalità totale")
    st.caption("Decessi per provincia di residenza. I dati del 2025 e del 2026 sono provvisori. Il confronto usa conteggi dello stesso mese nei due anni.")
    comparison = health.rename(columns={"deaths_2025": "2025", "deaths_2026": "2026"})
    comparison["Mese"] = comparison["month"].map(MONTHS)
    plot = px.line(comparison, x="Mese", y=["2025", "2026"], markers=True,
                   labels={"value": "Decessi osservati", "variable": "Anno"})
    st.plotly_chart(plot, use_container_width=True)
    st.markdown(f"[Fonte ISTAT · Rilascio del 16 novembre 2026]({ISTAT_SOURCE})")

    st.markdown("#### Qualità dell’aria")
    st.caption(
        "Media delle concentrazioni mensili delle stazioni RRQA con almeno un valore disponibile. "
        "La copertura divide i giorni-stazione con valore per i giorni di calendario attesi "
        "per le stazioni presenti nell’archivio del mese."
    )
    readings = air.loc[air["province"].eq(province) & air["pollutant_code"].eq(pollutant)].set_index("month")
    readings = readings.reindex(MONTHS)
    readings["Mese"] = readings.index.map(MONTHS)
    selected = readings.loc[month]
    if pd.isna(selected["mean_value"]):
        st.info(f"Nessun riepilogo RRQA per {MONTHS[month].lower()} nella copia locale.")
    else:
        a, b, c = st.columns(3)
        a.metric(f"{pollutant} · {MONTHS[month]}", f"{selected['mean_value']:.1f} µg/m³")
        b.metric("Stazioni con misure", int(selected["stations"]))
        c.metric("Copertura giorni-stazione", f"{selected['coverage_pct']:.1f}%")
    plot = px.line(readings, x="Mese", y="mean_value", markers=True,
                   labels={"mean_value": "Concentrazione media (µg/m³)"})
    plot.update_xaxes(type="category", categoryorder="array", categoryarray=list(MONTHS.values()))
    st.plotly_chart(plot, use_container_width=True)
    st.caption("I mesi senza misure restano vuoti. I due grafici descrivono andamenti distinti e servono a orientare gli approfondimenti.")
