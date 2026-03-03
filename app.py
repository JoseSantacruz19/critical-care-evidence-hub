import streamlit as st
import requests
import pandas as pd
import datetime
from Bio import Entrez

# Configuración de credenciales y entorno
Entrez.email = "ja.santacruz.arias@gmail.com"
Entrez.api_key = st.secrets["NCBI_API_KEY"]

st.set_page_config(page_title="Vigilancia ICU Multi-Fuente", layout="wide")
st.title("📚 Observatorio de Evidencia Multi-Base (NCBI + Europe PMC)")

def fetch_pubmed(query, max_results=20):
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        id_list = Entrez.read(handle)["IdList"]
        if not id_list: return []
        handle = Entrez.efetch(db="pubmed", id=",".join(id_list), retmode="xml")
        records = Entrez.read(handle)
        results = []
        for art in records['PubmedArticle']:
            medline = art['MedlineCitation']['Article']
            doi = "N/A"
            for ident in art['PubmedData'].get('ArticleIdList', []):
                if ident.attributes.get('IdType') == 'doi': doi = str(ident)
            results.append({
                "Título": medline.get('ArticleTitle', 'N/A'),
                "Revista": medline['Journal'].get('Title', 'N/A'),
                "DOI": doi.lower(),
                "Fuente": "PubMed"
            })
        return results
    except Exception as e:
        return []

def fetch_europe_pmc(query, max_results=20):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": query, "format": "json", "resultType": "core", "pageSize": max_results}
    try:
        r = requests.get(url, params=params)
        data = r.json().get('resultList', {}).get('result', [])
        return [{
            "Título": a.get('title', 'N/A'),
            "Revista": a.get('journalTitle', 'N/A'),
            "DOI": a.get('doi', 'N/A').lower(),
            "Fuente": "Europe PMC"
        } for a in data]
    except:
        return []

def ejecutar_vigilancia():
    revistas = ["Intensive care medicine", "Critical care", "Acta Colombiana de Cuidado Intensivo", "Medicina intensiva"]
    # Simplificación de la query para demostración de vínculo
    q_pubmed = f'({" OR ".join([f"{j}[Journal]" for j in revistas])}) AND ("last 30 days"[Filter])'
    q_epmc = f'({" OR ".join([f"JOURNAL:\\"{j}\\"" for j in revistas])}) AND FIRST_PDATE:[2026-02-01 TO 2026-03-03]'
    
    with st.spinner('Sincronizando bases de datos...'):
        res_pubmed = fetch_pubmed(q_pubmed)
        res_epmc = fetch_europe_pmc(q_epmc)
        
        # Unificación y desduplicación por DOI
        df_total = pd.concat([pd.DataFrame(res_pubmed), pd.DataFrame(res_epmc)], ignore_index=True)
        if not df_total.empty:
            # La desduplicación técnica es vital para evitar el sesgo de redundancia (Rathbone, 2015)
            df_final = df_total.drop_duplicates(subset='DOI', keep='first')
            st.success(f"Sincronización completa: {len(df_final)} estudios únicos identificados.")
            st.dataframe(df_final, use_container_width=True)
        else:
            st.info("No se hallaron registros en el intervalo temporal.")

if st.sidebar.button('Sincronizar Evidencia Global'):
    ejecutar_vigilancia()
