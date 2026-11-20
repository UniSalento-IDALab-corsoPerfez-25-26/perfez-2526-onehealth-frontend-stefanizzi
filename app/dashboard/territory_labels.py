"""Human-readable territory labels, preserving source geographic identifiers."""
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
PROVINCES={'071':'Foggia','072':'Bari','073':'Taranto','074':'Brindisi','075':'Lecce','076':'BAT'}

def municipality_code(values):
    return values.astype('string').str.strip().str.replace(r'\.0$','',regex=True).str.zfill(6)


def readable_territories(frame, territory):
    data=frame.copy()
    mapping_path=ROOT/'config/one_health/comuni_puglia.csv'
    mapping=pd.read_csv(mapping_path,dtype={'codice_comune':'string'}) if mapping_path.is_file() else pd.DataFrame(columns=['codice_comune','comune','provincia'])
    mapping=mapping.drop_duplicates('codice_comune').set_index('codice_comune')
    station_path=ROOT/'config/one_health/stazioni_dashboard.csv'
    if 'source_station_id' in data and not any(c in data for c in ('province','provincia')) and station_path.is_file():
        stations=pd.read_csv(station_path,dtype={'source_station_id':'string'})
        keys=['source_station_id']+(['network'] if 'network' in data else [])
        stations=stations[keys+['province']].drop_duplicates()
        # Ignore ambiguous identifiers rather than assigning an arbitrary province.
        stations=stations.loc[~stations.duplicated(keys,keep=False)]
        ids=data['source_station_id'].astype('string').str.replace(r'\.0$','',regex=True)
        if len(keys)==1:
            data['province']=ids.map(stations.set_index(keys[0]).province)
        else:
            index=pd.MultiIndex.from_arrays([ids,data['network'].astype('string')])
            data['province']=stations.set_index(keys).province.reindex(index).to_numpy()
    codecol=next((c for c in ('codice_comune','municipality_code') if c in data),None)
    if codecol:
        codes=municipality_code(data[codecol])
        namecol=next((c for c in ('comune','municipality','municipality_name') if c in data),None)
        names=data[namecol].astype('string').str.strip().replace('',pd.NA) if namecol else pd.Series(pd.NA,index=data.index,dtype='string')
        data['Comune']=names.fillna(codes.map(mapping['comune'])).fillna('Comune non identificato ('+codes+')')
        provcol=next((c for c in ('provincia','province') if c in data),None)
        prov=data[provcol].astype('string').str.strip().replace('',pd.NA) if provcol else pd.Series(pd.NA,index=data.index,dtype='string')
        data['Provincia']=prov.fillna(codes.map(mapping['provincia'])).fillna(codes.str[:3].map(PROVINCES))
        if territory==codecol:territory='Comune'
    elif 'province' in data or 'provincia' in data:
        col='province' if 'province' in data else 'provincia'
        data['Provincia']=data[col].astype('string')
    # Municipal ASL metadata can be used when province names are absent.
    elif territory not in ('asl',None) and 'asl' in data:
        data['Provincia']=data['asl'].astype('string')
    return data,territory


def representative_selection(frame, column, options, limit=6):
    """One starting category per province before filling remaining slots."""
    if 'Provincia' not in frame or column=='Provincia':return options[:limit]
    pairs=frame[[column,'Provincia']].dropna().drop_duplicates().copy()
    pairs[column]=pairs[column].astype(str)
    selected=[]
    for _,group in pairs.groupby('Provincia',sort=True):
        available=sorted(set(group[column]).intersection(options))
        if available and available[0] not in selected:selected.append(available[0])
    return (selected+[x for x in options if x not in selected])[:limit]
