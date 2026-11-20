"""Explore coverage and quality in the datasets shipped with OneHealthAI."""

from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.asl_quality_charts import render_asl_quality_charts
from app.dashboard.data_lineage import render_data_lineage
from app.dashboard.data_quality_catalog import CATALOG, DATA, STATION_KEY, Dataset
from app.dashboard.historical_series import render_environment_history, render_health_history
from app.dashboard.recent_data import render_recent_data
from app.dashboard.sidebar_menu import sidebar_menu


ROOT = Path(__file__).resolve().parents[3]
RRQA_FILES = re.compile(r"measurements_rrqa_(\d{4})_(\d{2})_(.+)\.parquet")
DATE_COLUMNS = ("measurement_date", "date", "periodo", "period_end")
QUALITY_COLUMNS = ("quality_status", "integration_quality_status", "validation_status")


@st.cache_data(max_entries=12, show_spinner=False)
def read_data(path: Path, modified_ns: int, size: int) -> pd.DataFrame:
    if path.suffix == ".csv":
        return pd.read_csv(path, low_memory=False)
    return pd.read_parquet(path)


def load_data(path: Path) -> pd.DataFrame | None:
    try:
        stat = path.stat()
        return read_data(path, stat.st_mtime_ns, stat.st_size)
    except FileNotFoundError:
        st.warning("File assente in questa installazione.")
    except (OSError, ValueError, ImportError) as error:
        st.error(f"Impossibile leggere il file: {error}")
    return None


