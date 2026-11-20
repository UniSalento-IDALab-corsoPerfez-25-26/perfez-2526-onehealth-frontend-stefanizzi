"""Show the health and environment inputs used for territorial screening."""

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.territorial_priorities import POLLUTANTS, fetch, territorial_filters

QUALITY = {
    "VALID": "Valido",
    "VALID_WITH_PARTIAL_METEO": "Valido con meteo parziale",
    "VALID_WITHOUT_METEO": "Valido senza meteo",
}


def render_territorial_overview() -> None:
    st.title("Quadro territoriale")
    st.write(
        "Consulta i dati sanitari e ambientali usati per confrontare le ASL pugliesi. "
        "Scegli lo stesso indicatore e anno della graduatoria e filtra per ASL per leggere i dati di partenza e la loro copertura."
    )
    st.caption("Inizia dalla voce Salute: i casi indicano quanti residenti hanno la patologia. "
               "La prevalenza li rapporta alla popolazione e permette di confrontare ASL di dimensioni diverse. "
               "Nella voce Ambiente trovi le concentrazioni usate per lo stesso anno.")
    selection = territorial_filters()
    if selection is None:
        return
    indicator, year = selection
    if year == 2024:
        st.caption("Dati osservati 2024. La prevalenza è disponibile per i residenti dai 40 anni in su, aggregati per ASL. Il tasso standardizzato richiede il dettaglio per fascia d’età.")
    data = fetch("scenarios", indicator_code=indicator, year=year)
    if data is None:
        return
    rows = data["scenarios"]["50"]
    if not rows:
        st.info("Nessuna osservazione per l’indicatore e l’anno selezionati.")
        return
    location = st.selectbox("ASL", ["Tutte", *sorted(row["asl"] for row in rows)], key="overview_asl")
    selected = [row for row in rows if location == "Tutte" or row["asl"] == location]

    st.subheader("Salute")
    st.caption("La prevalenza grezza è calcolata sui casi AReSS e sulla popolazione ISTAT di almeno 40 anni. La standardizzazione tiene conto della diversa struttura per età delle ASL.")
    health = pd.DataFrame([
        {"ASL": row["asl"], "Casi": row["cases"], "Popolazione": row["population"],
         "Prevalenza grezza per 1.000": row["crude_rate"], "Prevalenza standardizzata per 1.000": row["standardized_rate"]}
        for row in selected
    ])
    st.plotly_chart(px.bar(health, x="ASL", y="Prevalenza grezza per 1.000"), width="stretch")
    st.dataframe(health, hide_index=True, width="stretch")

    st.subheader("Ambiente")
    st.caption("Scegli un inquinante per confrontare le concentrazioni medie annue ARPA Puglia. La copertura è la percentuale di giorni validi sul totale dei giorni attesi delle stazioni incluse. Le medie derivano dai file originali ARPA ricostruiti.")
    pollutant = st.selectbox("Inquinante", list(POLLUTANTS), format_func=POLLUTANTS.__getitem__, key="overview_pollutant")
    environment = pd.DataFrame([
        {"ASL": row["asl"], "Concentrazione media (µg/m³)": row["pollutants"].get(pollutant),
         "Disponibilità (%)": data["coverage"].get(row["asl"], {}).get(pollutant)}
        for row in selected
    ])
    st.plotly_chart(px.bar(environment, x="ASL", y="Concentrazione media (µg/m³)"), width="stretch")
    st.dataframe(environment, hide_index=True, width="stretch")

    st.subheader("Meteo e qualità dell’integrazione")
    st.caption("I contatori si riferiscono alle ASL selezionate. La copertura meteo descrive il Master Dataset e può differire da quella delle serie meteorologiche disponibili in altri archivi.")
    if "weather" not in data:
        st.info("Per visualizzare la copertura meteo, riavvia il servizio AI con la versione aggiornata.")
        return
    weather_rows = []
    for row in selected:
        asl = row["asl"]
        meta = data["weather"].get(asl, {})
        status = row["integration_quality_status"]
        weather_rows.append({
            "ASL": asl, "Meteo presente": meta.get("meteo_available"), "Anno completo": meta.get("meteo_is_full_year"),
            "Copertura meteo (%)": meta.get("meteo_year_coverage_percent"), "Stato integrazione": QUALITY.get(status, status),
        })
    weather = pd.DataFrame(weather_rows)
    a, b, c = st.columns(3)
    a.metric("ASL con meteo", int(weather["Meteo presente"].eq(True).sum()))
    b.metric("ASL senza meteo", int(weather["Meteo presente"].eq(False).sum()))
    c.metric("ASL con anno completo", int(weather["Anno completo"].eq(True).sum()))
    if weather["Meteo presente"].isna().any():
        st.caption("Per alcune ASL lo stato della copertura meteo non è disponibile.")
    counts = weather["Stato integrazione"].fillna("Non disponibile").value_counts().rename("ASL").rename_axis("Stato").reset_index()
    st.plotly_chart(px.bar(counts, x="Stato", y="ASL"), width="stretch")
    st.dataframe(weather, hide_index=True, width="stretch")
