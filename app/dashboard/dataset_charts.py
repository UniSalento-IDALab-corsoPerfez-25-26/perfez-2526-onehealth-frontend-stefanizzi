"""Explore every catalogued dataset with explicit dimensions and aggregation."""
from pathlib import Path
import re
import pandas as pd
import plotly.express as px
import streamlit as st
from app.dashboard.data_quality_catalog import CATALOG, Dataset, STATION_KEY
from app.dashboard.territory_labels import readable_territories, representative_selection
from app.dashboard.weather_context import weather_note

ROOT = Path(__file__).resolve().parents[2]
LABELS = {
 'value':'Valore osservato', 'target_t_plus_1':'Indicatore sanitario dell’anno successivo',
 'no2_mean':'Concentrazione media NO₂ (µg/m³)', 'o3_mean':'Concentrazione media O₃ (µg/m³)',
 'pm10_mean':'Concentrazione media PM₁₀ (µg/m³)', 'pm25_mean':'Concentrazione media PM₂.₅ (µg/m³)',
 'meteo_temperature_mean':'Temperatura media', 'meteo_humidity_mean':'Umidità relativa media',
 'meteo_wind_mean':'Velocità media del vento',
 'mean_value':'Concentrazione media (µg/m³)', 'monitor_annual_mean_ug_m3':'Concentrazione media annuale (µg/m³)',
 'monitor_month_mean_ug_m3':'Concentrazione media mensile (µg/m³)',
 'prevalence_per_1000':'Prevalenza per 1.000 abitanti', 'crude_per_1000':'Tasso grezzo per 1.000 abitanti',
 'standardized_per_1000':'Tasso standardizzato per 1.000 abitanti', 'cases':'Casi', 'population':'Popolazione di riferimento',
 'population_40plus':'Popolazione dai 40 anni', 'population_65plus':'Popolazione dai 65 anni',
 'sex':'Sesso', 'age_group':'Fascia di età', 'pathology':'Patologia', 'indicator':'Tipo di indicatore',
 'indicator_code':'Indicatore sanitario', 'outcome':'Esito sanitario', 'pollutant':'Inquinante',
 'pollutant_code':'Inquinante', 'asl':'ASL', 'codice_comune':'Comune (codice ISTAT)',
 'municipality_code':'Comune (codice ISTAT)', 'source_station_id':'Stazione', 'metric':'Unità di misura',
 'coverage_fraction':'Quota di copertura (0–1)', 'availability_percent':'Copertura (%)',
 'decessi_totali':'Decessi, tutte le età', 'decessi_65plus':'Decessi, almeno 65 anni',
}
DIMENSIONS = ('indicator_code','hfa_indicator_code','pathology','indicator','outcome','pollutant_code','pollutant','sex','age_group','age','metric','network','unit')
TIME = {'year','anno','month','mese','day','giorno','target_year','feature_year','hfa_row_index'}


def label(column):
    return LABELS.get(column, column.replace('_',' '))

@st.cache_data(max_entries=8, show_spinner=False)
def read_frame(path, modified_ns):
    return pd.read_csv(path, low_memory=False) if path.suffix == '.csv' else pd.read_parquet(path)


def periods(frame):
    year = next((c for c in ('year','anno') if c in frame),None)
    month = next((c for c in ('month','mese') if c in frame),None)
    if year:
        data = {'year':pd.to_numeric(frame[year],errors='coerce'),'month':1,'day':1}
        if month:data['month']=pd.to_numeric(frame[month],errors='coerce')
        return pd.to_datetime(pd.DataFrame(data,index=frame.index),errors='coerce'), 'MS' if month else 'YS'
    date = next((c for c in ('measurement_date','date','periodo','period_start','period_end') if c in frame),None)
    if date:return pd.to_datetime(frame[date],errors='coerce',utc=True).dt.tz_localize(None),'D'
    return pd.Series(pd.NaT,index=frame.index,dtype='datetime64[ns]'),None


def numeric_columns(frame):
    return [c for c in frame if c not in TIME and c not in DIMENSIONS and not c.endswith('_original') and
            not re.search(r'(^id$|_id$|code|codice|latitude|longitude|^lat$|^lon$)',c) and
            pd.api.types.is_numeric_dtype(frame[c]) and not pd.api.types.is_bool_dtype(frame[c])]


def temporal_summary(frame, column, territory, agg, freq):
    keys=['Periodo'] + ([territory] if territory and territory in frame else [])
    # A mean/median is descriptive. Never add rates or repeated population denominators.
    grouped=frame.groupby(keys,dropna=False)[column].agg(agg).reset_index()
    if freq and not grouped.empty:
        parts=[]
        for name,part in (grouped.groupby(territory,dropna=False) if territory else [(None,grouped)]):
            calendar=pd.date_range(part.Periodo.min(),part.Periodo.max(),freq=freq)
            part=part.set_index('Periodo').reindex(calendar).rename_axis('Periodo').reset_index()
            if territory:part[territory]=name
            parts.append(part)
        grouped=pd.concat(parts,ignore_index=True)
    return grouped


