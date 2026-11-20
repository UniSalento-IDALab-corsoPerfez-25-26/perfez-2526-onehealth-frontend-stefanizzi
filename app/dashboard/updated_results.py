"""Present the recomputed annual and monthly experiments without stale results."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2] / 'reports/research/risultati_ricalcolati'

def render_updated_results():
    st.subheader('Risultati delle analisi annuali e mensili')
    st.write('Questa sezione mostra se aggiungere gli inquinanti aiuta a descrivere o prevedere gli indicatori sanitari. '
             'Le analisi usano le concentrazioni ricostruite dai file originali ARPA. '
             'Un miglioramento della previsione non dimostra un rapporto di causa ed effetto.')
    view = st.selectbox('Analisi da consultare', ['Comune annuale · previsione', 'Comune annuale · associazioni',
                          'Comune mensile · previsione', 'Comune mensile · associazioni'])
    names = ['Tabella_comunale_annuale_ML_160.csv', 'Tabella_comunale_annuale_regressioni.csv',
             'Tabella_mensile_V8_Ridge.csv', 'Tabella_mensile_V7_principale.csv']
    try:
        frame = pd.read_csv(ROOT / names[['Comune annuale · previsione', 'Comune annuale · associazioni',
                          'Comune mensile · previsione', 'Comune mensile · associazioni'].index(view)])
    except (OSError, ValueError):
        st.info('Risultati non disponibili in questa installazione.'); return
    if view == 'Comune annuale · previsione':
        wins = int(frame.improvement_due_to_pollutant_pct.gt(0).sum())
        a,b = st.columns(2)
        a.metric('Confronti con errore ridotto', f'{wins} / {len(frame)}')
        b.metric('Percentuale di miglioramenti', f'{100*wins/len(frame):.1f}%')
        st.caption('Test sul 2023 e 2024. Si confrontano lo stesso algoritmo e le stesse osservazioni con e senza inquinante. '
                   'Il guadagno è positivo quando il MAE, cioè l’errore assoluto medio, diminuisce. '
                   'I confronti condividono dati e non sono esperimenti indipendenti.')
        pollutant = st.selectbox('Inquinante', ['Tutti', *sorted(frame.pollutant.unique())])
        shown = frame if pollutant == 'Tutti' else frame[frame.pollutant.eq(pollutant)]
        st.plotly_chart(px.histogram(shown, x='improvement_due_to_pollutant_pct', nbins=25,
                        labels={'improvement_due_to_pollutant_pct':'Riduzione del MAE (%)'}), use_container_width=True)
    elif view == 'Comune mensile · previsione':
        st.caption('Previsione a un mese, valutata sul 2023–2024. A usa storico sanitario, demografia e calendario; '
                   'B aggiunge il meteo essenziale, C il meteo esteso e D anche gli inquinanti. '
                   'Il MAE è espresso in decessi per comune e mese: più è basso, migliore è la previsione.')
        frame['Scenario'] = frame.pollutant + ' · ' + frame.outcome.replace({'decessi_totali':'Tutte le età','decessi_65plus':'65+'})
        st.plotly_chart(px.bar(frame, x='Scenario', y='mae', color='configuration', barmode='group',
                              labels={'mae':'MAE (decessi per comune–mese)','configuration':'Configurazione'}), use_container_width=True)
        st.info('In tutti e quattro gli scenari, Ridge con la configurazione A ottiene l’errore più basso.')
    else:
        st.caption('Le associazioni confrontano ciascun comune nel tempo, tenendo conto dei fattori previsti dal modello. '
                   'Un rapporto dei tassi (RR) pari a 1 indica assenza di variazione stimata; '
                   'se l’intervallo di confidenza include 1, il risultato è compatibile anche con assenza di associazione.')
        if view.startswith('Comune annuale'):
            st.info('Nessun confronto secondario supera la correzione per i numerosi test effettuati.')
        else:
            st.info('Tutti i quattro intervalli di confidenza principali comprendono 1.')
    st.dataframe(frame, hide_index=True, use_container_width=True)
    st.download_button('Scarica i risultati visualizzati', frame.to_csv(index=False), file_name='risultati_analisi.csv', mime='text/csv')
