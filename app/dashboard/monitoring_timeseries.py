"""Separate monitoring pollutants/provinces and apply a disclosed display exclusion."""
from pathlib import Path
import pandas as pd


def prepare_series(frame, pollutant):
    data=frame.copy()
    data['date']=pd.to_datetime(data['date'],errors='coerce').dt.normalize()
    data['mean_value']=pd.to_numeric(data['mean_value'],errors='coerce')
    data=data.loc[data['pollutant'].eq(pollutant) & data.date.notna()].copy()
    excluded=(data['pollutant'].eq('SO2') & data['province'].astype(str).str.strip().str.casefold().eq('lecce') &
              data['date'].eq(pd.Timestamp('2025-07-30')) & data['mean_value'].sub(420).abs().lt(1e-6))
    removed=data.loc[excluded].copy()
    data.loc[excluded,'mean_value']=float('nan')
    parts=[]
    for province,part in data.groupby('province',dropna=False):
        part=part.sort_values('date')
        if part['date'].duplicated().any():raise ValueError('Più valori per la stessa provincia e giornata: controllare la risposta del servizio.')
        calendar=pd.date_range(part.date.min(),part.date.max(),freq='D')
        part=part.set_index('date').reindex(calendar).rename_axis('date').reset_index()
        part['province']=province;part['pollutant']=pollutant
        parts.append(part)
    return pd.concat(parts,ignore_index=True) if parts else data,removed


def unit_for(pollutant, latest):
    if {'pollutant','unit'}.issubset(latest):
        values=latest.loc[latest.pollutant.eq(pollutant),'unit'].dropna().unique()
        if len(values)==1:return str(values[0])
    path=Path(__file__).resolve().parents[2]/'data/raw/pollutants.csv'
    if path.is_file():
        metadata=pd.read_csv(path)
        values=metadata.loc[metadata.sigla.eq(pollutant),'unita_misura'].dropna().unique()
        if len(values)==1:return str(values[0])
    return 'unità non disponibile'


def render_monitoring_series(payload, pollutant, latest):
    import streamlit as st
    import plotly.express as px
    frame=pd.DataFrame(payload.get('series',[]))
    if frame.empty:
        st.info('Nessuna misura per i filtri selezionati.');return
    data,removed=prepare_series(frame,pollutant)
    if data.empty:
        st.info('Nessuna misura per questo inquinante e territorio.');return
    unit=unit_for(pollutant,latest)
    st.caption(f'{pollutant} · {unit}. Ogni linea rappresenta una provincia. '
               'Il valore riassume le misure pubblicate dalle stazioni disponibili nella giornata; '
               'il numero di stazioni può cambiare. Le interruzioni indicano dati mancanti o esclusi.')
    figure=px.line(data,x='date',y='mean_value',color='province',markers=True,
                  hover_data=['min_value','max_value','valid_values'],
                  labels={'date':'Data','mean_value':f'Valore medio tra stazioni ({unit})','province':'Provincia',
                          'min_value':'Minimo tra stazioni','max_value':'Massimo tra stazioni','valid_values':'Misure disponibili'})
    figure.update_traces(connectgaps=False)
    st.plotly_chart(figure,use_container_width=True)
    if not removed.empty:
        st.caption('Esclusione dalla visualizzazione: SO₂, provincia di Lecce, 30 luglio 2025, '
                   '420 µg/m³ (stazione Surbo – Croce). Il punto è escluso su richiesta e resta '
                   'conservato nei dati originali; non è stato accertato che sia un errore di misura.')
    with st.expander('Valori rappresentati nel grafico'):
        st.dataframe(data,hide_index=True,use_container_width=True)
