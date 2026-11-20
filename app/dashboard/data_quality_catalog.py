"""Files used by OneHealthAI and the observation keys for each product."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    group: str
    name: str
    path: str
    source: str
    frequency: str
    territory: str | None
    key: tuple[str, ...]


DATA = "data/processed/"
OH = DATA + "one_health/"
RESEARCH = OH + "research/"
REPORTS = "reports/research/"
MASTER = OH + "master_research_panel_v1/"
MONTHLY_QC = REPORTS + "mensile_epidemiology_ready_v4/"
MONTHLY_METEO = REPORTS + "mensile_meteo_integrato_v2/"
MONTHLY_V7 = REPORTS + "mensile_meteo_epidemiologia_v7_EXPLORATORY/"
ASL_POP_KEY = ("year", "asl", "sex", "age_group")
ASL_HEALTH_KEY = ("indicator_code", "year", "asl", "sex", "age_group")
HFA_KEY = ("year", "hfa_territory_code", "hfa_indicator_code", "sex")
STATION_KEY = ("measurement_date", "source_station_id", "pollutant_code", "network")
AIR_KEY = ("year", "asl", "pollutant_code")
MUNICIPAL_ANNUAL_KEY = ("codice_comune", "year", "pathology", "indicator")
MUNICIPAL_MONTH_KEY = ("codice_comune", "anno", "mese")
MONTH_POP = RESEARCH + "population_municipality_monthly_v1/"
V7_SOURCE = "ISTAT, ARPA Puglia, ERA5-Land"

CATALOG = (
    Dataset("DSS", "Estensione priorità 2024", OH + "one_health_dss_2024.parquet", "AReSS, ISTAT, ARPA Puglia", "Annuale", "asl", ("year", "indicator_code", "asl")),
    Dataset("DSS", "Master Dataset delle priorità", OH + "one_health_master_2021_2023.parquet", "AReSS, ISTAT, ARPA Puglia", "Annuale", "asl", ASL_HEALTH_KEY),
    Dataset("DSS", "Dataset integrato ASL della validazione iniziale", OH + "one_health_dataset_2021_2023.parquet", "AReSS, ISTAT, ARPA Puglia", "Annuale", "asl", ASL_HEALTH_KEY),
    Dataset("DSS", "Prevalenza sanitaria per ASL", DATA + "health/health_prevalence_2020_2023.parquet", "AReSS, ISTAT", "Annuale", "asl", ASL_HEALTH_KEY),
    Dataset("DSS", "Esposizione ASL del Master Dataset", OH + "environmental_exposure_asl_2021_2023.parquet", "ARPA Puglia", "Annuale", "asl", AIR_KEY),
    Dataset('ASL annuale', 'Esposizioni armonizzate prima dei controlli di idoneità', 'data/processed/one_health/research/environmental_exposure_2010_2025_HARMONIZED.parquet', 'ARPA Puglia', 'Annuale', 'asl', ('year', 'asl', 'pollutant_code')),
    Dataset("ASL annuale", "Ricoveri HFA", RESEARCH + "hfa_hospital_2010_2024_PROVISIONAL.parquet", "HFA", "Annuale", "asl", HFA_KEY),
    Dataset("ASL annuale", "Mortalità HFA", RESEARCH + "hfa_mortality_2010_2023_PROVISIONAL.parquet", "HFA", "Annuale", "asl", HFA_KEY),
    Dataset("ASL annuale", "Ricoveri – pannello per le analisi", RESEARCH + "consolidated_qc_v1/ml_hfa_hospital_CONSOLIDATED_QC_v1.parquet", "HFA, ARPA Puglia, ISTAT, ERA5-Land", "Annuale", "asl", HFA_KEY),
    Dataset("ASL annuale", "Mortalità – pannello per le analisi", RESEARCH + "consolidated_qc_v1/ml_hfa_mortality_CONSOLIDATED_QC_v1.parquet", "HFA, ARPA Puglia, ISTAT, ERA5-Land", "Annuale", "asl", HFA_KEY),
    Dataset("ASL annuale", "Esposizioni storiche con controlli di qualità", RESEARCH + "environmental_exposure_2010_2025_QC_v1.parquet", "ARPA Puglia", "Annuale", "asl", AIR_KEY),
    Dataset("ASL annuale", "Meteorologia storica", DATA + "meteorology/meteorology_asl_historical_2010_2025.parquet", "ERA5-Land", "Annuale", "asl", ("year", "asl")),
    Dataset("ASL annuale", "Popolazione storica", DATA + "demography/population_asl_historical_2006_2023.parquet", "ISTAT", "Annuale", "asl", ASL_POP_KEY),
    Dataset("Comune annuale", "Incidenza e prevalenza delle quattro patologie", MASTER + "master_health_municipal_2020_2024.csv", "AReSS, ISTAT", "Annuale", "codice_comune", MUNICIPAL_ANNUAL_KEY),
    Dataset("Comune annuale", "Monitoraggio ambientale locale", MASTER + "master_arpa_annual_local_monitoring.csv", "ARPA Puglia", "Annuale", "codice_comune", ("codice_comune", "year", "pollutant")),
    Dataset("Comune annuale", "Pannello integrato salute e aria", MASTER + "master_municipal_health_air_grid_2020_2024.csv", "AReSS, ISTAT, ARPA Puglia", "Annuale", "codice_comune", (*MUNICIPAL_ANNUAL_KEY, "pollutant")),
    Dataset('Comune mensile', 'Monitoraggio ARPA mensile per stazione', 'data/processed/one_health/research/arpa_station_monthly_v1/arpa_station_monthly.csv', 'ARPA Puglia', 'Mensile', 'source_station_id', ('source_station_id', 'network', 'pollutant', 'year', 'month')),
    Dataset('Comune mensile', 'Mortalità e monitoraggio locale con ritardi', 'data/processed/one_health/research/municipal_monthly_monitoring_panel_v1/municipality_month_monitoring_wide.csv', 'ISTAT, ARPA Puglia', 'Mensile', 'codice_comune', ('codice_comune', 'year', 'month')),
    Dataset("Comune mensile", "Decessi comunali ISTAT", RESEARCH + "mortalita_totale_comuni_puglia_mensile_v2/decessi_comune_mese.csv", "ISTAT", "Mensile", "codice_comune", MUNICIPAL_MONTH_KEY),
    Dataset("Comune mensile", "Mortalità, monitoraggio e popolazione", MONTH_POP + "pannello_comune_mese_con_popolazione.csv", "ISTAT, ARPA Puglia", "Mensile", "codice_comune", ("codice_comune", "year", "month")),
    Dataset("Comune mensile", "Popolazione comunale usata nelle analisi mensili", MONTH_POP + "popolazione_comune_anno.csv", "ISTAT", "Annuale", "codice_comune", ("codice_comune", "anno")),
    Dataset("Comune mensile", "Pannello con controlli epidemiologici", MONTHLY_QC + "panel_qc_full.csv", "ISTAT, ARPA Puglia", "Mensile", "codice_comune", MUNICIPAL_MONTH_KEY),
    Dataset("Comune mensile", "Meteorologia comunale", MONTHLY_METEO + "meteorology_municipality_monthly.csv", "ERA5-Land", "Mensile", "codice_comune", MUNICIPAL_MONTH_KEY),
    Dataset("Comune mensile", "Pannello integrato con meteorologia", MONTHLY_METEO + "panel_monthly_environment_health_meteo.csv", V7_SOURCE, "Mensile", "codice_comune", MUNICIPAL_MONTH_KEY),
    Dataset("Comune mensile", "Umidità e vento", MONTHLY_V7 + "meteo_extra_mensile_2021_2024.csv", "ERA5-Land", "Mensile", "codice_comune", MUNICIPAL_MONTH_KEY),
    Dataset("Comune mensile", "Campione NO₂ usato nelle campagne V7 e V8", MONTHLY_V7 + "analytic_no2_weather_extended.csv", V7_SOURCE, "Mensile", "codice_comune", MUNICIPAL_MONTH_KEY),
    Dataset("Comune mensile", "Campione PM₁₀ usato nelle campagne V7 e V8", MONTHLY_V7 + "analytic_pm10_weather_extended.csv", V7_SOURCE, "Mensile", "codice_comune", MUNICIPAL_MONTH_KEY),
    Dataset("Aggiornamenti e serie descrittive", "Popolazione ASL aggiornata", DATA + "demography/population_asl_2024_2026.parquet", "ISTAT", "Annuale", "asl", ASL_POP_KEY),
    Dataset("Aggiornamenti e serie descrittive", "Popolazione comunale aggiornata", DATA + "demography/population_municipality_2024_2026.parquet", "ISTAT", "Annuale", "municipality_code", ("year", "municipality_code", "sex", "age")),
    Dataset("Aggiornamenti e serie descrittive", "Meteorologia ASL 2026 parziale", DATA + "meteorology/meteorology_asl_2026_partial.parquet", "ERA5-Land", "Annuale parziale", "asl", ("year", "asl")),
    Dataset("Aggiornamenti e serie descrittive", "Mortalità mensile aggregata della Puglia", REPORTS + "mortalita_mensile_profilo_v1/mensile_puglia_2011_2026.csv", "ISTAT", "Mensile", None, ("anno", "mese")),
    Dataset("Aggiornamenti e serie descrittive", "Misure RRQA del primo semestre 2026", OH + "operational/rrqa_2026_h1_backfill.parquet", "ARPA Puglia", "Misure RRQA", "source_station_id", STATION_KEY),
)
