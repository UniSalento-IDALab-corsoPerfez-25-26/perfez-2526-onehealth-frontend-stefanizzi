"""Shared ASL charts for data coverage and research."""

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.main_api import api_get
from app.dashboard.sidebar_menu import sidebar_menu


# ONEHEALTHAI_ENVIRONMENT_HISTORY_CHART_V1

def render_environment_history():
    # ONEHEALTHAI_ENVIRONMENT_LAYOUT_V3
    st.subheader("Serie storica ambientale dal 2010")

    st.caption(
        "Andamento annuale degli inquinanti atmosferici. "
        "Le medie sono ricostruite dai file originali ARPA con lo stesso criterio. "
        "Scegli ASL e inquinante. Le interruzioni indicano anni senza un valore utilizzabile."
    )

    payload = api_get("/research/environment-history")

    if payload is None:
        st.info("Dati ambientali non disponibili.")
        return

    frame = pd.DataFrame(payload.get("results", []))

    if frame.empty:
        st.info("Nessuna osservazione disponibile.")
        return

    left_filter, right_filter = st.columns(2)

    with left_filter:
        territory = st.selectbox(
            "Territorio",
            sorted(frame["asl"].dropna().unique()),
            key="environment_history_territory_v3",
        )

    available = frame.loc[
        frame["asl"] == territory
    ]

    with right_filter:
        pollutant = st.selectbox(
            "Inquinante",
            sorted(
                available["pollutant_code"].dropna().unique()
            ),
            key="environment_history_pollutant_v3",
        )

    selected = available.loc[
        available["pollutant_code"] == pollutant
    ].copy()

    selected["year"] = pd.to_numeric(
        selected["year"], errors="coerce"
    )

    selected["mean_value"] = pd.to_numeric(
        selected["mean_value"], errors="coerce"
    )

    selected["coverage_fraction"] = pd.to_numeric(
        selected["coverage_fraction"], errors="coerce"
    )

    selected = selected.sort_values("year")

    eligible = selected["analysis_eligible"].eq(True)

    selected["valore_grafico"] = selected[
        "mean_value"
    ].where(eligible)

    chart_col, table_col = st.columns(
        [1.6, 1],
        gap="medium",
    )

    with chart_col:
        with st.container(border=True):
            st.markdown(
                f"#### {pollutant} — {territory}"
            )

            fig = px.line(
                selected,
                x="year",
                y="valore_grafico",
                markers=True,
            )

            fig.update_traces(
                line_color="#287BEA",
                marker_size=7,
                connectgaps=False,
            )

            excluded = selected.loc[
                ~eligible
                & selected["mean_value"].notna()
            ]

            if not excluded.empty:
                fig.add_scatter(
                    x=excluded["year"],
                    y=excluded["mean_value"],
                    mode="markers",
                    name="Non idoneo QC",
                    marker=dict(
                        color="#D64545",
                        symbol="x",
                        size=10,
                    ),
                )

            fig.update_layout(
                height=380,
                margin=dict(
                    l=10, r=10, t=15, b=10
                ),
                xaxis_title="Anno",
                yaxis_title=(
                    "Valore medio annuale "
                    "(µg/m³)"
                ),
                legend=dict(
                    orientation="h",
                    y=-0.25,
                ),
            )

            fig.update_xaxes(dtick=1)

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    with table_col:
        with st.container(border=True):
            st.markdown("#### Valori annuali")

            table = selected[
                [
                    "year",
                    "mean_value",
                    "quality_status",
                    "analysis_eligible",
                ]
            ].copy()

            table.columns = [
                "Anno",
                "Valore",
                "Stato del dato",
                "Idoneo",
            ]

            table["Stato del dato"] = table["Stato del dato"].replace({"RECONSTRUCTED_QUALIFIED": "Disponibile", "UNIT_NOT_DOCUMENTED": "Unità non documentata", "NO_QUALIFIED_STATIONS": "Copertura insufficiente"})

            table["Idoneo"] = table["Idoneo"].map(
                {True: "Sì", False: "No"}
            ).fillna("Da verificare")

            st.dataframe(
                table,
                use_container_width=True,
                hide_index=True,
                height=380,
            )

    total = len(selected)
    valid = int(eligible.sum())
    excluded_count = total - valid

    c1, c2, c3 = st.columns(3)

    c1.metric("Anni disponibili", total)
    c2.metric("Idonei QC", valid)
    c3.metric("Non idonei QC", excluded_count)

    with st.expander(
        "Dettagli qualità e copertura dei dati"
    ):
        st.dataframe(
            selected[
                [
                    "year",
                    "mean_value",
                    "quality_status",
                    "analysis_eligible",
                    "coverage_fraction",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.warning(
        "Le medie ASL riassumono le stazioni con almeno il 75% dei giorni validi, "
        "con uguale peso per stazione. Numero e posizione delle stazioni possono variare. "
        "Il 2011 e il 2012 sono esclusi perché le unità non sono documentate nei file disponibili. "
        "Questi valori descrivono la rete di monitoraggio, non l’esposizione individuale."
    )




# ONEHEALTHAI_HEALTH_HISTORY_CHART_V1

def render_health_history():
    # ONEHEALTHAI_HEALTH_LAYOUT_V3

    st.subheader("Serie storica sanitaria dal 2010")

    st.caption(
        "Indicatori sanitari osservati ISTAT HFA. "
        "Mortalità: 2010–2023. "
        "Ospedalizzazioni: 2010–2024."
    )

    domain_label = sidebar_menu(
        "Ambito sanitario", ("Mortalità", "Ospedalizzazioni"), key="health_history_domain_v3",
    )

    domain = (
        "mortality"
        if domain_label == "Mortalità"
        else "hospital"
    )

    payload = api_get(
        "/research/health-history",
        params={"domain": domain},
    )

    if payload is None:
        st.info("Serie storica sanitaria non disponibile.")
        return

    frame = pd.DataFrame(payload.get("results", []))

    if frame.empty:
        st.info("Nessuna osservazione disponibile.")
        return

    filter_left, filter_right = st.columns(2)

    with filter_left:
        territory = st.selectbox(
            "Territorio",
            sorted(frame["asl"].dropna().unique()),
            key="health_history_territory_v3",
        )

    available = frame.loc[
        frame["asl"] == territory
    ]

    with filter_right:
        outcome = st.selectbox(
            "Indicatore sanitario",
            sorted(
                available["outcome"].dropna().unique()
            ),
            key="health_history_outcome_v3",
        )

    selected = available.loc[
        available["outcome"] == outcome
    ].copy()

    selected["year"] = pd.to_numeric(
        selected["year"], errors="coerce"
    )

    selected["value"] = pd.to_numeric(
        selected["value"], errors="coerce"
    )

    selected.loc[
        selected["is_missing"].eq(True),
        "value",
    ] = float("nan")

    selected = selected.sort_values("year")

    metric_values = (
        selected["metric"].dropna().unique().tolist()
    )

    metric_label = (
        metric_values[0]
        if len(metric_values) == 1
        else "Unità da verificare"
    )

    chart_col, table_col = st.columns(
        [1.6, 1],
        gap="medium",
    )

    with chart_col:
        with st.container(border=True):
            st.markdown(
                f"#### {outcome} — {territory}"
            )

            fig = px.line(
                selected,
                x="year",
                y="value",
                markers=True,
            )

            fig.update_traces(
                line_color="#287BEA",
                marker_size=7,
                connectgaps=False,
            )

            fig.update_layout(
                height=380,
                margin=dict(
                    l=10, r=10, t=15, b=10
                ),
                xaxis_title="Anno",
                yaxis_title=metric_label,
                showlegend=False,
            )

            fig.update_xaxes(dtick=1)

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    with table_col:
        with st.container(border=True):
            st.markdown("#### Valori annuali")

            table = selected[
                [
                    "year",
                    "value",
                    "is_missing",
                ]
            ].copy()

            table.columns = [
                "Anno",
                "Valore",
                "Mancante",
            ]

            table["Mancante"] = (
                table["Mancante"]
                .map({True: "Sì", False: "No"})
                .fillna("Da verificare")
            )

            st.dataframe(
                table,
                use_container_width=True,
                hide_index=True,
                height=380,
            )

    total = len(selected)
    observed = int(selected["value"].notna().sum())
    missing = total - observed

    c1, c2, c3 = st.columns(3)

    c1.metric("Anni disponibili", total)
    c2.metric("Valori osservati", observed)
    c3.metric("Valori mancanti", missing)

    with st.expander(
        "Dettagli scientifici e validazione"
    ):
        st.dataframe(
            selected[
                [
                    "year",
                    "value",
                    "metric",
                    "is_missing",
                    "validation_status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )






# ONEHEALTHAI_ENV_HEALTH_COMPARISON_V1
