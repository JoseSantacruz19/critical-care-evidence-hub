import streamlit as st
from Bio import Entrez
import pandas as pd

# Configuración del entorno de vigilancia bibliográfica
Entrez.email = "ja.santacruz.arias@gmail.com"
Entrez.api_key = st.secrets["NCBI_API_KEY"]

st.set_page_config(page_title="Vigilancia ICU", layout="wide")
st.title("📚 Observatorio de Evidencia en Medicina Crítica")
st.subheader("Actualización diaria automatizada de literatura científica")

def extraer_metadatos(id_list):
    if not id_list:
        return []
    ids = ",".join(id_list)
    handle = Entrez.efetch(db="pubmed", id=ids, retmode="xml")
    records = Entrez.read(handle)
    
    lista_articulos = []
    for article in records['PubmedArticle']:
        detalles = article['MedlineCitation']['Article']
        titulo = detalles.get('ArticleTitle', 'N/A')
        revista = detalles['Journal'].get('Title', 'N/A')
        
        # Procesamiento de autores
        autores_raw = detalles.get('AuthorList', [])
        autores = ", ".join([f"{a.get('LastName', '')} {a.get('Initials', '')}" for a in autores_raw])
        
        # Resolución del DOI
        ids_pubmed = article['PubmedData'].get('ArticleIdList', [])
        doi = "No disponible"
        for item in ids_pubmed:
            if item.attributes.get('IdType') == 'doi':
                doi = str(item)
        
        pmid = article['MedlineCitation']['PMID']
        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        
        lista_articulos.append({
            "Título": titulo,
            "Autores": autores,
            "Revista": revista,
            "DOI": doi,
            "Enlace PubMed": link
        })
    return lista_articulos

def ejecutar_consulta():
    # Consulta optimizada por términos MeSH y ventana temporal de 24 horas
    busqueda = "(Critical Care[MeSH] OR Intensive Care[MeSH] OR Sepsis[MeSH]) AND (\"last 1 days\"[Filter])"
    with st.spinner('Consultando servidores de NCBI...'):
        handle = Entrez.esearch(db="pubmed", term=busqueda, retmax=10)
        resultado = Entrez.read(handle)
        id_list = resultado["IdList"]
        
        if id_list:
            articulos = extraer_metadatos(id_list)
            df = pd.DataFrame(articulos)
            st.write(f"Se han identificado {len(id_list)} artículos nuevos en las últimas 24 horas:")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No se identificaron nuevos registros en el intervalo de búsqueda seleccionado.")

if st.sidebar.button('Sincronizar Literatura'):
    ejecutar_consulta()
