from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from app.dashboard.updated_results import render_updated_results
from app.dashboard.research_overview import render_research_overview
from app.dashboard.ridge_explanations import render_ridge_explanations
from app.dashboard.monitoring_timeseries import render_monitoring_series
from app.dashboard.weather_context import ANNUAL_WEATHER_NOTE, split_weather_periods
from app.dashboard.update_status import render_daily_update_status
from app.dashboard.experimental_forecasts import render_experimental_forecasts
from app.dashboard.historical_series import render_environment_history, render_health_history
from app.dashboard.main_api import api_get
from app.dashboard.monthly_monitoring import render_monthly_monitoring
from app.dashboard.sidebar_menu import sidebar_menu
from app.dashboard.territorial_overview import render_territorial_overview
from app.dashboard.territorial_priorities import render_territorial_priorities


st.set_page_config(
    page_title="Panoramica · OneHealthAI",
    page_icon="🌿",
    layout="wide",
)

@st.cache_data(ttl=300)
def load_stations():
    return api_get("/stations")


@st.cache_data(ttl=300)
def load_latest_measurements():
    return api_get(
        "/measurements/latest",
        params={"limit": 1000},
    )

def render_master_dss():
    monitor_section = sidebar_menu(
        "Monitoraggio territoriale",
        ("Panoramica territoriale", "Monitoraggio mensile 2026", "Monitoraggio ambientale", "Qualità e pipeline", "Meteorologia e clima"),
        key="dss_monitor_section",
    )

    if monitor_section == "Monitoraggio mensile 2026":
        render_monthly_monitoring()
        return

    # ONEHEALTHAI_MASTER_VISUAL_V1
    st.markdown(
        """
        <div style="margin-bottom:18px">
          <div style="font-size:12px;font-weight:700;
                      letter-spacing:1.5px;color:#15936e">
            ONEHEALTHAI / DECISION SUPPORT SYSTEM
          </div>
          <h1 style="margin:6px 0;font-size:32px">
            Monitoraggio territoriale
          </h1>
          <div style="color:#718096;font-size:14px">
            Ambiente, salute e qualità dei dati ·
            Piattaforma operativa
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write({
        "Panoramica territoriale": "Consulta le ultime misure ambientali e il loro andamento. Usa i filtri per provincia e inquinante nella barra laterale.",
        "Monitoraggio ambientale": "Esplora la mappa delle stazioni ARPA, poi usa i filtri delle misure per approfondire provincia e inquinante.",
        "Qualità e pipeline": "Controlla lo stato delle fonti, i problemi di qualità registrati e l’ultima acquisizione. Usa il pulsante di aggiornamento per ricalcolare il riepilogo.",
        "Meteorologia e clima": "Consulta le serie meteorologiche disponibili. Scegli il territorio e la variabile da visualizzare e verifica se il periodo è completo.",
    }[monitor_section])


    # ---------------------------------------------------------
    # Controllo backend
    # ---------------------------------------------------------

    health = api_get("/health")

    if not health:
        st.stop()



    # ---------------------------------------------------------
    # Caricamento dati iniziali
    # ---------------------------------------------------------

    stations_data = load_stations()
    latest_data = load_latest_measurements()

    if not stations_data or not latest_data:
        st.stop()


    stations_df = pd.DataFrame(
        stations_data["stations"]
    )

    measurements_df = pd.DataFrame(
        latest_data["measurements"]
    )


    # ---------------------------------------------------------
    # Sidebar
    # ---------------------------------------------------------

    st.sidebar.header("Filtri")

    provinces = sorted(
        stations_df["province"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_province = st.sidebar.selectbox(
        "Provincia",
        ["Tutte"] + provinces,
    )

    if not measurements_df.empty:
        pollutants = sorted(
            measurements_df["pollutant"]
            .dropna()
            .unique()
            .tolist()
        )
    else:
        pollutants = []

    selected_pollutant = st.sidebar.selectbox(
        "Inquinante",
        ["Tutti"] + pollutants,
    )


    # ---------------------------------------------------------
    # Parametri API
    # ---------------------------------------------------------

    params = {
        "limit": 1000,
    }

    if selected_province != "Tutte":
        params["province"] = selected_province

    if selected_pollutant != "Tutti":
        params["pollutant"] = selected_pollutant


    filtered_response = api_get(
        "/measurements/latest",
        params=params,
    )

    if not filtered_response:
        st.stop()


    filtered_df = pd.DataFrame(
        filtered_response["measurements"]
    )


    # ---------------------------------------------------------
    # KPI
    # ---------------------------------------------------------

    render_daily_update_status()
    st.subheader(
        f"Ultime misure disponibili: "
        f"{filtered_response.get('date')}"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Misure",
        len(filtered_df),
    )

    col2.metric(
        "Stazioni",
        (
            filtered_df["station"]
            .nunique()
            if not filtered_df.empty
            else 0
        ),
    )

    valid_values = (
        filtered_df["value"]
        .notna()
        .sum()
        if not filtered_df.empty
        else 0
    )

    col3.metric(
        "Valori disponibili",
        int(valid_values),
    )

    warnings = (
        (
            filtered_df["quality_status"]
            == "VALID_WITH_WARNING"
        ).sum()
        if not filtered_df.empty
        else 0
    )

    col4.metric(
        "Warning",
        int(warnings),
    )

    # ---------------------------------------------------------
    # Serie temporale
    # ---------------------------------------------------------


    if monitor_section == "Panoramica territoriale":
        st.divider()
        st.subheader("Andamento temporale")

        chart_pollutant = selected_pollutant
        if chart_pollutant == "Tutti":
            if not pollutants:
                st.info("Nessun inquinante disponibile.")
                return
            chart_pollutant = st.selectbox(
                "Inquinante del grafico", pollutants,
                index=pollutants.index("NO2") if "NO2" in pollutants else 0,
                key="monitoring_chart_pollutant",
            )
        timeseries_params = {"pollutant": chart_pollutant}
        if selected_province != "Tutte":
            timeseries_params["province"] = selected_province
        timeseries_response = api_get("/measurements/timeseries", params=timeseries_params)
        if timeseries_response:
            render_monitoring_series(timeseries_response, chart_pollutant, measurements_df)

        # ---------------------------------------------------------
        # Mappa
        # ---------------------------------------------------------


    if monitor_section == "Monitoraggio ambientale":
        st.divider()
        st.subheader("Stazioni di monitoraggio")

        station_params = {}

        if selected_province != "Tutte":
            station_params["province"] = selected_province

        station_response = api_get(
            "/stations",
            params=station_params,
        )

        station_map_df = pd.DataFrame(
            station_response["stations"]
            if station_response
            else []
        )

        station_map_df = station_map_df.dropna(
            subset=[
                "latitude",
                "longitude",
            ]
        )

        if not station_map_df.empty:

            fig_map = px.scatter_map(
                station_map_df,
                lat="latitude",
                lon="longitude",
                hover_name="name",
                hover_data=[
                    "municipality",
                    "province",
                    "network",
                ],
                zoom=6,
                height=550,
            )

            fig_map.update_layout(
                map_style="open-street-map",
                margin={
                    "r": 0,
                    "t": 0,
                    "l": 0,
                    "b": 0,
                },
            )

            st.plotly_chart(
                fig_map,
                use_container_width=True,
            )

        else:
            st.info(
                "Nessuna stazione disponibile "
                "per i filtri selezionati."
            )


        # ---------------------------------------------------------
        # Misure
        # ---------------------------------------------------------

        st.divider()
        st.subheader("Ultime misure")

        if filtered_df.empty:
            st.info(
                "Nessuna misura disponibile."
            )

        else:
            display_columns = [
                "station",
                "municipality",
                "province",
                "pollutant",
                "value",
                "unit",
                "quality_status",
            ]

            existing_columns = [
                column
                for column in display_columns
                if column in filtered_df.columns
            ]

            st.dataframe(
                filtered_df[existing_columns],
                use_container_width=True,
                hide_index=True,
            )


        # ---------------------------------------------------------
        # Data quality
        # ---------------------------------------------------------



    # ONEHEALTHAI_ARPA_MASTER_MONITORING_V1
    if monitor_section == "Monitoraggio ambientale":
        st.divider()
        st.subheader("Misurazioni ARPA Puglia — archivio operativo")
        st.caption(
            "Fonte: PostgreSQL ARPA · Dati osservati · "
            "Nessuna promozione automatica al Research Panel"
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            arpa_province = st.selectbox(
                "Provincia ARPA",
                ["Tutte", "BAT", "Bari", "Brindisi",
                 "Foggia", "Lecce", "Taranto"],
                key="arpa_master_province",
            )

        with c2:
            arpa_pollutant = st.selectbox(
                "Inquinante ARPA",
                ["Tutti", "NO2", "O3", "PM10", "PM2.5", "SO2"],
                key="arpa_master_pollutant",
            )

        with c3:
            arpa_limit = st.selectbox(
                "Numero di misurazioni",
                [100, 250, 500, 1000],
                key="arpa_master_limit",
            )

        params = {"limit": arpa_limit}

        if arpa_province != "Tutte":
            params["province"] = arpa_province

        if arpa_pollutant != "Tutti":
            params["pollutant_code"] = arpa_pollutant

        try:
            response = requests.get(
                "http://127.0.0.1:8001/v1/operational-measurements-enriched",
                params=params,
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            arpa_df = pd.DataFrame(payload.get("items", []))

            if arpa_df.empty:
                st.info("Nessuna misurazione per i filtri selezionati.")
            else:
                arpa_df["value"] = pd.to_numeric(
                    arpa_df["value"], errors="coerce"
                )

                valid_df = arpa_df.loc[
                    arpa_df["value"].notna()
                    & arpa_df["quality_status"].eq("VALID")
                ].copy()

                m1, m2, m3 = st.columns(3)
                m1.metric("Misurazioni visualizzate", len(arpa_df))
                m2.metric("Valide nel campione", len(valid_df))
                m3.metric(
                    "Da verificare / escluse",
                    len(arpa_df) - len(valid_df),
                )

                st.dataframe(
                    arpa_df,
                    use_container_width=True,
                    hide_index=True,
                )

                st.caption(
                    "Le metriche si riferiscono soltanto ai record "
                    "restituiti dalla pagina API, non all'intero archivio. "
                    "I record diversi da VALID sono esclusi dal "
                    "sottoinsieme utilizzabile per analisi preliminari."
                )

        except requests.RequestException as exc:
            st.warning(
                "Servizio ambientale locale non disponibile (porta 8001). Controlla l’avvio di environment-service. Dettaglio: "
                + str(exc)
            )

    if monitor_section == "Qualità e pipeline":

        # ONEHEALTHAI_SOURCE_REFRESH_V3
        if st.button("Aggiorna stato delle fonti", key="refresh_sources"):
            import subprocess
            import sys

            with st.spinner("Aggiornamento monitoraggio..."):
                _result = subprocess.run(
                    [
                        sys.executable, "-c",
                        "import subprocess,sys; "
                        "scripts=['scripts/one_health/source_status.py',"
                        "'scripts/one_health/update_plan.py']; "
                        "[subprocess.run([sys.executable,s],check=True) for s in scripts]"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

            if _result.returncode == 0:
                st.success("Stato delle fonti aggiornato.")
                st.rerun()
            else:
                st.error("Aggiornamento non riuscito.")
                st.code(_result.stderr)

        # ONEHEALTHAI_UPDATE_PLAN_PANEL_V1
        _plan_path = __import__("pathlib").Path(
            "data/processed/one_health/operational/update_plan.json"
        )
        if _plan_path.exists():
            import json as _plan_json
            _plan = _plan_json.loads(
                _plan_path.read_text(encoding="utf-8")
            )
            st.markdown("#### Piano aggiornamenti")
            st.dataframe(
                [
                    {
                        "Fonte": a["domain"],
                        "Stato": a["status"],
                        "Motivazione": a["reason"],
                    }
                    for a in _plan.get("actions", [])
                ],
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "Piano generato: "
                + str(_plan.get("generated_at", "N/D"))
                + ". Nessuna acquisizione automatica."
            )

        # ONEHEALTHAI_SOURCE_STATUS_PANEL_V1
        st.subheader("Stato delle fonti dati")
        from pathlib import Path as _SourcePath
        import json as _source_json

        _status_path = _SourcePath(
            "data/processed/one_health/operational/source_status.json"
        )

        _report = {}
        if _status_path.exists():
            _report = _source_json.loads(
                _status_path.read_text(encoding="utf-8")
            )
            _rows = []
            for _domain, _info in _report["sources"].items():
                for _dataset in _info["datasets"]:
                    _rows.append({
                        "Dominio": _domain,
                        "Dataset": _SourcePath(_dataset["file"]).name,
                        "Stato": _dataset["status"],
                        "Primo anno": _dataset.get("first_year"),
                        "Ultimo anno": _dataset.get("last_year"),
                        "Record": _dataset.get("records", 0),
                    })
                if not _info["datasets"]:
                    _rows.append({
                        "Dominio": _domain,
                        "Dataset": "Non configurato",
                        "Stato": _info["status"],
                        "Primo anno": None,
                        "Ultimo anno": None,
                        "Record": 0,
                    })

            st.dataframe(_rows, use_container_width=True, hide_index=True)

        # ONEHEALTHAI_ARPA_OPERATIONAL_PANEL_V1
        _arpa = _report.get("sources", {}).get("environment", {}).get(
            "operational_database"
        )
        if _arpa:
            st.markdown("#### ARPA — Database operativo")
            _c1, _c2, _c3 = st.columns(3)
            _arpa_records = _arpa.get("records", _arpa.get("record_count", _arpa.get("rows")))
            _c1.metric(
                "Misurazioni",
                f"{_arpa_records:,}".replace(",", ".")
                if isinstance(_arpa_records, (int, float))
                else "N/D",
            )
            _c2.metric("Prima data", _arpa.get("first_date") or "N/D")
            _c3.metric("Ultima data", _arpa.get("last_date") or "N/D")
            st.caption(
                "Dati operativi PostgreSQL, separati dai dataset "
                "scientifici del Research Panel."
            )

            st.caption(
                "Copertura dei dataset registrati; READY indica leggibilità, "
                "non aggiornamento o validazione scientifica. "
                "Il monitoraggio ARPA operativo 2026 sarà integrato separatamente."
            )
        else:
            st.info("Report non disponibile. Eseguire source_status.py.")
        st.divider()
        st.subheader("Qualità dei dati")

        quality_response = api_get(
            "/quality/summary"
        )

        if quality_response:
            quality_df = pd.DataFrame(
                quality_response["issues"]
            )

            if not quality_df.empty:

                fig_quality = px.bar(
                    quality_df,
                    x="issue_type",
                    y="count",
                    hover_data=["severity"],
                    labels={
                        "issue_type": "Problema",
                        "count": "Numero record",
                    },
                )

                st.plotly_chart(
                    fig_quality,
                    use_container_width=True,
                )

                st.dataframe(
                    quality_df,
                    use_container_width=True,
                    hide_index=True,
                )

            else:
                st.info(
                    "Nessun problema di qualità registrato."
                )


        # ---------------------------------------------------------
        # Ultima ingestion
        # ---------------------------------------------------------

        st.divider()
        st.subheader("Stato pipeline ETL")

        ingestion = api_get(
            "/ingestion/latest"
        )

        if ingestion:

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Stato",
                ingestion.get(
                    "status",
                    "N/D",
                ),
            )

            col2.metric(
                "Record input",
                ingestion.get(
                    "input_records",
                    0,
                ),
            )

            col3.metric(
                "Duplicati",
                ingestion.get(
                    "duplicate_records",
                    0,
                ),
            )

            with st.expander(
                "Dettaglio ultima acquisizione"
            ):
                st.json(ingestion)




    # ONEHEALTHAI_METEOROLOGY_DASHBOARD_V1
    if monitor_section == "Meteorologia e clima":
        st.subheader("Riepilogo meteorologico annuale")
        st.caption(
            "Dati meteorologici provinciali Open-Meteo ERA5-Seamless. "
            "Serie storica 2010–2025 e aggiornamento provvisorio 2026."
        )
        st.write(ANNUAL_WEATHER_NOTE)
        st.caption("Il confronto mensile è disponibile in Qualità e copertura → Grafici dei dataset → Comune mensile.")
        if st.button("Esplora il meteo mensile", key="open_monthly_weather"):
            st.session_state["quality_section"] = "Grafici dei dataset"
            st.session_state["charts_group"] = "Comune mensile"
            st.session_state["charts_dataset"] = "Meteorologia comunale"
            st.switch_page("pages/quality_coverage.py")

        meteo_response = api_get("/v1/meteorology")

        if meteo_response is not None:
            meteo_df = pd.DataFrame(meteo_response.get("items", []))

            if meteo_df.empty:
                st.info("Nessun dato meteorologico disponibile.")
            else:
                variables = {
                    "Temperatura media annua (°C)": "temperature_mean",
                    "Temperatura minima (°C)": "temperature_min",
                    "Temperatura massima (°C)": "temperature_max",
                    "Umidità relativa media (%)": "relative_humidity_mean",
                    "Velocità media del vento (km/h)": "wind_speed_mean",
                    "Pressione superficiale media (hPa)": "surface_pressure_mean",
                    "Radiazione solare media (W/m²)": "shortwave_radiation_mean",
                    "Copertura nuvolosa media (%)": "cloud_cover_mean",
                    "Direzione media del vento (°)": "wind_direction_circular_mean",
                }

                c1, c2 = st.columns(2)

                with c1:
                    meteo_area = st.selectbox(
                        "Provincia meteorologica",
                        ["Tutte"] + sorted(meteo_df["asl"].unique()),
                        key="meteo_area",
                    )

                with c2:
                    meteo_variable = st.selectbox(
                        "Variabile meteorologica",
                        list(variables),
                        key="meteo_variable",
                    )

                column = variables[meteo_variable]

                selected = meteo_df.copy()
                if meteo_area != "Tutte":
                    selected = selected[selected["asl"] == meteo_area]

                selected = selected.sort_values(["asl", "year"])

                complete_years, partial_years = split_weather_periods(selected)
                if not partial_years.empty:
                    st.caption("Il grafico confronta soltanto gli anni completi. I periodi parziali sono riportati separatamente sotto la tabella, con la copertura disponibile.")

                fig = px.line(
                    complete_years,
                    x="year",
                    y=column,
                    color="asl",
                    markers=True,
                    labels={
                        "year": "Anno",
                        column: meteo_variable,
                        "asl": "Provincia",
                    },
                    hover_data=["quality_status", "coverage"],
                )

                fig.update_xaxes(dtick=1)

                st.plotly_chart(fig, use_container_width=True)

                st.caption(
                    "La direzione del vento è una media circolare. "
                    "Le temperature minime e massime provinciali "
                    "sono medie delle statistiche delle stazioni."
                )

                st.subheader("Copertura e qualità")

                columns = [
                    "year", "asl", column, "station_count",
                    "coverage", "quality_status",
                ]

                if "period_end" in selected.columns:
                    columns.append("period_end")

                st.dataframe(
                    complete_years[columns].sort_values(
                        ["year", "asl"], ascending=[False, True]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                if not partial_years.empty:
                    st.subheader("Periodi parziali disponibili")
                    st.caption("Questi valori non rappresentano un intero anno e non vanno confrontati direttamente con le medie annue. Verifica il termine del periodo e la copertura.")
                    partial_columns = [c for c in ["year", "asl", column, "period_start", "period_end", "coverage", "quality_status"] if c in partial_years]
                    st.dataframe(partial_years[partial_columns], use_container_width=True, hide_index=True)


def render_research_panel():
    # ONEHEALTHAI_RESEARCH_PANEL_V1
    # ---------------------------------------------------------
    # Research Panel - catalogo scientifico
    # ---------------------------------------------------------

    st.divider()
    st.header("Dataset e documentazione")
    st.caption(
        "Esplora i dati integrati, "
        "benchmark ML e risultati sperimentali."
    )


    with st.expander(
        "Catalogo degli artefatti scientifici",
        expanded=False
    ):
        research_response = api_get(
            "/research/artifacts"
        )

        if research_response is not None:
            artifacts = research_response.get(
                "artifacts", []
            )

            st.metric(
                "Artefatti scientifici registrati",
                len(artifacts)
            )

            if artifacts:
                research_df = pd.DataFrame(artifacts)

                display_columns = [
                    "id",
                    "type",
                    "status",
                    "format",
                    "master_dss_approved",
                ]

                available_columns = [
                    column
                    for column in display_columns
                    if column in research_df.columns
                ]

                st.dataframe(
                    research_df[available_columns],
                    use_container_width=True,
                    hide_index=True,
                )

            st.info(
                research_response.get(
                    "notice",
                    "Catalogo scientifico disponibile."
                )
            )




# ONEHEALTHAI_ML_BENCHMARKS_V1
def render_ml_benchmarks():
    st.subheader("Benchmark dei modelli ML")

    st.caption(
        "Confronto retrospettivo tra Persistence, "
        "Ridge, Random Forest e Gradient Boosting."
    )

    domain_label = st.selectbox(
        "Ambito sanitario",
        ["Mortalità", "Ospedalizzazioni"],
        key="research_ml_domain",
    )

    domain = (
        "mortality"
        if domain_label == "Mortalità"
        else "hospital"
    )

    payload = api_get(
        "/research/benchmarks",
        params={"domain": domain},
    )

    if payload is None:
        st.info("Benchmark non disponibile.")
        return

    frame = pd.DataFrame(
        payload.get("results", [])
    )

    if frame.empty:
        st.info("Nessun risultato disponibile.")
        return

    outcome = st.selectbox(
        "Indicatore sanitario",
        sorted(frame["outcome"].unique()),
        key="research_ml_outcome",
    )

    selected = frame[
        frame["outcome"] == outcome
    ].copy()

    selected = selected.sort_values("MAE")

    figure = px.bar(
        selected,
        x="model",
        y="MAE",
        color="model",
        hover_data=[
            "RMSE",
            "n",
            "mae_gain_pct",
        ],
        title="Errore assoluto medio (MAE)",
    )

    figure.update_layout(
        showlegend=False,
        xaxis_title="Modello",
        yaxis_title="MAE (unità dell'indicatore)",
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
    )

    st.dataframe(
        selected[
            [
                "model",
                "n",
                "MAE",
                "RMSE",
                "mae_gain_pct",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Un MAE inferiore indica un errore "
        "predittivo minore sul benchmark considerato."
    )





# ONEHEALTHAI_PREQUENTIAL_CHART_V1
def render_prequential_validation():
    st.subheader("Validazione temporale — Prequential V2")

    st.caption(
        "Confronto annuale tra il modello selezionato "
        "sulla base degli errori precedenti e Persistence."
    )

    domain_label = st.selectbox(
        "Ambito della validazione temporale",
        ["Mortalità", "Ospedalizzazioni"],
        key="prequential_domain",
    )

    domain = (
        "mortality"
        if domain_label == "Mortalità"
        else "hospital"
    )

    payload = api_get(
        "/research/prequential",
        params={"domain": domain},
    )

    if payload is None:
        st.info("Risultati prequential non disponibili.")
        return

    frame = pd.DataFrame(
        payload.get("results", [])
    )

    if frame.empty:
        st.info("Nessuna valutazione disponibile.")
        return

    outcome = st.selectbox(
        "Indicatore sanitario — validazione temporale",
        sorted(frame["outcome"].unique()),
        key="prequential_outcome",
    )

    selected = frame.loc[
        frame["outcome"] == outcome
    ].sort_values("test_year").copy()

    plot_frame = selected.melt(
        id_vars=["test_year"],
        value_vars=["selected_MAE", "baseline_MAE"],
        var_name="Serie",
        value_name="MAE",
    )

    plot_frame["Serie"] = plot_frame["Serie"].replace({
        "selected_MAE": "Modello selezionato",
        "baseline_MAE": "Persistence",
    })

    fig = px.line(
        plot_frame,
        x="test_year",
        y="MAE",
        color="Serie",
        markers=True,
        title="MAE per anno di valutazione",
    )

    fig.update_layout(
        xaxis_title="Anno",
        yaxis_title="MAE (unità dell'indicatore)",
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=sorted(
            selected["test_year"].unique().tolist()
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    selected["Esito"] = selected["gain"].apply(
        lambda value: (
            "Miglioramento" if value > 1e-9
            else "Peggioramento" if value < -1e-9
            else "Equivalente"
        )
    )

    st.dataframe(
        selected[
            [
                "test_year",
                "selected_model",
                "selected_MAE",
                "baseline_MAE",
                "gain",
                "Esito",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    improvements = int(
        (selected["gain"] > 1e-9).sum()
    )
    worsening = int(
        (selected["gain"] < -1e-9).sum()
    )
    equivalent = len(selected) - improvements - worsening

    col1, col2, col3 = st.columns(3)

    col1.metric("Anni migliori", improvements)
    col2.metric("Anni equivalenti", equivalent)
    col3.metric("Anni peggiori", worsening)





# ONEHEALTHAI_SCIENTIFIC_SUMMARY_V1
def render_scientific_summary():
    st.subheader("Sintesi scientifica dei risultati ML")

    st.caption(
        "Analisi descrittiva delle valutazioni "
        "temporali Prequential V2."
    )

    domain_label = st.selectbox(
        "Ambito della sintesi",
        ["Mortalità", "Ospedalizzazioni"],
        key="scientific_summary_domain",
    )

    domain = (
        "mortality"
        if domain_label == "Mortalità"
        else "hospital"
    )

    payload = api_get(
        "/research/prequential",
        params={"domain": domain},
    )

    if payload is None:
        st.info("Sintesi non disponibile.")
        return

    frame = pd.DataFrame(
        payload.get("results", [])
    )

    if frame.empty:
        st.info("Nessun risultato disponibile.")
        return

    tolerance = 1e-9

    frame["esito"] = frame["gain"].apply(
        lambda value: (
            "Miglioramento"
            if value > tolerance
            else "Peggioramento"
            if value < -tolerance
            else "Equivalente"
        )
    )

    total = len(frame)
    better = int(
        (frame["esito"] == "Miglioramento").sum()
    )
    equal = int(
        (frame["esito"] == "Equivalente").sum()
    )
    worse = int(
        (frame["esito"] == "Peggioramento").sum()
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Indicatori",
        frame["outcome"].nunique(),
    )

    col2.metric(
        "Valutazioni annuali",
        total,
    )

    col3.metric(
        "Miglioramenti",
        f"{100 * better / total:.1f}%",
    )

    col4.metric(
        "Peggioramenti",
        f"{100 * worse / total:.1f}%",
    )

    st.caption(
        f"Valutazioni: {better} miglioramenti, "
        f"{equal} equivalenze, "
        f"{worse} peggioramenti. "
        "Le percentuali si riferiscono alle "
        "valutazioni annuali, non agli indicatori."
    )

    st.markdown(
        "#### Risultati per indicatore sanitario"
    )

    summary = (
        frame.groupby("outcome")
        .agg(
            anni=("test_year", "nunique"),
            gain_medio=("gain", "mean"),
            miglioramenti=(
                "esito",
                lambda values: (
                    values == "Miglioramento"
                ).sum(),
            ),
            equivalenze=(
                "esito",
                lambda values: (
                    values == "Equivalente"
                ).sum(),
            ),
            peggioramenti=(
                "esito",
                lambda values: (
                    values == "Peggioramento"
                ).sum(),
            ),
        )
        .reset_index()
        .sort_values(
            "gain_medio",
            ascending=False,
        )
    )

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Il gain medio è la differenza media "
        "tra MAE di Persistence e MAE del modello "
        "selezionato. Valori positivi indicano "
        "un vantaggio medio in unità dell'indicatore. "
        "Non confrontare direttamente i gain "
        "di indicatori con scale diverse."
    )

    st.markdown(
        "#### Frequenza di selezione dei modelli"
    )

    counts = (
        frame["selected_model"]
        .value_counts()
        .rename_axis("Modello")
        .reset_index(name="Selezioni")
    )

    fig = px.bar(
        counts,
        x="Modello",
        y="Selezioni",
        title="Modelli selezionati nelle valutazioni annuali",
    )

    fig.update_layout(
        xaxis_title="Modello",
        yaxis_title="Numero di selezioni",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.markdown(
        "#### Interpretazione scientifica"
    )

    st.info(
        "I risultati rappresentano una valutazione "
        "retrospettiva della selezione dei modelli. "
        "Un miglioramento del MAE non implica "
        "stabilità predittiva futura né causalità "
        "tra esposizioni ambientali e salute."
    )





def render_environment_health_comparison():
    # ONEHEALTHAI_COMPARISON_LAYOUT_V3

    st.markdown(
        """
        <div class="oh-section-title">
            ↔ Analisi comparativa delle serie storiche
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Esplorazione descrittiva di indicatori sanitari "
        "e inquinanti atmosferici sul medesimo territorio."
    )

    domain_label = sidebar_menu(
        "Ambito sanitario", ("Mortalità", "Ospedalizzazioni"), key="comparison_domain_v3",
    )
    domain = (
        "mortality"
        if domain_label == "Mortalità"
        else "hospital"
    )

    health_payload = api_get(
        "/research/health-history",
        params={"domain": domain},
    )
    environment_payload = api_get(
        "/research/environment-history"
    )

    if health_payload is None or environment_payload is None:
        st.info("Dati del confronto non disponibili.")
        return

    health = pd.DataFrame(health_payload.get("results", []))
    environment = pd.DataFrame(
        environment_payload.get("results", [])
    )

    if health.empty or environment.empty:
        st.info("Serie storiche non disponibili.")
        return

    territories = sorted(
        set(health["asl"].dropna())
        & set(environment["asl"].dropna())
    )
    if not territories:
        st.info("Nessun territorio comune.")
        return

    col_territory, col_outcome, col_pollutant = st.columns(3)

    with col_territory:
        territory = st.selectbox(
            "Territorio",
            territories,
            key="comparison_territory_v3",
        )

    outcomes = sorted(
        health.loc[
            health["asl"] == territory,
            "outcome",
        ].dropna().unique()
    )
    pollutants = sorted(
        environment.loc[
            environment["asl"] == territory,
            "pollutant_code",
        ].dropna().unique()
    )

    with col_outcome:
        outcome = st.selectbox(
            "Indicatore sanitario",
            outcomes,
            key="comparison_outcome_v3",
        )

    with col_pollutant:
        pollutant = st.selectbox(
            "Inquinante",
            pollutants,
            key="comparison_pollutant_v3",
        )

    h = health.loc[
        (health["asl"] == territory)
        & (health["outcome"] == outcome)
    ].copy()

    e = environment.loc[
        (environment["asl"] == territory)
        & (environment["pollutant_code"] == pollutant)
    ].copy()

    h["year"] = pd.to_numeric(h["year"], errors="coerce")
    e["year"] = pd.to_numeric(e["year"], errors="coerce")
    h["value"] = pd.to_numeric(h["value"], errors="coerce")
    e["mean_value"] = pd.to_numeric(
        e["mean_value"], errors="coerce"
    )

    h.loc[
        h["is_missing"].eq(True),
        "value",
    ] = float("nan")

    # Manteniamo il valore ambientale originale
    # nella tabella, ma escludiamo dalla linea
    # le osservazioni non idonee ai controlli QC.
    e["environment_value_original"] = e["mean_value"]
    e["environment_value_valid"] = e[
        "mean_value"
    ].where(e["analysis_eligible"].eq(True))

    joined = h[
        ["year", "value", "metric", "validation_status"]
    ].merge(
        e[
            [
                "year",
                "environment_value_original",
                "environment_value_valid",
                "quality_status",
                "analysis_eligible",
                "coverage_fraction",
            ]
        ],
        on="year",
        how="inner",
        validate="one_to_one",
    ).sort_values("year")

    if joined.empty:
        st.info("Nessun anno comune disponibile.")
        return

    valid = joined.loc[
        joined["value"].notna()
        & joined["environment_value_valid"].notna()
    ]

    health_unit = (
        h["metric"].dropna().iloc[0]
        if h["metric"].notna().any()
        else "Unità da verificare"
    )

    min_year = int(joined["year"].min())
    max_year = int(joined["year"].max())

    st.markdown(
        f"**Territorio:** {territory}  |  "
        f"**Periodo comune:** {min_year}–{max_year}"
    )

    left_chart, right_chart = st.columns(
        2, gap="medium"
    )

    with left_chart:
        with st.container(border=True):
            st.markdown("#### ♥ Indicatore sanitario")

            fig_health = px.line(
                joined,
                x="year",
                y="value",
                markers=True,
                title=outcome,
            )
            fig_health.update_traces(
                line_color="#E46B79",
                marker_size=7,
                connectgaps=False,
            )
            fig_health.update_layout(
                height=370,
                margin=dict(l=10, r=10, t=45, b=10),
                xaxis_title="Anno",
                yaxis_title=health_unit,
                showlegend=False,
            )
            fig_health.update_xaxes(dtick=1)

            st.plotly_chart(
                fig_health,
                use_container_width=True,
            )

    with right_chart:
        with st.container(border=True):
            st.markdown("#### ▥ Inquinante ambientale")

            fig_environment = px.line(
                joined,
                x="year",
                y="environment_value_valid",
                markers=True,
                title=pollutant,
            )
            fig_environment.update_traces(
                line_color="#287BEA",
                marker_size=7,
                connectgaps=False,
            )

            excluded = joined.loc[
                ~joined["analysis_eligible"].eq(True)
                & joined["environment_value_original"].notna()
            ]

            if not excluded.empty:
                fig_environment.add_scatter(
                    x=excluded["year"],
                    y=excluded["environment_value_original"],
                    mode="markers",
                    name="Non idoneo QC",
                    marker=dict(
                        color="#D64545",
                        symbol="x",
                        size=10,
                    ),
                )

            fig_environment.update_layout(
                height=370,
                margin=dict(l=10, r=10, t=45, b=10),
                xaxis_title="Anno",
                yaxis_title="Valore (unità da verificare)",
            )
            fig_environment.update_xaxes(dtick=1)

            st.plotly_chart(
                fig_environment,
                use_container_width=True,
            )

    c1, c2, c3 = st.columns(3)

    c1.metric("Anni comuni", len(joined))
    c2.metric("Anni confrontabili", len(valid))
    c3.metric(
        "Anni non confrontabili",
        len(joined) - len(valid),
    )

    with st.expander(
        "Visualizza tabella annuale e controlli QC"
    ):
        st.dataframe(
            joined.rename(
                columns={
                    "year": "Anno",
                    "value": "Valore sanitario",
                    "environment_value_original":
                        "Valore ambientale originale",
                    "environment_value_valid":
                        "Valore ambientale QC",
                    "quality_status": "Qualità QC",
                    "analysis_eligible": "Idoneità QC",
                    "coverage_fraction": "Copertura",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.warning(
        "Confronto esplorativo, non causale. "
        "Le serie hanno unità differenti. "
        "L'equivalenza territoriale province/ASL, "
        "le definizioni degli indicatori e "
        "le metodologie di aggregazione ambientale "
        "richiedono ulteriori verifiche."
    )




# ONEHEALTHAI_MOCKUP_V2

st.markdown("""
<style>
.stApp {
    background: #f7f9fc;
    color: #17365e;
}
.block-container {
    max-width: 1550px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}
header[data-testid="stHeader"] {
    background: transparent;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#104577,#092e56);
}
section[data-testid="stSidebar"] * {
    color: #f2f7ff;
}
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    justify-content: flex-start;
    text-align: left;
    border: 1px solid transparent;
    border-radius: 8px;
    min-height: 42px;
    font-weight: 650;
    padding: 0.4rem 0.75rem;
    background: #284e73;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    border-color: #8db9db;
    background: #315d85;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #1764b3;
}
section[data-testid="stSidebar"] [class*="st-key-oh_submenu_"] .stButton > button {
    min-height: 30px;
    padding: 0.15rem 0.6rem;
    background: #143c60;
    border-radius: 6px;
    font-weight: 500;
}
section[data-testid="stSidebar"] [class*="st-key-oh_submenu_"] .stButton p {
    font-size: 0.84rem;
}
section[data-testid="stSidebar"] [class*="st-key-oh_submenu_"] .stButton > button:hover {
    background: #245275;
}
section[data-testid="stSidebar"] [class*="st-key-oh_submenu_"] .stButton > button[kind="primary"] {
    background: #11685f;
}
section[data-testid="stSidebar"] :is(.st-key-oh_top_pages, .st-key-oh_areas, [class*="st-key-oh_submenu_"])[data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] :is(.st-key-oh_top_pages, .st-key-oh_areas, [class*="st-key-oh_submenu_"]) [data-testid="stVerticalBlock"] {
    gap: 0.25rem;
}
section[data-testid="stSidebar"] .st-key-oh_brand h2 {
    padding: 0;
    margin: 0;
    letter-spacing: -0.03em;
}
section[data-testid="stSidebar"] .st-key-oh_brand [data-testid="stIconMaterial"] {
    color: #80e0ab;
}
h1, h2, h3 {
    color: #12375f;
    letter-spacing: -0.025em;
}
h1 {
    font-weight: 800;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e2eaf4;
    border-radius: 13px;
    padding: 1rem;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 15px;
}
div[data-testid="stAlert"] {
    border-radius: 12px;
}
.stButton > button {
    border-radius: 10px;
}
.oh-hero {
    background: #e7f3ff;
    border: 1px solid #d3e7fa;
    border-radius: 15px;
    padding: 1.3rem 1.6rem;
    margin: 0.5rem 0 1rem;
}
.oh-hero h3 {
    margin: 0 0 0.4rem;
    color: #103e78;
}
.oh-hero p {
    color: #315a85;
    margin: 0;
}
.oh-card {
    border-radius: 14px;
    padding: 1.2rem;
    min-height: 145px;
    border: 1px solid rgba(30,80,140,0.08);
}
.oh-card h4 {
    font-size: 1.04rem;
    margin: 0 0 0.55rem;
    color: #133d75;
}
.oh-card p {
    font-size: 0.89rem;
    margin: 0;
    color: #315777;
}
.oh-green {background: #e7f7ef;}
.oh-blue {background: #e5f2ff;}
.oh-red {background: #ffebed;}
.oh-purple {background: #efedff;}
.oh-section-title {
    background: linear-gradient(90deg,#287bc2,#368fe0);
    color: white;
    border-radius: 12px 12px 0 0;
    padding: 0.8rem 1.1rem;
    font-weight: 700;
    font-size: 1.12rem;
    margin-top: 1rem;
}
.oh-kicker {
    color: #597a9c;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
.st-key-oh_home_hero {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    border-radius: 22px;
    padding: clamp(1.6rem, 4vw, 3.4rem);
    margin: 0.45rem 0 0.85rem;
    background: linear-gradient(112deg, #102a43 13%, #154d61 71%, #176557 100%);
}
.st-key-oh_home_hero::after {
    content: "";
    position: absolute;
    z-index: -1;
    inset: 0;
    pointer-events: none;
    background: repeating-radial-gradient(ellipse at 99% -58%,
        transparent 0 2.1rem, rgba(162, 237, 203, 0.14) 2.12rem 2.17rem, transparent 2.19rem 3rem);
    mask-image: linear-gradient(90deg, transparent 20%, #000 100%);
}
.st-key-oh_home_hero h1 {
    color: #f6fbff;
    font-size: clamp(2rem, 4.4vw, 3.65rem);
    line-height: 1.07;
    padding: 0;
    max-width: 16ch;
}
.st-key-oh_home_hero p {
    max-width: 56ch;
    color: #e2eff4;
    font-size: clamp(0.98rem, 1.45vw, 1.12rem);
    line-height: 1.56;
    margin-bottom: 0;
}
[class*="st-key-oh_home_card_"] {
    --oh-accent: #135849;
    --oh-tint: #e8f5ef;
    background: #fff;
    border: 1px solid #dce6ee;
    border-radius: 16px;
    padding: 1.15rem;
}
.st-key-oh_home_card_quality {
    --oh-accent: #4b3c83;
    --oh-tint: #f0edf9;
}
.st-key-oh_home_card_research {
    --oh-accent: #175587;
    --oh-tint: #eaf3fa;
}
[class*="st-key-oh_home_card_"] [data-testid="stIconMaterial"] {
    color: var(--oh-accent);
}
[class*="st-key-oh_home_card_"] [data-testid="stMarkdownContainer"] [data-testid="stIconMaterial"] {
    display: grid;
    place-items: center;
    width: 2.5rem;
    height: 2.5rem;
    background: var(--oh-tint);
    border-radius: 10px;
    font-size: 1.35rem;
}
[class*="st-key-oh_home_card_"] h3 {
    min-height: 2.5em;
    padding: 0;
    font-size: clamp(1.05rem, 1.6vw, 1.25rem);
    line-height: 1.25;
    letter-spacing: -0.02em;
}
[class*="st-key-oh_home_card_"] [data-testid="stMarkdownContainer"] p {
    color: #394e63;
    line-height: 1.48;
}
[class*="st-key-oh_home_card_"] [data-testid="stMarkdown"]
    :not(:has([data-testid="stIconMaterial"])) > p {
    min-height: 5.92em;
    margin: 0;
}
[class*="st-key-oh_home_card_"] .stButton > button {
    min-height: 2.55rem;
    justify-content: flex-start;
    border-color: transparent;
    border-radius: 8px;
    background: var(--oh-tint);
    color: var(--oh-accent);
}
[class*="st-key-oh_home_card_"] .stButton > button:hover {
    border-color: var(--oh-accent);
    color: var(--oh-accent);
}
[class*="st-key-oh_home_card_"] .stButton p {
    color: inherit;
    font-weight: 650;
}
@media (max-width: 900px) {
    [class*="st-key-oh_home_card_"] h3,
    [class*="st-key-oh_home_card_"] [data-testid="stMarkdown"] :not(:has([data-testid="stIconMaterial"])) > p {
        min-height: 0;
    }
}
</style>
""", unsafe_allow_html=True)


def oh_navigate(area, section=None):
    st.session_state["oh_area"] = area
    if section is not None:
        st.session_state["oh_section"] = section
    st.rerun()


def oh_sidebar():
    with st.sidebar, st.container(key="oh_areas"):
        current = st.session_state.get("oh_area", "Home")
        for label in ("Decision Support System", "Research Panel"):
            if st.button(
                label,
                key=f"oh_nav_{label}",
                type="primary" if current == label else "secondary",
                width="stretch",
            ):
                oh_navigate(label)


def oh_card(title, description, css_class):
    st.markdown(
        f"""
        <div class="oh-card {css_class}">
            <h4>{title}</h4>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home_v2():
    with st.container(key="oh_home_hero"):
        st.title("Ambiente e salute in Puglia")
        st.write(
            "OneHealthAI riunisce dati pubblici sulla qualità dell’aria e sulla salute. "
            "Esplora le misure ambientali, confronta gli indicatori delle ASL e verifica "
            "quali territori e periodi sono coperti dai dati. Per iniziare, scegli una delle tre schede qui sotto. Usa Panoramica nel menu a sinistra per tornare a questa pagina."
        )

    with st.expander("Prima visita? Scegli da dove iniziare"):
        st.markdown(
            "**Vuoi sapere com’è l’aria nella tua provincia?** Apri Decision Support System → "
            "Monitoraggio territoriale → Monitoraggio mensile 2026. Scegli provincia, mese e inquinante.\n\n"
            "**Vuoi confrontare le aziende sanitarie locali (ASL)?** Apri Decision Support System → "
            "Priorità territoriali. Scegli una patologia e un anno, poi seleziona un’ASL sotto la graduatoria.\n\n"
            "**Cerchi i dati di un comune o di un anno?** Apri Qualità e copertura dei dati → Catalogo. "
            "Puoi controllare la fonte e il periodo disponibile prima di interpretare un grafico.\n\n"
            "**Vuoi capire se gli inquinanti aiutano a prevedere un esito sanitario?** "
            "Apri Research Panel → Modelli e validazione per confrontare gli errori di previsione."
        )

    decision, quality, research = st.columns(3, gap="small")
    with decision, st.container(key="oh_home_card_decision", border=True):
        st.markdown(":material/monitoring:")
        st.subheader("Decision Support System")
        st.write(
            "Consulta le misure delle stazioni, confronta le ASL e scopri come cambiano "
            "le priorità territoriali al variare dei pesi."
        )
        if st.button("Apri il DSS", key="home_to_dss", width="stretch", icon=":material/arrow_forward:"):
            oh_navigate("Decision Support System")

    with quality, st.container(key="oh_home_card_quality", border=True):
        st.markdown(":material/database:")
        st.subheader("Qualità e copertura dei dati")
        st.write(
            "Verifica gli anni e i territori coperti dagli archivi e risali "
            "alle fonti dei dati visualizzati."
        )
        if st.button("Esplora i dati", key="home_to_quality", width="stretch", icon=":material/arrow_forward:"):
            st.switch_page("pages/quality_coverage.py")

    with research, st.container(key="oh_home_card_research", border=True):
        st.markdown(":material/query_stats:")
        st.subheader("Research Panel")
        st.write(
            "Esplora le serie storiche, i confronti tra ambiente e salute "
            "e i risultati dei modelli."
        )
        if st.button("Apri il Research Panel", key="home_to_research", width="stretch", icon=":material/arrow_forward:"):
            oh_navigate("Research Panel")


def render_research_v2():
    st.title("Research Panel")
    st.caption(
        "Analisi esplorative su ambiente, salute "
        "e modelli previsionali"
    )


    selected = sidebar_menu(
        "Sezioni di ricerca",
        ("Panoramica", "Serie storiche", "Ambiente–salute", "Modelli e validazione", "Spiegazioni XAI", "Sintesi scientifica"),
        key="oh_section",
    )

    st.write({
        "Panoramica": "",
        "Serie storiche": "Esplora le osservazioni annuali. Scegli Ambiente o Salute, poi imposta il territorio e l’indicatore che vuoi seguire.",
        "Ambiente–salute": "Confronta le serie di un inquinante e di un indicatore sanitario nello stesso territorio. Usa i filtri e controlla gli anni disponibili per entrambe le serie.",
        "Modelli e validazione": "Consulta le prestazioni dei modelli previsionali. Usa Benchmark ML per confrontare gli algoritmi o Validazione prequential per esaminare la valutazione temporale.",
        "Spiegazioni XAI": "Scegli Ridge o XGBoost e una previsione per capire il contributo delle variabili. Ridge comprende le analisi annuali ASL e mensili comunali; XGBoost comprende le configurazioni BPCO disponibili.",
        "Sintesi scientifica": "Leggi i risultati sperimentali e le condizioni in cui sono stati ottenuti. Per approfondire le metriche, apri Modelli e validazione.",
    }[selected])

    if selected == "Panoramica":
        def navigate_research(section, analysis=None):
            if analysis is not None:
                st.session_state["oh_model_section"] = analysis
            oh_navigate("Research Panel", section)

        render_research_overview(navigate_research)
        with st.expander("Catalogo tecnico dei dati e dei risultati"):
            if st.checkbox("Carica il catalogo", key="research_overview_load_catalog"):
                render_research_panel()

    elif selected == "Serie storiche":
        st.markdown(
            '<div class="oh-section-title">'
            '▥  Serie storiche ambientali e sanitarie'
            '</div>',
            unsafe_allow_html=True,
        )

        source = sidebar_menu(
            "Fonte dati", ("Ambiente", "Salute"), key="oh_historical_source",
        )

        if source == "Ambiente":
            render_environment_history()
        else:
            render_health_history()

    elif selected == "Ambiente–salute":
        st.markdown(
            '<div class="oh-section-title">'
            '↔  Confronto storico ambiente–salute'
            '</div>',
            unsafe_allow_html=True,
        )
        render_environment_health_comparison()

    elif selected == "Modelli e validazione":
        st.markdown(
            '<div class="oh-section-title">'
            '⚙  Modelli e validazione temporale'
            '</div>',
            unsafe_allow_html=True,
        )

        model_section = sidebar_menu(
            "Analisi", ("Benchmark ML", "Validazione prequential", "Risultati annuali e mensili"), key="oh_model_section",
        )

        if model_section == "Benchmark ML":
            render_ml_benchmarks()
        elif model_section == "Risultati annuali e mensili":
            render_updated_results()
        else:
            render_prequential_validation()

    elif selected == "Spiegazioni XAI":
        algorithm = st.selectbox("Modello da spiegare", ["Ridge", "XGBoost"], key="research_xai_algorithm")
        if algorithm == "Ridge":
            render_ridge_explanations()
        else:
            render_experimental_forecasts(lambda: oh_navigate("Research Panel", "Modelli e validazione"), embedded=True)

    elif selected == "Sintesi scientifica":
        st.markdown(
            '<div class="oh-section-title">'
            '▤  Sintesi scientifica'
            '</div>',
            unsafe_allow_html=True,
        )
        render_scientific_summary()


def render_overview():
    oh_sidebar()

    area = st.session_state.get("oh_area", "Home")

    if area == "Home":
        render_home_v2()
    elif area == "Decision Support System":
        section = sidebar_menu(
            "Viste del Decision Support System", ("Monitoraggio territoriale", "Quadro territoriale", "Priorità territoriali", "Previsioni sperimentali"), key="master_dss_section",
        )
        if section == "Monitoraggio territoriale":
            render_master_dss()
        elif section == "Quadro territoriale":
            render_territorial_overview()
        elif section == "Priorità territoriali":
            render_territorial_priorities()
        else:
            algorithm = st.selectbox("Modello da spiegare", ["XGBoost", "Ridge"], key="dss_xai_algorithm")
            if algorithm == "Ridge":
                st.title("Previsioni sperimentali")
                render_ridge_explanations()
            else:
                render_experimental_forecasts(lambda: oh_navigate("Research Panel", "Modelli e validazione"))
    elif area == "Research Panel":
        render_research_v2()


overview_page = st.Page(render_overview, title="Panoramica", default=True)
quality_page = st.Page(
    "pages/quality_coverage.py",
    title="Qualità e copertura dei dati",
    url_path="qualita-e-copertura",
)
page = st.navigation([overview_page, quality_page], position="hidden")
in_overview = page.url_path == overview_page.url_path
if st.session_state.get("oh_area") == "Master DSS":
    st.session_state["oh_area"] = "Decision Support System"
on_home = in_overview and st.session_state.get("oh_area", "Home") == "Home"
with st.sidebar:
    with st.container(key="oh_brand"):
        st.markdown("## :material/eco: OneHealthAI")
    with st.container(key="oh_top_pages"):
        if st.button("Panoramica", key="oh_page_overview", type="primary" if on_home else "secondary", width="stretch"):
            st.session_state["oh_area"] = "Home"
            st.switch_page(overview_page)
        if st.button(
            "Qualità e copertura dei dati", key="oh_page_quality",
            type="secondary" if in_overview else "primary", width="stretch",
        ):
            st.switch_page(quality_page)
page.run()
