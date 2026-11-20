"""Display the archived temporal XGBoost evaluation and TreeSHAP contributions."""

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


REPORTS = Path(__file__).resolve().parents[2] / "reports/research/shap_temporale"
OUTCOMES = {"hospital_discharge_copd": "Ricoveri per BPCO", "mortality_copd": "Mortalità per BPCO"}
POLLUTANTS = {"NO2": "NO₂", "PM25": "PM₂,₅"}
VARIABLES = {
    "value": "Indicatore sanitario dell’anno precedente",
    "population_40plus": "Popolazione dai 40 anni",
    "population_65plus": "Popolazione dai 65 anni",
    "share_65plus_among_40plus": "Quota 65+ tra i residenti 40+",
    "meteo_temperature_mean": "Temperatura media",
    "meteo_humidity_mean": "Umidità media",
    "meteo_wind_mean": "Velocità media del vento",
    "no2_mean": "Concentrazione media di NO₂",
    "pm25_mean": "Concentrazione media di PM₂,₅",
}


def format_value(value: float, digits: int = 3) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:.{digits}f}".replace(".", ",")


def render_explanation(case: pd.DataFrame) -> None:
    result = case.iloc[0]
    ordered = case.assign(magnitude=case["shap_value"].abs()).sort_values("magnitude", ascending=False)
    labels = ordered["variable"].map(VARIABLES).fillna(ordered["variable"])
    x = ["Valore di riferimento", *labels, "Previsione"]
    y = [result["base_value"], *ordered["shap_value"], 0]
    chart = go.Figure(go.Waterfall(
        orientation="v", x=x, y=y, measure=["absolute", *(["relative"] * len(ordered)), "total"],
        text=[format_value(result["base_value"]), *ordered["shap_value"].map(format_value), format_value(result["predicted"])],
        textposition="outside", increasing={"marker": {"color": "#176e5a"}},
        decreasing={"marker": {"color": "#a34135"}}, totals={"marker": {"color": "#184b78"}},
        connector={"line": {"color": "#667d91"}},
    ))
    chart.update_layout(
        yaxis_title="Tasso per 10.000 abitanti", xaxis_tickangle=-28, margin={"b": 110, "t": 25},
        height=480, showlegend=False,
    )
    st.plotly_chart(chart, width="stretch")
    st.caption("Il verde indica un aumento della previsione, il rosso una diminuzione. Le barre mostrano come il modello ha usato i dati. Da questo grafico non si può stabilire se un inquinante abbia causato l’esito.")
    st.dataframe(pd.DataFrame({
        "Variabile": labels, "Valore usato dal modello": ordered["value"].map(format_value),
        "Contributo SHAP": ordered["shap_value"].map(format_value),
    }), hide_index=True, width="stretch")


