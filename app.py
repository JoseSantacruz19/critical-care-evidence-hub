import streamlit as st
from Bio import Entrez
import pandas as pd

# Configuración del entorno de vigilancia bibliográfica de alta precisión
Entrez.email = "ja.santacruz.arias@gmail.com"
Entrez.api_key = st.secrets["NCBI_API_KEY"]

st.set_page_config(page_title="Vigilancia ICU Elite", layout="wide")
st.title("📚 Observatorio de Evidencia de Alta Jerarquía")
st.subheader("Filtro Epidemiológico: ECA, Metanálisis y NMA en Revistas Top Q1")

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
        
        # Procesamiento de autores con formato académico
        autores_raw = detalles.get('AuthorList', [])
        autores = ", ".join([f"{a.get('LastName', '')} {a.get('Initials', '')}" for a in autores_raw])
        
        # Extracción de tipo de publicación para validación de diseño
        tipos_pub = detalles.get('PublicationTypeList', [])
        diseno = ", ".join([str(tp) for tp in tipos_pub])
        
        # Resolución del DOI y enlace persistente
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
            "Diseño de Estudio": diseno,
            "DOI": doi,
            "Enlace PubMed": link
        })
    return lista_articulos

def ejecutar_consulta():
    # Estrategia de búsqueda: Lista blanca de las mejores revistas (Top 20 + Regionales)
    revistas = [
        "American journal of respiratory and critical care medicine", "Intensive care medicine",
        "Journal of the American Society of Nephrology", "Critical care",
        "Clinical journal of the American Society of Nephrology", "Clinical nutrition",
        "Critical care medicine", "Chest", "Burns & trauma", "Advances in wound care",
        "Annals of intensive care", "Chinese medical journal pulmonary and critical care medicine",
        "European heart journal. Acute cardiovascular care", "The journal of trauma and acute care surgery",
        "Journal of intensive care", "Neurocritical care", "Critical care clinics",
        "Pediatric critical care medicine", "Journal of critical care", "Current opinion in critical care",
        "Acta Colombiana de Cuidado Intensivo", "Medicina intensiva"
    ]
    
    filtro_revistas = " OR ".join([f"\"{j}\"[Journal]" for j in revistas])
    
    # Filtro avanzado MeSH y texto libre para máxima sensibilidad en diseños de alta jerarquía
    mesh_clinico = "(Sepsis[MeSH] OR Shock, Septic[MeSH] OR Respiration, Artificial[MeSH] OR Critical Care[MeSH] OR Renal Replacement Therapy[MeSH] OR Hemodynamics[MeSH] OR Intensive Care Units[MeSH])"
    disenos_evidencia = "(Randomized Controlled Trial[PT] OR Controlled Clinical Trial[PT] OR Meta-Analysis[PT] OR Systematic Review[PT] OR \"Network Meta-Analysis\"[TIAB] OR \"NMA\"[TIAB])"
    
    # Ventana temporal de 30 días para compensar latencia de indexación
    tiempo = "\"last 30 days\"[Filter]"
    
    consulta_final = f"({filtro_revistas}) AND {mesh_clinico} AND {disenos_evidencia} AND {tiempo}"
    
    with st.spinner('Ejecutando escrutinio metodológico en PubMed...'):
        handle = Entrez.esearch(db="pubmed", term=consulta_final, retmax=50)
        resultado = Entrez.read(handle)
        id_list = resultado["IdList"]
        
        if id_list:
            articulos = extraer_metadatos(id_list)
            df = pd.DataFrame(articulos)
            st.success(f"Se han identificado {len(id_list)} estudios de alta jerarquía metodológica.")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No se identificaron estudios con los criterios de alta jerarquía en el periodo de 30 días.")

if st.sidebar.button('Sincronizar Evidencia Top'):
    ejecutar_consulta()
