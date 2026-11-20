"""Explain temporal aggregation without implying untested weather benefits."""
import pandas as pd

ANNUAL_WEATHER_NOTE = (
    'Le medie annuali riassumono le condizioni dell’anno: non descrivono le differenze tra stagioni, '
    'le ondate di calore o gli episodi di freddo intenso. Nella ricerca sono state usate come '
    'informazioni sintetiche; la loro presenza nei modelli non dimostra un controllo completo '
    'della meteorologia né un miglioramento della previsione. Il meteo non entra nel punteggio delle priorità territoriali.'
)
MONTHLY_WEATHER_NOTE = (
    'Questi valori si riferiscono al singolo mese e mantengono più dettaglio stagionale rispetto alle medie annue, '
    'ma non descrivono tutti gli episodi giornalieri. Nelle campagne V5–V7 il meteo è stato usato '
    'nei controlli delle associazioni; in V8 è stato valutato come informazione predittiva aggiuntiva.'
)

def weather_note(dataset):
    name=dataset.name.lower()
    if not any(word in name for word in ('meteorolog','meteo','umidità','vento')):return None
    return MONTHLY_WEATHER_NOTE if dataset.frequency=='Mensile' else ANNUAL_WEATHER_NOTE


def split_weather_periods(frame):
    """Keep full calendar years and partial-year observations distinct."""
    partial=pd.Series(False,index=frame.index)
    if 'meteo_is_full_year' in frame:
        partial |= frame.meteo_is_full_year.astype('string').str.lower().isin(['false','0'])
    for column in ('quality_status','meteo_quality_status'):
        if column in frame:
            partial |= frame[column].astype('string').str.contains('PARTIAL_YEAR|ANNO_PARZIALE|PARZIALE_ANNO',case=False,na=False)
    return frame.loc[~partial].copy(),frame.loc[partial].copy()