def render_experimental_forecasts(open_research: Callable[[], None], *, embedded: bool = False) -> None:
    if embedded:
        st.subheader("Spiegazioni XAI")
        st.write("XAI significa intelligenza artificiale spiegabile. Qui SHAP mostra quali variabili hanno aumentato o ridotto le previsioni di XGBoost per la BPCO. Sono spiegazioni di modelli già valutati, non nuovi addestramenti eseguiti durante la consultazione.")
    else:
        st.title("Previsioni sperimentali")
    st.write(
        "Esplora le previsioni storiche del modello XGBoost per la BPCO. Scegli un caso per "
        "confrontare la previsione con l’esito osservato e vedere come hanno contribuito le variabili."
    )
    st.caption("Per una prima lettura confronta Previsione e Valore osservato: la distanza fra i due indica "
               "l’errore per quel caso. Apri Spiega la previsione per vedere come ciascuna variabile ha spostato "
               "la stima a partire dal valore di riferimento del modello.")
    try:
        explanations = pd.read_csv(REPORTS / "shap_local_temporale.csv")
        errors = pd.read_csv(REPORTS / "xgboost_mae_ablation_per_anno.csv")
    except FileNotFoundError:
        st.info("Copia i due CSV delle previsioni sperimentali in reports/research/shap_temporale.")
        return
    if explanations.empty:
        st.info("L’archivio delle spiegazioni è vuoto.")
        return

    a, b, c, d = st.columns(4)
    outcome = a.selectbox("Esito", explanations["outcome"].unique(), format_func=OUTCOMES.__getitem__)
    selected = explanations.loc[explanations["outcome"].eq(outcome)]
    pollutant = b.selectbox("Inquinante incluso", selected["pollutant"].unique(), format_func=POLLUTANTS.__getitem__)
    selected = selected.loc[selected["pollutant"].eq(pollutant)]
    year = c.selectbox("Anno previsto", sorted(selected["target_year"].unique(), reverse=True))
    selected = selected.loc[selected["target_year"].eq(year)]
    asl = d.selectbox("ASL", sorted(selected["asl"].unique()))
    case = selected.loc[selected["asl"].eq(asl)]
    result = case.iloc[0]
    st.caption(f"Predittori del {int(result['feature_year'])} · Esito del {int(year)} · Tasso per 10.000 abitanti")
    a, b, c = st.columns(3)
    st.caption("Sono previsioni retrospettive: il modello è stato valutato su anni successivi a quelli di addestramento. Il valore di riferimento "
               "è il punto di partenza della spiegazione SHAP del modello, non il valore sanitario dell’anno precedente.")
    a.metric("Previsione XGBoost", format_value(result["predicted"]))
    b.metric("Valore osservato", format_value(result["observed"]))
    c.metric("Valore di riferimento", format_value(result["base_value"]))
    with st.expander("Spiega la previsione", expanded=True):
        render_explanation(case)

    st.subheader("Quali variabili contano nel test annuale?")
    st.caption("Questo riepilogo riguarda tutte le ASL valutate per l’esito, l’inquinante e l’anno selezionati. "
               "Il grafico della singola ASL, sopra, spiega invece soltanto il caso scelto.")
    try:
        importance = pd.read_csv(REPORTS / "shap_importanza_per_anno.csv")
        importance = importance.loc[
            importance["outcome"].eq(outcome) & importance["pollutant"].eq(pollutant) & importance["target_year"].eq(year)
        ].sort_values("mean_abs_shap")
    except (FileNotFoundError, KeyError):
        importance = pd.DataFrame()
    if not importance.empty:
        labels = importance["variable"].map(VARIABLES).fillna(importance["variable"])
        figure = go.Figure(go.Bar(x=importance["mean_abs_shap"], y=labels, orientation="h", marker_color="#184b78"))
        figure.update_layout(xaxis_title="Contributo SHAP medio in valore assoluto", yaxis_title="Variabile", height=380, margin={"l": 10, "r": 15, "t": 15, "b": 45})
        st.plotly_chart(figure, width="stretch")
        st.caption(f"Riepilogo di {selected['asl'].nunique()} ASL nel test annuale. Le barre misurano l’ampiezza media del contributo, "
                   "senza indicare se aumenti o diminuisca la previsione. Non rappresentano effetti causali sulla salute.")
    else:
        st.info("Riepilogo SHAP del test annuale non disponibile per questa selezione.")

    st.subheader("Quanto aiuta l’inquinante nella previsione?")
    st.caption("Il MAE è l’errore assoluto medio sulle ASL del test per l’anno selezionato. Un valore più basso indica un errore minore.")
    match = errors.loc[errors["outcome"].eq(outcome) & errors["pollutant"].eq(pollutant) & errors["target_year"].eq(year)]
    if not match.empty:
        with_mae = float(match.iloc[0]["with_pollutant"])
        without_mae = float(match.iloc[0]["without_pollutant"])
        difference = without_mae - with_mae
        a, b, c = st.columns(3)
        a.metric("MAE con inquinante", format_value(with_mae))
        b.metric("MAE senza inquinante", format_value(without_mae))
        c.metric("Riduzione del MAE", format_value(difference, 6))
        st.caption("Riduzione del MAE = errore senza inquinante − errore con inquinante. "
                   "Un valore positivo indica un miglioramento; un valore negativo un peggioramento. "
                   "La differenza è mostrata con sei decimali per rendere visibili anche variazioni piccole.")
        scope = " Il confronto riguarda tutte le ASL valutate nell’anno selezionato, non soltanto quella scelta nel grafico SHAP."
        if format_value(with_mae) == format_value(without_mae):
            st.info("L’aggiunta dell’inquinante non modifica l’errore alla precisione mostrata nei due MAE (tre decimali)." + scope)
        elif difference > 0:
            gain = 100 * difference / without_mae if without_mae > 0 else None
            relative = f" ({format_value(gain, 2)}%)" if gain is not None else ""
            st.success(f"L’aggiunta dell’inquinante riduce l’errore medio di {format_value(difference, 6)}{relative}." + scope)
        else:
            loss = -100 * difference / without_mae if without_mae > 0 else None
            relative = f" ({format_value(loss, 2)}%)" if loss is not None else ""
            st.info(f"L’aggiunta dell’inquinante aumenta l’errore medio di {format_value(-difference, 6)}{relative}." + scope)

    else:
        st.info("Confronto degli errori assente per la configurazione selezionata.")
    if st.button("Apri Modelli e validazione nel Research Panel"):
        open_research()