def periods_for(data: pd.DataFrame, monthly: bool) -> pd.Series:
    year_col = next((name for name in ("year", "anno") if name in data), None)
    month_col = next((name for name in ("month", "mese") if name in data), None)
    if year_col is not None:
        years = pd.to_numeric(data[year_col], errors="coerce").astype("Int64").astype("string")
        if monthly and month_col is not None:
            month = pd.to_numeric(data[month_col], errors="coerce").astype("Int64")
            return years + "-" + month.where(month.between(1, 12)).astype("string").str.zfill(2)
        return years
    date_col = next((name for name in DATE_COLUMNS if name in data), None)
    if date_col:
        return pd.to_datetime(data[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    return pd.Series(pd.NA, index=data.index, dtype="string")


def describe(dataset: Dataset) -> None:
    st.subheader(dataset.name)
    st.caption(f"Fonte: {dataset.source} · Frequenza: {dataset.frequency}")
    st.caption(dataset.path)
    if dataset.group == "Comune mensile":
        st.caption("Le campagne principali usano dati 2021–2024. La fonte ISTAT dei decessi include pubblicazioni provvisorie, soggette a revisione.")
    if dataset.name == "Pannello integrato salute e aria":
        st.caption("Le righe rappresentano combinazioni di comune, anno, indicatore, patologia e inquinante. Le variabili di idoneità distinguono le combinazioni utilizzabili nelle analisi.")
    data = load_data(ROOT / dataset.path)
    if data is None:
        return

    territory = dataset.territory
    periods = periods_for(data, dataset.frequency == "Mensile")
    known_periods = sorted(periods.dropna().unique())
    span = "—"
    if known_periods:
        span = str(known_periods[0]) if len(known_periods) == 1 else f"{known_periods[0]} – {known_periods[-1]}"
    a, b, c = st.columns(3)
    a.metric("Righe nell’archivio", f"{len(data):,}".replace(",", "."))
    b.metric("Periodo osservato", span)
    if territory and territory in data:
        label = {"asl": "ASL", "codice_comune": "Comuni", "municipality_code": "Comuni", "source_station_id": "Stazioni"}.get(territory, "Territori")
        c.metric(label, data[territory].nunique())
    else:
        c.metric("Periodi osservati", len(known_periods))

    a, b = st.columns(2)
    years = sorted(periods.dropna().str[:4].unique())
    picked_year = a.selectbox("Anno", ["Tutti", *years], key=f"year_{dataset.path}")
    filtered = data if picked_year == "Tutti" else data.loc[periods.str[:4].eq(picked_year).fillna(False)]
    if territory and territory in filtered:
        locations = sorted(filtered[territory].dropna().astype(str).unique())
        picked_location = b.selectbox("Territorio", ["Tutti", *locations], key=f"territory_{dataset.path}")
        if picked_location != "Tutti":
            filtered = filtered.loc[filtered[territory].astype(str).eq(picked_location)]

    st.subheader("Copertura e controlli")
    observed = periods.loc[filtered.index].value_counts().sort_index()
    if not observed.empty:
        coverage = observed.rename("Righe").to_frame()
        if territory and territory in filtered:
            coverage["Territori"] = filtered.groupby(periods.loc[filtered.index])[territory].nunique()
        metric = "Territori" if "Territori" in coverage else "Righe"
        timeline = coverage.rename_axis("Periodo").reset_index()
        st.plotly_chart(
            px.bar(timeline, x="Periodo", y=metric, title=f"{metric} per periodo").update_xaxes(type="category"),
            use_container_width=True,
        )
        st.dataframe(coverage.rename_axis("Periodo"), use_container_width=True)
    if filtered.empty:
        st.info("Nessuna riga corrisponde ai filtri.")
        return
    if dataset.key and set(dataset.key).issubset(filtered.columns):
        key = list(dataset.key)
        duplicates = int(filtered.duplicated(key, keep=False).sum())
        incomplete = int(filtered[key].isna().any(axis=1).sum())
        st.caption(f"Chiave osservazione: {', '.join(key)}. Righe con chiave ripetuta: {duplicates}. Righe con chiave incompleta: {incomplete}.")

    for column in ("population", "population_40plus", "population_65plus", "pop_totale", "pop_65plus"):
        if column in filtered:
            population = pd.to_numeric(filtered[column], errors="coerce")
            st.caption(f"Denominatore {column}: {int(population.le(0).sum())} valori presenti ma non positivi.")

    missing = filtered.isna().sum()
    summary = pd.DataFrame({"Campo": missing.index, "Mancanti": missing.values, "Mancanti (%)": (100 * missing / len(filtered)).round(2).values})
    st.caption(f"{len(filtered)} righe selezionate. Le percentuali si riferiscono alle righe selezionate.")
    summary = summary.sort_values(["Mancanti", "Campo"], ascending=[False, True])
    incomplete_fields = summary.loc[summary["Mancanti"] > 0].head(12)
    if not incomplete_fields.empty:
        st.plotly_chart(
            px.bar(
                incomplete_fields.iloc[::-1], x="Mancanti (%)", y="Campo",
                orientation="h", title="Campi con più valori mancanti",
                range_x=[0, 100],
            ),
            use_container_width=True,
        )
    st.dataframe(summary, hide_index=True, use_container_width=True)

    checks = []
    for column in filtered:
        if column in QUALITY_COLUMNS or pd.api.types.is_bool_dtype(filtered[column]) or column in ("suppressed", "anno_parziale"):
            for value, count in filtered[column].value_counts(dropna=False).items():
                checks.append({"Controllo": column, "Valore": "Mancante" if pd.isna(value) else str(value), "Righe": count})
    if checks:
        with st.expander("Esiti registrati dei controlli e criteri di idoneità"):
            st.dataframe(pd.DataFrame(checks), hide_index=True, use_container_width=True)
    with st.expander("Anteprima delle prime 100 righe selezionate"):
        st.dataframe(filtered.head(100), hide_index=True, use_container_width=True)


def show_station_archive() -> None:
    partitions = {}
    for path in sorted((ROOT / DATA).glob("measurements_rrqa_*.parquet")):
        match = RRQA_FILES.fullmatch(path.name)
        if match:
            year, month, pollutant = match.groups()
            partitions[(year, month, pollutant)] = path
    if not partitions:
        st.info("Nessun archivio mensile RRQA trovato in questa installazione.")
        return
    rows = [{"Mese": f"{year}-{month}", "Inquinante": pollutant.upper()} for year, month, pollutant in partitions]
    st.caption(f"{len(rows)} file RRQA mensili disponibili. Ogni riga indica un file presente per mese e inquinante.")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    selected = st.selectbox("Archivio mensile da controllare", list(partitions), format_func=lambda key: f"{key[0]}-{key[1]} · {key[2].upper()}")
    path = partitions[selected]
    describe(Dataset("ARPA RRQA", "Misure di stazione", path.relative_to(ROOT).as_posix(), "ARPA Puglia", "Misure RRQA", "source_station_id", STATION_KEY))


st.set_page_config(page_title="Qualità e copertura dei dati", layout="wide")
st.title("Qualità e copertura dei dati")
st.write(
    "Qui puoi verificare quali dati usa OneHealthAI, quali anni e territori coprono e dove mancano dei valori. "
    "Scegli una voce nel menu a sinistra, poi usa i filtri per consultare gli archivi e i grafici."
)
section = sidebar_menu(
    "Esplora i dati",
    (
        "Catalogo", "Controlla un dataset", "Vista storica", "Dati recenti",
        "Grafici ASL 2021–2023", "Archivi RRQA per mese", "Tracciabilità del dato",
    ),
    key="quality_section",
)
if section == "Catalogo":
    st.write("Consulta la lista degli archivi e le relative fonti. Usa Controlla un dataset per approfondire gli anni, i territori e la completezza di un file.")
    st.dataframe(pd.DataFrame([
        {"Area": item.group, "Dataset": item.name, "Fonte": item.source, "Frequenza": item.frequency,
         "Stato": "Disponibile" if (ROOT / item.path).is_file() else "File assente"}
        for item in CATALOG
    ]), hide_index=True, use_container_width=True)
    st.caption("Per le misure operative e l’elenco delle stazioni del database, usa Decision Support System → Monitoraggio territoriale.")
    st.caption("Nella sezione Controlla un dataset, periodi, conteggi e completezza si calcolano dai file presenti. Gli aggiornamenti descrittivi possono coprire periodi diversi da quelli delle analisi.")
elif section == "Controlla un dataset":
    st.write("Scegli l’area e l’archivio. Usa i filtri per verificare quantità di dati, valori mancanti e controlli di qualità per anno e territorio.")
    group = st.selectbox("Area", list(dict.fromkeys(item.group for item in CATALOG)))
    candidates = {item.name: item for item in CATALOG if item.group == group}
    name = st.selectbox("Dataset", list(candidates))
    describe(candidates[name])
elif section == "Vista storica":
    st.write("Scegli Ambiente o Salute nella barra laterale, poi seleziona l’ASL e l’indicatore. Verifica gli anni disponibili prima di confrontare i grafici.")
    topic = sidebar_menu("Serie", ("Ambiente", "Salute"), key="quality_history_topic")
    if topic == "Ambiente":
        render_environment_history()
    else:
        render_health_history()
elif section == "Dati recenti":
    render_recent_data()
elif section == "Grafici ASL 2021–2023":
    st.write("Usa i filtri a sinistra per esplorare la prevalenza per fascia d’età e ASL, le esposizioni annuali e il confronto descrittivo tra ambiente e salute.")
    render_asl_quality_charts()
elif section == "Tracciabilità del dato":
    render_data_lineage()
else:
    st.write("Scegli un file per mese e inquinante per consultare le osservazioni RRQA per stazione. I filtri mostrano la copertura e i valori mancanti del file scelto.")
    show_station_archive()
