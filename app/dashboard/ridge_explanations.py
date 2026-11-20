"""Read verified linear Ridge attributions; never retrain from the interface."""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from app.dashboard.experimental_forecasts import format_value, VARIABLES

ROOT=Path(__file__).resolve().parents[2]/'reports/research/ridge_xai'
NAMES={**VARIABLES,'year':'Anno delle informazioni','municipality':'Comune (contributo delle categorie territoriali)',
 'month_sin':'Stagionalità del mese (seno)','month_cos':'Stagionalità del mese (coseno)',
 'known_pop_total':'Popolazione totale dell’anno precedente','known_pop_65plus':'Popolazione 65+ dell’anno precedente',
 'population_65_share_known':'Quota 65+ dell’anno precedente','pm10_mean':'Concentrazione media di PM₁₀',
 'decessi_totali_lag1':'Decessi totali del mese precedente','decessi_totali_lag12':'Decessi totali dello stesso mese dell’anno precedente',
 'decessi_65plus_lag1':'Decessi 65+ del mese precedente','decessi_65plus_lag12':'Decessi 65+ dello stesso mese dell’anno precedente',
 'meteo_temp_mean_lag1':'Temperatura media del mese precedente','rain_log1p_lag1':'Precipitazioni del mese precedente (logaritmo)',
 'meteo_humidity_mean_lag1':'Umidità media del mese precedente','meteo_wind_mean_lag1':'Vento medio del mese precedente'}
for pol,pretty in [('no2','NO₂'),('pm10','PM₁₀')]:
 for lag in (1,2,3):NAMES[f'monitoring_{pol}_lag{lag}']=f'{pretty}: concentrazione di {lag} mesi prima'
DISEASES={'acute_myocardial_infarction':'infarto miocardico acuto','cerebrovascular':'malattie cerebrovascolari',
 'circulatory':'malattie circolatorie','copd':'BPCO','ischemic_heart':'cardiopatie ischemiche',
 'pneumonia_influenza':'polmonite e influenza','respiratory':'malattie respiratorie'}
CONFIG_ANNUAL={'A':'A · Storico sanitario, demografia e meteo','B':'B · Base A con NO₂ e PM₁₀'}
CONFIG_MONTHLY={'A_baseline':'A · Storico sanitario, demografia e calendario','B_meteo_essenziale':'B · A con meteo essenziale',
 'C_meteo_esteso':'C · B con umidità e vento','D_meteo_inquinante':'D · C con inquinante'}

def outcome_name(code):
 if code=='decessi_totali':return 'Decessi, tutte le età'
 if code=='decessi_65plus':return 'Decessi, almeno 65 anni'
 prefix='Ricoveri per ' if code.startswith('hospital_discharge_') else 'Mortalità per '
 name=code.removeprefix('hospital_discharge_').removeprefix('mortality_')
 older=name.endswith('_65plus');name=name.removesuffix('_65plus')
 return prefix+DISEASES.get(name,name.replace('_',' '))+(' · 65+' if older else '')

@st.cache_data(max_entries=5,show_spinner=False)
def load_table(name,modified):
 return pd.read_csv(ROOT/(name+'.csv'),low_memory=False,dtype={'territory':'string'})