def render_dataset_charts():
    st.subheader('Grafici dei dataset')
    st.write('Esplora salute, ambiente, meteorologia e popolazione nei periodi disponibili. '
             'Scegli un dataset, seleziona l’indicatore e usa i filtri per confrontare anni, territori, sesso e fasce d’età. '
             'Ogni grafico riguarda un solo archivio: fonti e scale diverse restano separate.')
    catalog=list(CATALOG)
    for path in sorted((ROOT/'data/processed').glob('measurements_rrqa_*.parquet')):
        catalog.append(Dataset('Archivi RRQA mensili',path.stem,path.relative_to(ROOT).as_posix(),'ARPA Puglia','Misure RRQA','source_station_id',STATION_KEY))
    group=st.selectbox('Famiglia di dati',list(dict.fromkeys(d.group for d in catalog)),key='charts_group')
    candidates=[d for d in catalog if d.group==group]
    name=st.selectbox('Dataset da visualizzare',[d.name for d in candidates],key='charts_dataset')
    dataset=next(d for d in candidates if d.name==name);path=ROOT/dataset.path
    st.caption(f'Fonte: {dataset.source} · Frequenza: {dataset.frequency}')
    note=weather_note(dataset)
    if note:st.caption(note)
    if not path.is_file():
        st.info('Questo archivio non è presente nell’installazione. Scegli un altro dataset.');return
    try:frame=read_frame(path,path.stat().st_mtime_ns).copy()
    except (OSError,ValueError,ImportError) as exc:
        st.error(f'Archivio non leggibile: {exc}');return
    if frame.empty:st.info('Il dataset non contiene osservazioni.');return
    dates,freq=periods(frame);frame['Periodo']=dates
    frame,actual_territory=readable_territories(frame,dataset.territory)
    geo='Provincia' if 'Provincia' in frame else ('asl' if 'asl' in frame else None)
    selected_geo='Tutte'
    if geo:
        choices=sorted(frame[geo].dropna().astype(str).unique())
        selected_geo=st.selectbox('Provincia' if geo=='Provincia' else 'ASL da esplorare',['Tutte',*choices],key=f'chart_{dataset.path}_geo')
        if selected_geo!='Tutte':frame=frame.loc[frame[geo].astype(str).eq(selected_geo)]
        st.caption(f'{len(choices)} '+('province' if geo=='Provincia' else 'ASL')+' disponibili nel dataset prima dei filtri sugli indicatori.')
    elif actual_territory is None:
        st.caption('Questo archivio contiene dati aggregati: non dispone di un dettaglio provinciale selezionabile.')
    token=f'{dataset.path}_{selected_geo}'
    comparisons=list(dict.fromkeys(c for c in (actual_territory,'age_group','sex','age') if c and c in frame))
    comparison=st.selectbox('Dimensione di confronto',comparisons,format_func=label,key=f'chart_{token}_comparison') if comparisons else None
    with st.expander('Filtri degli indicatori e della popolazione',expanded=True):
        for col in DIMENSIONS:
            if col not in frame or col == comparison:continue
            options=sorted(frame[col].dropna().astype(str).unique())
            if not options:continue
            # One category at a time avoids mixing pathogens, pollutants, age classes or units.
            default=options.index('ALL') if 'ALL' in options else 0
            selected=st.selectbox(label(col),options,index=default,key=f'chart_{token}_{col}')
            frame=frame.loc[frame[col].astype(str).eq(selected)]
    eligible=next((c for c in ('analysis_eligible','qualified_annual','ml_eligible') if c in frame),None)
    if eligible and st.checkbox('Solo osservazioni idonee secondo i controlli disponibili',value=True,key=f'chart_{token}_eligible'):
        frame=frame.loc[frame[eligible].eq(True)]
    years=sorted(frame.Periodo.dropna().dt.year.unique())
    years_choice=st.multiselect('Anni da includere',years,default=years,key=f'chart_{token}_years') if years else []
    if years:frame=frame.loc[frame.Periodo.dt.year.isin(years_choice)]
    territory=comparison
    actual=actual_territory if actual_territory in frame else None
    if actual and actual != comparison:
        locations=sorted(frame[actual].dropna().astype(str).unique())
        if locations:
            location=st.selectbox('Territorio di riferimento',locations,key=f'chart_{token}_reference')
            frame=frame.loc[frame[actual].astype(str).eq(location)]
    if territory:
        options=sorted(frame[territory].dropna().astype(str).unique())
        initial=[v for v in options if v not in ('ALL','All','Totale','TOTAL')] or options
        chosen=st.multiselect(label(territory)+' da confrontare',options,default=representative_selection(frame,territory,initial),key=f'chart_{token}_territories_{territory}')
        frame=frame.loc[frame[territory].astype(str).isin(chosen)].copy()
        frame[territory]=frame[territory].astype(str)
        st.caption('La selezione iniziale comprende al massimo sei categorie; quando possibile include province diverse. Puoi modificarla o aggiungerne altre.')
    if frame.empty:st.info('Nessuna osservazione per i filtri selezionati.');return
    cols=numeric_columns(frame)
    if not cols:st.info('Questo archivio non contiene misure numeriche rappresentabili con i filtri selezionati.');return
    preferred=next((c for c in ['prevalence_per_1000','crude_per_1000','mean_value','monitor_annual_mean_ug_m3','value','cases'] if c in cols),cols[0])
    measure=st.selectbox('Valore da rappresentare',cols,index=cols.index(preferred),format_func=label,key=f'chart_{token}_measure')
    mode=st.selectbox('Tipo di grafico',['Andamento nel tempo','Confronto per categoria','Distribuzione dei valori','Confronto tra due variabili','Copertura nel tempo'],key=f'chart_{token}_mode')
    aggregation=st.selectbox('Riepilogo di più osservazioni nello stesso punto',['Media','Mediana'],key=f'chart_{token}_aggregation')
    agg='mean' if aggregation=='Media' else 'median'
    st.caption('Quando più righe corrispondono allo stesso punto si usa la media o la mediana selezionata. '
               'I tassi e i denominatori ripetuti non vengono sommati. Il grafico è descrittivo, non un tasso sanitario ricalcolato.')
    frame[measure]=pd.to_numeric(frame[measure],errors='coerce')
    a,b=st.columns(2);a.metric('Righe selezionate',len(frame));b.metric('Valori numerici disponibili',int(frame[measure].notna().sum()))
    title=label(measure)
    if measure in ('value','target_t_plus_1') and 'metric' in frame:
        units=frame.metric.dropna().unique()
        if len(units)==1:
            unit={'crude_rate_per_10000':'Tasso grezzo per 10.000 abitanti'}.get(str(units[0]),str(units[0]))
            title=f'{title} · {unit}'
            st.caption(f'Unità: {unit}')
    chart=None
    if mode=='Andamento nel tempo':
        valid=frame.loc[frame.Periodo.notna()]
        if valid.empty:st.info('Il dataset non contiene una data utilizzabile.')
        else:
            data=temporal_summary(valid,measure,territory,agg,freq)
            chart=px.line(data,x='Periodo',y=measure,color=territory,markers=True,labels={measure:title})
            chart.update_traces(connectgaps=False)
    elif mode=='Confronto per categoria':
        if not territory:st.info('Il dataset non distingue categorie confrontabili. Usa un altro tipo di grafico.')
        else:
            data=frame.groupby(territory)[measure].agg(agg).reset_index()
            chart=px.bar(data,x=territory,y=measure,labels={measure:title,territory:label(territory)})
            st.caption('Se hai incluso più periodi, ogni barra riassume il valore della categoria su quei periodi.')
    elif mode=='Distribuzione dei valori':chart=px.histogram(frame,x=measure,nbins=25,labels={measure:title})
    elif mode=='Confronto tra due variabili':
        other=[c for c in cols if c!=measure]
        if not other:st.info('Non è disponibile una seconda misura numerica.')
        else:
            second=st.selectbox('Seconda variabile',other,format_func=label,key=f'chart_{token}_second')
            chart=px.scatter(frame,x=measure,y=second,color=territory,labels={measure:title,second:label(second)})
            st.caption('Ogni punto è una riga selezionata. Eventuali relazioni visive non dimostrano causalità; le osservazioni possono ripetersi nelle griglie integrate.')
    else:
        valid=frame.loc[frame.Periodo.notna()]
        keys=['Periodo']+([territory] if territory else [])
        data=valid.groupby(keys)[measure].agg(Righe='size',Disponibili='count').reset_index()
        data['Disponibili (%)']=100*data.Disponibili/data.Righe
        chart=px.bar(data,x='Periodo',y='Disponibili (%)',color=territory,barmode='group',range_y=[0,100])
        st.caption('Percentuale di valori presenti nelle righe selezionate del periodo. Non misura i giorni di rilevazione attesi né la copertura di territori assenti dall’archivio.')
    if chart is not None:st.plotly_chart(chart,use_container_width=True)
    with st.expander('Dati usati nel grafico'):
        columns=['Periodo']+([territory] if territory else [])+[measure]
        st.dataframe(frame[columns],hide_index=True,use_container_width=True)
    st.download_button('Scarica i dati selezionati',frame.drop(columns='Periodo').to_csv(index=False),file_name='dati_grafico.csv',mime='text/csv',key=f'chart_{token}_download')
