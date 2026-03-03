import streamlit as st
import requests
import pandas as pd
import datetime
from Bio import Entrez

# Configuración del entorno y credenciales académicas
# Se recomienda encarecidamente el uso de st.secrets para la gestión de API Keys
Entrez.email = "ja.santacruz.arias@gmail.com"
Entrez.api_key = st.secrets["NCBI_API_KEY"]

st.set_page_config(page_title="Vigilancia ICU Multi-Fuente", layout="wide")
st.title("📚 Observatorio de Evidencia de Alta Jerarquía")
st.subheader("Integración de Vanguardia: NCBI + Europe PMC + Crossref")

def fetch_pubmed(query, max_results=30):
    """Recupera metadatos desde NCBI PubMed utilizando Biopython de forma segura."""
    try:
        # MEJORA 1: Usamos reldate=30 y datetype="edat" nativos de la API en lugar de texto
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, reldate=30, datetype="edat")
        id_list = Entrez.read(handle)["IdList"]
        
        if not id_list: return []
        
        handle = Entrez.efetch(db="pubmed", id=",".join(id_list), retmode="xml")
        records = Entrez.read(handle)
        results = []
        
        # MEJORA 2: Usamos .get() en todas partes para evitar que un metadato faltante rompa el código
        for art in records.get('PubmedArticle', []):
            medline = art.get('MedlineCitation', {}).get('Article', {})
            doi = "No disponible"
            
            for ident in art.get('PubmedData', {}).get('ArticleIdList', []):
                if ident.attributes.get('IdType') == 'doi': 
                    doi = str(ident).lower()
                    
            results.append({
                "Título": medline.get('ArticleTitle', 'N/A'),
                "Revista": medline.get('Journal', {}).get('Title', 'N/A'),
                "Diseño": ", ".join([str(tp) for tp in medline.get('PublicationTypeList', [])]),
                "DOI": doi,
                "Fuente": "PubMed"
            })
        return results
    except Exception as e:
        # MEJORA 3: Mostramos el error temporalmente en pantalla para saber qué pasa
        st.error(f"Error interno consultando PubMed: {e}")
        return []

def fetch_europe_pmc(query, max_results=30):
    """Recupera metadatos desde la API REST de Europe PMC."""
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": query, "format": "json", "resultType": "core", "pageSize": max_results}
    try:
        r = requests.get(url, params=params)
        data = r.json().get('resultList', {}).get('result', [])
        return [{
            "Título": a.get('title', 'N/A'),
            "Revista": a.get('journalTitle', 'N/A'),
            "Diseño": ", ".join(a.get('pubTypeList', {}).get('pubType', [])),
            "DOI": a.get('doi', 'N/A').lower(),
            "Fuente": "Europe PMC"
        } for a in data]
    except: return []

def get_crossref_citations(doi):
    """Obtiene el conteo de citaciones desde Crossref para enriquecer la evidencia."""
    if doi == "no disponible": return 0
    url = f"https://api.crossref.org/works/{doi}"
    try:
        r = requests.get(url, headers={"User-Agent": "EvidenceApp/1.0 (mailto:ja.santacruz.arias@gmail.com)"})
        if r.status_code == 200:
            return r.json()['message'].get('is-referenced-by-count', 0)
    except: pass
    return 0

def ejecutar_vigilancia():
    # Definición de revistas Q1 y regionales estratégicas
    revistas = [
        "American journal of respiratory and critical care medicine", "Intensive care medicine",
        "Journal of the American Society of Nephrology", "Critical care",
        "Clinical journal of the American Society of Nephrology", "Clinical nutrition",
        "Critical care medicine", "Chest", "Burns & trauma", "Advances in wound care",
        "Annals of intensive care", "Journal of trauma and acute care surgery",
        "Neurocritical care", "Acta Colombiana de Cuidado Intensivo", "Medicina intensiva", 
        "New England Journal of Medicine", "Nature Medicine", 
        "Lancet",  "Lancet Respiratory Medicine",
        "JAMA", "JAMA Cardiology", "Shock", 
        "trials", "Clinical Trials"
    ]
    
    # Construcción segura de subconsultas
    jr_pubmed = " OR ".join([f'"{j}"[Journal]' for j in revistas])
    jr_epmc = " OR ".join([f'JOURNAL:"{j}"' for j in revistas])
    
    # Definición de tópicos clínicos granulares
    topicos_text = ("(sepsis OR \"septic shock\" OR \"cardiogenic shock\" OR \"shock\" OR "
                    "\"Acute Respiratory Distress Syndrome\" OR \"Continuous Renal Replacement Therapy\" OR "
                    "\"Acute Kidney Injury\" OR \"Extracorporeal Membrane Oxygenation\" OR "
                    "\"mechanical ventilation\" OR \"ultrasound\" OR \"intensive care unit\" OR "
                    "\"hemoperfusion\" OR \"hemoadsorption\" OR \"vasopressors\" OR "
                    "\"hemodynamic monitoring\" OR \"status epilepticus\" OR "
                    "\"acute liver failure\" OR \"ventilator-associated pneumonia\" OR "
                    "\"delirium\" OR \"multiorgan failure\")")
                    
    # Filtros de jerarquía
    hier_pubmed = "(Randomized Controlled Trial[PT] OR Controlled Clinical Trial[PT] OR Meta-Analysis[PT])"
    hier_epmc = "(PUB_TYPE:\"Randomized Controlled Trial\" OR PUB_TYPE:\"Controlled Clinical Trial\" OR PUB_TYPE:\"clinical trial\" OR PUB_TYPE:\"Meta-Analysis\")"
    
    # --- NUEVO: Cálculo dinámico de fechas para los últimos 30 días ---
    hoy = datetime.date.today()
    hace_30_dias = hoy - datetime.timedelta(days=30)
    
    # Convertimos las fechas a texto en formato AAAA-MM-DD
    fecha_fin = hoy.strftime("%Y-%m-%d")
    fecha_inicio = hace_30_dias.strftime("%Y-%m-%d")
    # -------------------------------------------------------------------
    
    # Ensamblaje de consultas finales
    q_pubmed = f"({jr_pubmed}) AND {topicos_text} AND {hier_pubmed}"
    
    # Insertamos las fechas dinámicas en la consulta de Europe PMC
    q_epmc = f"({jr_epmc}) AND {topicos_text} AND {hier_epmc} AND FIRST_PDATE:[{fecha_inicio} TO {fecha_fin}]"
    
    with st.spinner('Sincronizando bases de datos globales y enriqueciendo metadatos...'):
        res_pubmed = fetch_pubmed(q_pubmed)
        res_epmc = fetch_europe_pmc(q_epmc)
        
        # Unificación y desduplicación técnica por DOI
        df_total = pd.concat([pd.DataFrame(res_pubmed), pd.DataFrame(res_epmc)], ignore_index=True)
        
        if not df_total.empty:
            df_final = df_total.drop_duplicates(subset='DOI', keep='first').copy()
            
            # Enriquecimiento con Crossref
            if st.sidebar.checkbox('Verificar impacto (Citas Crossref)'):
                df_final['Citas'] = df_final['DOI'].apply(get_crossref_citations)
            
            st.success(f"Vigilancia completada: {len(df_final)} estudios únicos de alta jerarquía identificados.")
            st.dataframe(df_final, use_container_width=True, 
                         column_config={"DOI": st.column_config.LinkColumn("Enlace DOI")})
        else:
            st.warning("No se identificaron nuevos estudios que cumplan los criterios en la ventana de 30 días.")
            
if st.sidebar.button('Sincronizar Evidencia Global'):
    ejecutar_vigilancia()