def render_ridge_explanations():
 st.subheader('Spiegazioni Ridge')
 st.write('Scegli una previsione già valutata per capire come le variabili l’hanno spostata rispetto al riferimento del modello. '
          'Sono disponibili le serie annuali ASL e la mortalità mensile comunale; la pagina consulta risultati archiviati senza addestrare nuovi modelli.')
 try:
  tables={name:load_table(name,(ROOT/(name+'.csv')).stat().st_mtime_ns) for name in ['cases','local','global','fits','coefficients']}
 except (OSError,ValueError):
  st.info('Le spiegazioni Ridge non sono disponibili in questa installazione.');return
 all_cases=tables['cases'];scale_label=st.selectbox('Scala di analisi',['ASL annuale','Comune mensile'],key='ridge_scale')
 scale='annual' if scale_label=='ASL annuale' else 'monthly'
 filtered=all_cases.loc[all_cases.scale.eq(scale)].copy()
 outcome=st.selectbox('Esito sanitario',sorted(filtered.outcome.unique()),format_func=outcome_name,key='ridge_outcome_'+scale)
 filtered=filtered.loc[filtered.outcome.eq(outcome)]
 configurations=CONFIG_ANNUAL if scale=='annual' else CONFIG_MONTHLY
 config=st.selectbox('Configurazione Ridge',[x for x in configurations if x in filtered.configuration.unique()],format_func=configurations.__getitem__,key='ridge_config_'+scale)
 pool=filtered.copy()
 filtered=filtered.loc[filtered.configuration.eq(config)]
 if scale=='monthly':
  pol=st.selectbox('Campione ambientale',sorted(filtered.pollutant.unique()),format_func=lambda x:{'NO2':'NO₂','PM10':'PM₁₀'}.get(x,x),key='ridge_pollutant')
  pool=pool.loc[pool.pollutant.eq(pol)];filtered=filtered.loc[filtered.pollutant.eq(pol)]
  st.caption('Il campione identifica i comuni con dati disponibili per l’inquinante. In A, B e C l’inquinante non è un predittore, ma il campione resta lo stesso per il confronto con D.')
 periods=sorted(filtered.period.astype(str).unique(),reverse=True)
 period=st.selectbox('Anno previsto' if scale=='annual' else 'Mese previsto',periods,key='ridge_period_'+scale)
 filtered=filtered.loc[filtered.period.astype(str).eq(period)]
 ids=filtered.territory.astype(str).unique().tolist();territory_labels=filtered.set_index('territory').territory_name.to_dict()
 territory=st.selectbox('ASL' if scale=='annual' else 'Comune',sorted(ids,key=lambda x:territory_labels.get(x,x)),format_func=lambda x:territory_labels.get(x,x),key='ridge_territory_'+scale)
 result=filtered.loc[filtered.territory.astype(str).eq(territory)].iloc[0]
 unit='punti del tasso per 10.000 abitanti' if scale=='annual' else 'decessi per comune e mese'
 st.caption('Unità: '+unit+'. Il riferimento è la previsione media sui dati di addestramento di quel modello, non l’ultimo valore sanitario osservato.')
 a,b,c,d=st.columns(4)
 a.metric('Previsione Ridge',format_value(result.predicted));b.metric('Valore osservato',format_value(result.observed))
 c.metric('Errore assoluto del caso',format_value(abs(result.predicted-result.observed)));d.metric('Riferimento del modello',format_value(result.base_value))
 local=tables['local'].loc[tables['local'].case_id.eq(result.case_id)].copy()
 ordered=local.assign(magnitude=local.contribution.abs()).sort_values('magnitude',ascending=False)
 labels=ordered.variable.map(NAMES).fillna(ordered.variable)
 values=ordered.contribution.tolist();names=labels.tolist()
 if result.clipping_adjustment>0:
  values.append(float(result.clipping_adjustment));names.append('Vincolo finale: conteggio non negativo')
 chart=go.Figure(go.Waterfall(x=['Riferimento',*names,'Previsione'],y=[float(result.base_value),*values,0],
  measure=['absolute',*['relative']*len(values),'total'],text=[format_value(result.base_value),*[format_value(v) for v in values],format_value(result.predicted)],
  textposition='outside',increasing={'marker':{'color':'#176e5a'}},decreasing={'marker':{'color':'#a34135'}},totals={'marker':{'color':'#184b78'}}))
 chart.update_layout(yaxis_title=unit,xaxis_tickangle=-30,height=490,showlegend=False,margin={'b':130,'t':30})
 st.plotly_chart(chart,width='stretch')
 st.caption('I contributi positivi aumentano la previsione rispetto al riferimento; quelli negativi la riducono. Mostrano come il modello usa le informazioni, non effetti causali sulla salute.')
 if result.clipping_adjustment>0:
  st.caption('La previsione lineare era negativa ed è stata riportata a zero come previsto dal protocollo. Questo aggiustamento è mostrato separatamente e non è un contributo SHAP di una variabile.')
 st.dataframe(pd.DataFrame({'Variabile':labels,'Valore usato':ordered.value,'Contributo SHAP':ordered.contribution}),hide_index=True,width='stretch')
 st.subheader('Importanza delle variabili nel blocco di test')
 importance=tables['global'].loc[tables['global'].fit_id.eq(result.fit_id)].sort_values('mean_abs_contribution')
 fig=go.Figure(go.Bar(x=importance.mean_abs_contribution,y=importance.variable.map(NAMES).fillna(importance.variable),orientation='h',marker_color='#184b78'))
 fig.update_layout(xaxis_title='Contributo medio assoluto ('+unit+')',height=400,margin={'l':10,'t':10})
 st.plotly_chart(fig,width='stretch')
 block=pool.loc[pool.block.astype(str).eq(str(result.block))]
 selected_block=block.loc[block.configuration.eq(config)]
 st.caption(f'Riepilogo di {len(selected_block)} previsioni su {selected_block.territory.nunique()} territori nel '+('test annuale.' if scale=='annual' else 'semestre di test. Non riguarda soltanto il mese e il comune selezionati.'))
 st.subheader('Errore delle configurazioni sullo stesso test')
 metrics=block.assign(error=(block.predicted-block.observed).abs()).groupby('configuration').agg(MAE=('error','mean'),Previsioni=('case_id','size')).reset_index()
 metrics['Configurazione']=metrics.configuration.map(configurations)
 st.dataframe(metrics[['Configurazione','MAE','Previsioni']],hide_index=True,width='stretch')
 st.caption('Il MAE riguarda tutte le osservazioni del blocco di test. Un valore inferiore indica un errore medio minore; le versioni sono confrontate sugli stessi casi.')
 with st.expander('Metodo e coefficienti'):
  st.write('Le spiegazioni usano la decomposizione lineare SHAP con riferimento ai soli dati di addestramento, dopo imputazione e standardizzazione. '
           'Il metodo assume indipendenza per attribuire i contributi: con variabili correlate la ripartizione può dipendere da questa scelta. '
           'Le colonne che codificano il comune sono riunite in un unico contributo territoriale. '
           'Le previsioni sono state confrontate con quelle archiviate prima di pubblicare le spiegazioni.')
  coefficients=tables['coefficients'].loc[tables['coefficients'].fit_id.eq(result.fit_id)]
  st.caption('I coefficienti descrivono il modello stimato, non relazioni causali. Quelli standardizzati si riferiscono agli ingressi trasformati del singolo modello.')
  st.dataframe(coefficients[['term','coefficient_transformed','coefficient_original_unit']],hide_index=True,width='stretch')
 st.download_button('Scarica i contributi del caso',local.to_csv(index=False),file_name='ridge_contributi.csv',mime='text/csv',key='ridge_download')
