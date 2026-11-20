"""Show recorded acquisition dates, independently from measurement dates."""
from pathlib import Path
import json

def render_daily_update_status():
    import streamlit as st
    path=Path(__file__).resolve().parents[2]/'data/processed/one_health/operational/daily_update_status.json'
    if not path.is_file():
        st.caption('La data delle misure è distinta dalla data di acquisizione. Il prossimo aggiornamento tramite pipeline registrerà anche il suo esito.');return
    try:data=json.loads(path.read_text())
    except (OSError,ValueError):return
    states={'OK':'completato','RUNNING':'in esecuzione','FAILED':'non completato'}
    st.caption('Ultimo tentativo di aggiornamento (UTC): '+str(data.get('last_attempt_utc','non registrato'))+
               ' · Esito: '+states.get(data.get('status'),'non registrato')+
               ' · Ultimo completamento (UTC): '+str(data.get('last_success_utc','non registrato')))
    if data.get('status')=='FAILED':
        st.info('L’ultimo aggiornamento non è terminato nella fase '+str(data.get('stage'))+'. Le misure già caricate restano consultabili.')
