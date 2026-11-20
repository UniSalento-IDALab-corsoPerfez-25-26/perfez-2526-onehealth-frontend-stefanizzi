"""Explain the available research and its methods before presenting results."""
import streamlit as st


def render_research_overview(navigate):
    st.write(
        "Qui puoi esplorare i dati e le analisi sul rapporto tra qualità dell’aria e salute in Puglia. "
        "Le ricerche affrontano due domande: le variazioni degli inquinanti si accompagnano a variazioni "
        "degli indicatori sanitari? Aggiungere i dati ambientali aiuta a prevedere meglio questi indicatori?"
    )
    st.subheader("Cosa puoi consultare")
    left, middle, right = st.columns(3, gap="medium")
    with left, st.container(border=True):
        st.markdown("#### Serie storiche")
        st.write("Segui l’andamento degli inquinanti, dei ricoveri e della mortalità nelle ASL. "
                 "Scegli ambiente o salute, poi territorio e indicatore. Le interruzioni mostrano gli anni senza dati utilizzabili.")
        if st.button("Esplora le serie", key="research_overview_series", use_container_width=True):
            navigate("Serie storiche")
    with middle, st.container(border=True):
        st.markdown("#### Relazioni tra ambiente e salute")
        st.write("Affianca le serie annuali e consulta le associazioni statistiche comunali annuali e mensili. "
                 "Le stime e gli intervalli di confidenza aiutano a distinguere l’associazione osservata dalla sua incertezza.")
        if st.button("Confronta le serie", key="research_overview_comparison", use_container_width=True):
            navigate("Ambiente–salute")
        if st.button("Consulta le associazioni", key="research_overview_associations", use_container_width=True):
            navigate("Modelli e validazione", "Risultati annuali e mensili")
    with right, st.container(border=True):
        st.markdown("#### Previsioni e validazione")
        st.write("Confronta gli errori dei modelli e verifica se gli inquinanti aggiungono informazione allo storico sanitario. "
                 "Puoi consultare sia i risultati complessivi sia le valutazioni ripetute su anni successivi.")
        if st.button("Confronta i modelli", key="research_overview_models", use_container_width=True):
            navigate("Modelli e validazione", "Benchmark ML")
        if st.button("Apri i risultati annuali e mensili", key="research_overview_results", use_container_width=True):
            navigate("Modelli e validazione", "Risultati annuali e mensili")

    st.subheader("Capire le previsioni con XAI")
    st.write("Nella sezione Spiegazioni XAI trovi i contributi dei modelli Ridge annuali ASL e mensili comunali, oltre alle quattro configurazioni XGBoost per ricoveri e mortalità BPCO con NO₂ o PM₂.₅. "
             "Puoi leggere la spiegazione di una singola previsione e l’importanza delle variabili sulle ASL del test annuale. "
             "Le spiegazioni riguardano i modelli disponibili, non tutti gli algoritmi delle campagne.")
    if st.button("Apri le spiegazioni XAI", key="research_overview_xai"):
        navigate("Spiegazioni XAI")

    st.subheader("Le ricerche disponibili")
    st.markdown(
        "- **ASL annuale.** Ricoveri nel 2010–2024 e mortalità per causa nel 2010–2023, "
        "per le sei ASL pugliesi. Le analisi esaminano 23 esiti sanitari e confrontano anche finestre di esposizione di più anni.\n"
        "- **Comune annuale.** Incidenza e prevalenza di BPCO, diabete, ipertensione e scompenso cardiaco "
        "nel 2020–2024. Il collegamento con le misure ambientali locali riguarda i comuni e gli anni con copertura adeguata; "
        "i test predittivi considerano il 2023–2024.\n"
        "- **Comune mensile.** Mortalità per tutte le età e per i residenti di almeno 65 anni nel 2021–2024, "
        "collegata a NO₂, PM₁₀ e meteorologia. Le campagne V5–V7 studiano le associazioni; "
        "V8 valuta la previsione dei decessi del mese successivo. Le analisi preliminari con periodi diversi "
        "sono identificate nei risultati."
    )
    st.caption("I periodi sanitari non coincidono necessariamente con la disponibilità ambientale. "
               "Ogni risultato riguarda il campione effettivamente utilizzabile per quell’analisi.")

    st.subheader("Come sono state eseguite")
    st.caption("Fonti utilizzate: HFA e ISTAT, AReSS Open Salute, ARPA Puglia e rianalisi meteorologiche tramite Open-Meteo.")
    st.markdown(
        "1. **Preparazione dei dati.** Le fonti sanitarie, ambientali, meteorologiche e demografiche sono state "
        "collegate attraverso territorio e periodo. Le concentrazioni ambientali sono state ricostruite dai file originali ARPA "
        "con criteri di aggregazione espliciti. Dati mancanti e valori esclusi non sono stati trasformati in zero.\n"
        "2. **Analisi delle associazioni.** I modelli confrontano ciascun territorio con sé stesso nel tempo, "
        "tenendo conto delle caratteristiche territoriali e dei controlli temporali previsti dal protocollo. "
        "Nella linea mensile sono stati confrontati diversi controlli meteorologici e ritardi dell’esposizione. "
        "Quando si esaminano molti confronti, si applica una correzione statistica per contenere i risultati positivi casuali.\n"
        "3. **Valutazione delle previsioni.** I modelli vengono addestrati sui periodi precedenti e valutati su periodi successivi. "
        "Le configurazioni con e senza inquinanti sono confrontate sulle stesse osservazioni. "
        "I riferimenti includono la persistenza, che riutilizza l’ultimo valore sanitario o quello dello stesso mese dell’anno precedente, "
        "e algoritmi come Ridge, Random Forest, Gradient Boosting e XGBoost, secondo la campagna."
    )
    st.caption("Le medie meteorologiche annuali sono indicatori sintetici: non descrivono stagionalità o episodi estremi. "
               "Nelle prove mensili è stato valutato separatamente l’arricchimento con meteo e inquinanti.")

    with st.expander("Come leggere grafici e risultati"):
        st.write("Il MAE è l’errore assoluto medio: più è basso, migliore è la previsione. "
                 "Un guadagno positivo indica una riduzione dell’errore rispetto al riferimento dichiarato. "
                 "Per le associazioni, l’intervallo di confidenza descrive l’incertezza della stima: "
                 "per un rapporto dei tassi, un intervallo che comprende 1 è compatibile anche con assenza di associazione. "
                 "Un confronto visivo o un miglioramento predittivo, da soli, non dimostrano un rapporto di causa ed effetto.")
    st.caption("Per iniziare: apri una serie storica, scegli un territorio e un indicatore; "
               "poi passa a Modelli e validazione per esaminare i risultati dei confronti.")
