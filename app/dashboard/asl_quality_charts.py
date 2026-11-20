from __future__ import annotations

import os
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


API_BASE_URL = os.getenv(
    "ONE_HEALTH_API_URL",
    "http://127.0.0.1:8000",
)


def api_get(
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    try:
        response = requests.get(
            f"{API_BASE_URL}{endpoint}",
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as exc:
        st.error(
            "Errore durante la comunicazione con FastAPI: "
            f"{exc}"
        )

        return None


@st.cache_data(ttl=300)
def load_summary() -> dict[str, Any] | None:
    return api_get(
        "/one-health/summary"
    )


@st.cache_data(ttl=300)
def load_one_health_data(
    start_year: int,
    end_year: int,
    asl: str | None,
    indicator: str | None,
    sex: str | None,
    age_group: str | None,
) -> dict[str, Any] | None:
    params: dict[str, Any] = {
        "start_year": start_year,
        "end_year": end_year,
        "limit": 10000,
    }

    if asl:
        params["asl"] = asl

    if indicator:
        params["indicator"] = indicator

    if sex:
        params["sex"] = sex

    if age_group:
        params["age_group"] = age_group

    return api_get(
        "/one-health/data",
        params=params,
    )


@st.cache_data(ttl=300)
def load_environmental_data(
    start_year: int,
    end_year: int,
    asl: str | None,
    pollutant: str | None,
) -> dict[str, Any] | None:
    params: dict[str, Any] = {
        "start_year": start_year,
        "end_year": end_year,
        "limit": 10000,
    }

    if asl:
        params["asl"] = asl

    if pollutant:
        params["pollutant"] = pollutant

    return api_get(
        "/one-health/environment",
        params=params,
    )


def render_asl_quality_charts() -> None:
    st.subheader("Grafici del dataset ASL 2021–2023")

    st.caption(
        "Controllo tecnico dell'integrazione tra dati ambientali "
        "ARPAP, indicatori sanitari AReSS e popolazione ISTAT."
    )


    summary = load_summary()

    if not summary:
        return


    years = summary.get("years", [])
    asl_values = summary.get("asl", [])
    indicators = summary.get("indicators", [])
    sexes = summary.get("sexes", [])
    age_groups = summary.get("age_groups", [])


    if not years:
        st.warning(
            "Il dataset One Health non contiene annualità."
        )
        return


    # ---------------------------------------------------------
    # Sidebar
    # ---------------------------------------------------------

    st.sidebar.header("Filtri")

    start_year = st.sidebar.selectbox(
        "Anno iniziale",
        years,
        index=0,
    )

    end_year = st.sidebar.selectbox(
        "Anno finale",
        years,
        index=len(years) - 1,
    )

    if start_year > end_year:
        st.sidebar.error(
            "L'anno iniziale non può superare quello finale."
        )
        return


    selected_asl = st.sidebar.selectbox(
        "ASL",
        ["Tutte"] + asl_values,
    )

    selected_indicator = st.sidebar.selectbox(
        "Indicatore sanitario",
        ["Tutti"] + indicators,
    )

    selected_sex = st.sidebar.selectbox(
        "Sesso",
        ["Tutti"] + sexes,
    )

    selected_age_group = st.sidebar.selectbox(
        "Fascia d'età",
        ["Tutte"] + age_groups,
    )


    asl_filter = (
        None
        if selected_asl == "Tutte"
        else selected_asl
    )

    indicator_filter = (
        None
        if selected_indicator == "Tutti"
        else selected_indicator
    )

    sex_filter = (
        None
        if selected_sex == "Tutti"
        else selected_sex
    )

    age_filter = (
        None
        if selected_age_group == "Tutte"
        else selected_age_group
    )


    data_response = load_one_health_data(
        start_year=start_year,
        end_year=end_year,
        asl=asl_filter,
        indicator=indicator_filter,
        sex=sex_filter,
        age_group=age_filter,
    )

    if not data_response:
        return


    data = pd.DataFrame(
        data_response.get(
            "data",
            [],
        )
    )

    if data.empty:
        st.info(
            "Nessun record disponibile per i filtri selezionati."
        )
        return


    # ---------------------------------------------------------
    # KPI
    # ---------------------------------------------------------

    st.subheader("Copertura del dataset")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Record",
        len(data),
    )

    col2.metric(
        "Anni",
        data["year"].nunique(),
    )

    col3.metric(
        "ASL",
        data["asl"].nunique(),
    )

    col4.metric(
        "Indicatori",
        data["indicator_code"].nunique(),
    )

    col5.metric(
        "Sottogruppi",
        data[
            [
                "sex",
                "age_group",
            ]
        ]
        .drop_duplicates()
        .shape[0],
    )


    # ---------------------------------------------------------
    # Controlli qualità
    # ---------------------------------------------------------

    st.subheader("Controlli di qualità")

    logical_keys = [
        "indicator_code",
        "year",
        "asl",
        "sex",
        "age_group",
    ]

    duplicate_count = int(
        data.duplicated(
            subset=logical_keys,
            keep=False,
        ).sum()
    )

    main_columns = [
        "cases",
        "population",
        "prevalence_per_1000",
        "pm10_mean_value",
        "pm2_5_mean_value",
        "no2_mean_value",
        "o3_mean_value",
    ]

    existing_main_columns = [
        column
        for column in main_columns
        if column in data.columns
    ]

    null_count = int(
        data[existing_main_columns]
        .isna()
        .sum()
        .sum()
    )

    invalid_population = int(
        (
            pd.to_numeric(
                data["population"],
                errors="coerce",
            )
            <= 0
        ).sum()
    )

    invalid_cases = int(
        (
            pd.to_numeric(
                data["cases"],
                errors="coerce",
            )
            < 0
        ).sum()
    )

    q1, q2, q3, q4 = st.columns(4)

    q1.metric(
        "Duplicati logici",
        duplicate_count,
    )

    q2.metric(
        "Valori mancanti",
        null_count,
    )

    q3.metric(
        "Popolazioni non valide",
        invalid_population,
    )

    q4.metric(
        "Conteggi sanitari non validi",
        invalid_cases,
    )


    if (
        duplicate_count == 0
        and null_count == 0
        and invalid_population == 0
        and invalid_cases == 0
    ):
        st.success(
            "I controlli principali di qualità sono superati."
        )
    else:
        st.warning(
            "Sono presenti anomalie da approfondire."
        )


    # ---------------------------------------------------------
    # Prevalenza per fascia d'età
    # ---------------------------------------------------------

    st.subheader("Prevalenza sanitaria per fascia d'età")

    plot_data = data.copy()

    plot_data["prevalence_per_1000"] = pd.to_numeric(
        plot_data["prevalence_per_1000"],
        errors="coerce",
    )

    plot_data["year"] = (
        pd.to_numeric(
            plot_data["year"],
            errors="coerce",
        )
        .astype("Int64")
    )

    age_order = [
        "40-44",
        "45-49",
        "50-54",
        "55-59",
        "60-64",
        "65-69",
        "70-74",
        "75-79",
        "80-84",
        "85+",
    ]

    plot_data["age_group"] = pd.Categorical(
        plot_data["age_group"],
        categories=age_order,
        ordered=True,
    )

    fig_age = px.line(
        plot_data.sort_values(
            [
                "year",
                "asl",
                "sex",
                "age_group",
            ]
        ),
        x="age_group",
        y="prevalence_per_1000",
        color="asl",
        line_dash="sex",
        facet_col="year",
        markers=True,
        labels={
            "age_group": "Fascia d'età",
            "prevalence_per_1000": "Prevalenza per 1.000",
            "asl": "ASL",
            "sex": "Sesso",
            "year": "Anno",
        },
    )

    fig_age.update_xaxes(
        categoryorder="array",
        categoryarray=age_order,
    )

    st.plotly_chart(
        fig_age,
        use_container_width=True,
    )


    # ---------------------------------------------------------
    # Confronto per ASL
    # ---------------------------------------------------------

    st.subheader("Prevalenza media per ASL")

    asl_summary = (
        plot_data.groupby(
            [
                "year",
                "asl",
            ],
            as_index=False,
        )
        .agg(
            population=(
                "population",
                "sum",
            ),
            cases=(
                "cases",
                "sum",
            ),
        )
    )

    asl_summary["prevalence_per_1000"] = (
        asl_summary["cases"]
        / asl_summary["population"]
        * 1000
    )

    fig_asl = px.bar(
        asl_summary,
        x="asl",
        y="prevalence_per_1000",
        color="year",
        barmode="group",
        hover_data=[
            "cases",
            "population",
        ],
        labels={
            "asl": "ASL",
            "prevalence_per_1000": "Prevalenza per 1.000",
            "year": "Anno",
            "cases": "Casi",
            "population": "Popolazione",
        },
    )

    st.plotly_chart(
        fig_asl,
        use_container_width=True,
    )


    # ---------------------------------------------------------
    # Esposizione ambientale
    # ---------------------------------------------------------

    st.subheader("Esposizione ambientale annuale")

    pollutant_options = [
        "PM10",
        "PM2.5",
        "NO2",
        "O3",
    ]

    selected_pollutant = st.selectbox(
        "Inquinante da visualizzare",
        pollutant_options,
    )

    environment_response = load_environmental_data(
        start_year=start_year,
        end_year=end_year,
        asl=asl_filter,
        pollutant=selected_pollutant,
    )

    environment = pd.DataFrame(
        environment_response.get(
            "data",
            [],
        )
        if environment_response
        else []
    )

    if environment.empty:
        st.info(
            "Nessun indicatore ambientale disponibile."
        )

    else:
        environment["year"] = pd.to_numeric(
            environment["year"],
            errors="coerce",
        )

        environment["mean_value"] = pd.to_numeric(
            environment["mean_value"],
            errors="coerce",
        )

        fig_environment = px.bar(
            environment,
            x="asl",
            y="mean_value",
            color="year",
            barmode="group",
            hover_data=[
                "median_value",
                "percentile_95",
                "maximum_value",
                "availability_percent",
                "stations",
                "days",
            ],
            labels={
                "asl": "ASL",
                "mean_value": (
                    f"Valore medio annuale {selected_pollutant}"
                ),
                "year": "Anno",
            },
        )

        st.plotly_chart(
            fig_environment,
            use_container_width=True,
        )


    # ---------------------------------------------------------
    # Confronto esplorativo ambiente-salute
    # ---------------------------------------------------------

    st.subheader("Confronto esplorativo ambiente–salute")

    pollutant_column_mapping = {
        "PM10": "pm10_mean_value",
        "PM2.5": "pm2_5_mean_value",
        "NO2": "no2_mean_value",
        "O3": "o3_mean_value",
    }

    environment_column = pollutant_column_mapping[
        selected_pollutant
    ]

    comparison = data.copy()

    comparison[environment_column] = pd.to_numeric(
        comparison[environment_column],
        errors="coerce",
    )

    comparison["prevalence_per_1000"] = pd.to_numeric(
        comparison["prevalence_per_1000"],
        errors="coerce",
    )

    # Per evitare di contare più volte la stessa esposizione,
    # la visualizzazione resta stratificata per sesso ed età.
    fig_comparison = px.scatter(
        comparison,
        x=environment_column,
        y="prevalence_per_1000",
        color="asl",
        symbol="sex",
        size="population",
        hover_data=[
            "year",
            "age_group",
            "cases",
            "population",
        ],
        labels={
            environment_column: (
                f"Esposizione media annuale {selected_pollutant}"
            ),
            "prevalence_per_1000": "Prevalenza per 1.000",
            "asl": "ASL",
            "sex": "Sesso",
        },
    )

    st.plotly_chart(
        fig_comparison,
        use_container_width=True,
    )

    st.info(
        "Il grafico è esplorativo: una correlazione visiva non "
        "dimostra un rapporto causale. Le esposizioni ambientali "
        "sono definite a livello ASL-anno e vengono ripetute nei "
        "diversi sottogruppi sanitari."
    )


    # ---------------------------------------------------------
    # Matrice valori mancanti
    # ---------------------------------------------------------

    st.subheader("Completezza delle variabili")

    missing_summary = (
        data[existing_main_columns]
        .isna()
        .sum()
        .rename("missing")
        .reset_index()
        .rename(
            columns={
                "index": "variable",
            }
        )
    )

    missing_summary["available"] = (
        len(data)
        - missing_summary["missing"]
    )

    missing_summary["availability_percent"] = (
        missing_summary["available"]
        / len(data)
        * 100
    ).round(2)

    st.dataframe(
        missing_summary,
        use_container_width=True,
        hide_index=True,
    )


    # ---------------------------------------------------------
    # Dataset
    # ---------------------------------------------------------

    st.subheader("Record integrati")

    display_columns = [
        "indicator_code",
        "year",
        "asl",
        "sex",
        "age_group",
        "cases",
        "population",
        "prevalence_per_1000",
        "pm10_mean_value",
        "pm2_5_mean_value",
        "no2_mean_value",
        "o3_mean_value",
        "dataset_version",
        "quality_status_integrated",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in data.columns
    ]

    st.dataframe(
        data[display_columns],
        use_container_width=True,
        hide_index=True,
    )