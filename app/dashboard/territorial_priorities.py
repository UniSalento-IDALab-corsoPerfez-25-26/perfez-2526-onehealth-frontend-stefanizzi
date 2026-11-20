"""Streamlit screen for territorial screening via the OneHealthAI AI service."""

import os

import requests
import pandas as pd
import streamlit as st

API = os.environ.get("ONEHEALTH_DSS_API_URL", "http://127.0.0.1:8007").rstrip("/")
POLLUTANTS = {
    "no2_mean_value": "NO₂",
    "o3_mean_value": "O₃",
    "pm10_mean_value": "PM₁₀",
    "pm2_5_mean_value": "PM₂.₅",
}
WEIGHTS = (25, 50, 75)


def fetch(endpoint, **params):
    try:
        response = requests.get(f"{API}/v1/dss/{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        st.error("Servizio DSS non disponibile. Verifica l’indirizzo del backend e riprova.")
        return None


def number(value, decimals=2):
    return "—" if value is None else f"{value:.{decimals}f}".replace(".", ",")


def territorial_filters() -> tuple[str, int] | None:
    options = fetch("options")
    if not options:
        return None
    by_code = {item["code"]: item for item in options["indicators"] if item["years"]}
    if not by_code:
        st.info("Il dataset non contiene indicatori consultabili.")
        return None
    left, right = st.columns(2)
    with left:
        indicator = st.selectbox(
            "Indicatore sanitario", list(by_code), index=list(by_code).index("BPCO") if "BPCO" in by_code else 0,
            format_func=lambda code: by_code[code]["label"], key="territorial_indicator",
        )
    with right:
        year = st.selectbox("Anno", sorted(by_code[indicator]["years"], reverse=True), key="territorial_year")
    return indicator, year


def render_territorial_priorities():
    st.title("Priorità territoriali")
    st.write("Confronta le ASL pugliesi per indicatore e anno. Cambia il peso ambientale per vedere come varia la graduatoria e seleziona un’ASL per esaminare i contributi sanitari e ambientali.")
    st.caption("Questa graduatoria confronta la situazione dell’anno selezionato. "
               "I pesi sono criteri di screening modificabili, non effetti sanitari stimati. "
               "Il meteo non entra nel punteggio. "
               "Per gli andamenti dal 2010 apri Research Panel → Serie storiche.")
    with st.expander("Prima visita? Prova il confronto con Lecce"):
        st.markdown(
            "1. Scegli **Broncopneumopatia cronica ostruttiva (BPCO)** e **2024**. "
            "La prevalenza indica quante persone convivono con la patologia ogni 1.000 residenti della fascia considerata.\n"
            "2. Imposta **Peso ambientale** al **50%**. In questo scenario salute e ambiente contano allo stesso modo. "
            "Il punteggio, su 100, serve a scegliere quali territori approfondire. La prima posizione indica "
            "l’ASL con il punteggio più alto fra quelle confrontate.\n"
            "3. In **ASL da esaminare**, scegli **Lecce**. Leggi i punti sanitari e ambientali: la loro somma dà il punteggio.\n"
            "4. Cambia il peso al **25%** e poi al **75%**. Confronta sia i punti sia la posizione: "
            "il peso cambia per tutte le ASL contemporaneamente."
        )
    selection = territorial_filters()
    if selection is None:
        return
    indicator, year = selection
    if year == 2024:
        st.caption("Dati osservati 2024. La prevalenza è disponibile per i residenti dai 40 anni in su, aggregati per ASL. Il tasso standardizzato richiede il dettaglio per fascia d’età.")
    weight = st.selectbox("Peso ambientale", WEIGHTS, index=1, format_func=lambda w: f"{w}%")

    data = fetch("scenarios", indicator_code=indicator, year=year)
    if data is None:
        return
    if data["status"] == "NO_DATA":
        st.info("Nessuna osservazione disponibile per l’indicatore e l’anno selezionati.")
        return

    scenarios = {int(w): {row["asl"]: row for row in rows} for w, rows in data["scenarios"].items()}
    selected = scenarios[weight]
    st.subheader("Graduatoria e sensibilità ai pesi")
    st.caption(f"Scenario selezionato: salute {100-weight}% · ambiente {weight}%. I ranghi si riferiscono alle ASL disponibili.")
    table = []
    for asl, row in selected.items():
        table.append({
            "ASL": asl,
            "Punteggio /100": row["score"],
            "Posizione attiva": row["rank"],
            "Sanità · punti": row["health_points"],
            "Ambiente · punti": row["environment_points"],
            **{f"Posizione con ambiente {w}%": scenarios[w].get(asl, {}).get("rank") for w in WEIGHTS},
            "Inquinanti disponibili": f'{row["available_pollutants"]}/4',
        })
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch", column_config={
        "Punteggio /100": st.column_config.NumberColumn(format="%.2f"),
        "Sanità · punti": st.column_config.NumberColumn(format="%.2f"),
        "Ambiente · punti": st.column_config.NumberColumn(format="%.2f"),
    })
    if any(row["available_pollutants"] < 4 or row["score"] is None for row in selected.values()):
        st.info("La copertura varia tra ASL. Il punteggio ambientale usa i percentili degli inquinanti disponibili. Se una componente è assente, il servizio lascia punteggio e posizione mancanti.")

    st.subheader("Spiegazione per ASL")
    asl = st.selectbox("ASL da esaminare", list(selected), index=list(selected).index("Taranto") if "Taranto" in selected else 0)
    item = selected[asl]
    m1, m2, m3 = st.columns(3)
    m1.metric("Punteggio su 100", number(item["score"]))
    m2.metric("Punti sanitari", number(item["health_points"]))
    m3.metric("Punti ambientali", number(item["environment_points"]))
    if item["score"] is not None:
        st.caption("Somma dei contributi ponderati. I valori visualizzati sono arrotondati.")
    r1, r2 = st.columns(2)
    r1.metric("Prevalenza grezza per 1.000", number(item["crude_rate"]))
    r2.metric("Prevalenza standardizzata per 1.000", number(item["standardized_rate"]))
    st.caption(f"La graduatoria usa la prevalenza grezza. La standardizzazione per età usa la popolazione interna delle sei ASL nel {data['reference_year']} (residenti di almeno {data['age_minimum']} anni).")
    st.caption(f"Fonte sanitaria: AReSS e denominatori ISTAT. Casi: {item['cases'] if item['cases'] is not None else '—'} · Popolazione: {item['population'] if item['population'] is not None else '—'}. Fonte ambientale: ARPA Puglia.")
    st.dataframe(pd.DataFrame([
        {"Inquinante": label, "Concentrazione media (µg/m³)": item["pollutants"][key],
         "Disponibilità misure nell’archivio (%)": data["coverage"].get(asl, {}).get(key)}
        for key, label in POLLUTANTS.items()
    ]), hide_index=True, width="stretch")
    st.caption(f"Qualità dell’integrazione: {item['integration_quality_status'] or '—'}. Il simbolo — o una cella vuota indica un valore non disponibile.")
