import os
import tempfile
import zipfile
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import warnings
import io
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import array_bounds
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import folium
from folium import Map
from folium.raster_layers import ImageOverlay
import streamlit as st
from streamlit_folium import st_folium
import geopandas as gpd
import matplotlib.cm as mpl_cm
from matplotlib import colormaps
import streamlit as st
import hashlib
import json
from datetime import datetime
import os

# ========================
# Configuration d'authentification
# ========================

# IMPORTANT: Ne JAMAIS exposer les credentials en production
# Utiliser des variables d'environnement ou un gestionnaire de secrets
USERS_DB = {
    "supervisor": {
        "password_hash": hashlib.sha256(os.getenv("SUPERVISOR_PWD", "supervisor123").encode()).hexdigest(),
        "role": "Superviseur GIRE",
        "email": "supervisor@sanaga.cm"
    },
    "engineer": {
        "password_hash": hashlib.sha256(os.getenv("ENGINEER_PWD", "engineer123").encode()).hexdigest(),
        "role": "Ingénieur Barrage (NHPC/EDC)",
        "email": "engineer@sanaga.cm"
    },
    "chemist": {
        "password_hash": hashlib.sha256(os.getenv("CHEMIST_PWD", "chemist123").encode()).hexdigest(),
        "role": "Hydrochimiste / Labo",
        "email": "chemist@sanaga.cm"
    },
    "field_agent": {
        "password_hash": hashlib.sha256(os.getenv("FIELD_AGENT_PWD", "agent123").encode()).hexdigest(),
        "role": "Agent de Terrain",
        "email": "field@sanaga.cm"
    },
    "minister": {
        "password_hash": hashlib.sha256(os.getenv("MINISTER_PWD", "minister123").encode()).hexdigest(),
        "role": "Décideur / Ministère",
        "email": "minister@sanaga.cm"
    }
}


def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def check_credentials(username: str, password: str) -> bool:
    """Vérifie les identifiants de l'utilisateur"""
    if username not in USERS_DB:
        return False
    
    password_hash = hash_password(password)
    stored_hash = USERS_DB[username]["password_hash"]
    
    return password_hash == stored_hash


def get_user_role(username: str) -> str:
    """Récupère le rôle de l'utilisateur"""
    if username in USERS_DB:
        return USERS_DB[username]["role"]
    return None


def login_user(username: str, password: str) -> bool:
    """Authentifie l'utilisateur et stocke les infos en session"""
    if check_credentials(username, password):
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.role = get_user_role(username)
        st.session_state.email = USERS_DB[username]["email"]
        st.session_state.login_time = datetime.now()
        return True
    return False


def logout_user():
    """Déconnecte l'utilisateur"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.email = None
    st.session_state.login_time = None


def init_session_state():
    """Initialise l'état de session"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "email" not in st.session_state:
        st.session_state.email = None
    if "login_time" not in st.session_state:
        st.session_state.login_time = None


def login_page():
    """Page de connexion stylisée - Code masqué en production"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <style>
            .login-container {
                background: linear-gradient(135deg, #0A1929 0%, #10233A 100%);
                border-radius: 12px;
                padding: 40px;
                border: 1px solid #23425F;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            .login-title {
                font-family: 'Space Grotesk', sans-serif;
                font-size: 32px;
                font-weight: 700;
                color: #E7EEF6;
                text-align: center;
                margin-bottom: 10px;
            }
            .login-subtitle {
                font-family: 'IBM Plex Mono', monospace;
                font-size: 13px;
                color: #8FA6BE;
                text-align: center;
                margin-bottom: 30px;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }
            .input-field {
                margin-bottom: 15px;
            }
            </style>
            <div class="login-container">
                <div class="login-title">🌊 JUMEAU SANAGA</div>
                <div class="login-subtitle">Système d'authentification sécurisé</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col_form_1, col_form_2 = st.columns([1, 1])
        
        with col_form_1:
            username = st.text_input(
                "Nom d'utilisateur",
                key="username_input",
                placeholder="Entrez votre identifiant"
            )
        
        with col_form_2:
            password = st.text_input(
                "Mot de passe",
                type="password",
                key="password_input",
                placeholder="Entrez votre mot de passe"
            )
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn1:
            if st.button("🔓 Se connecter", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("⚠️ Veuillez remplir tous les champs")
                elif login_user(username, password):
                    st.success("✅ Connexion réussie ! Bienvenue")
                    st.rerun()
                else:
                    st.error("❌ Identifiants incorrects. Veuillez réessayer.")
        
        with col_btn3:
            st.info("💡 Contactez l'administrateur pour vos identifiants")
        
        st.markdown("---")
        st.warning("⚠️ Accès sécurisé - Toute tentative d'accès non autorisé est enregistrée et peut être poursuivie en justice")


def user_profile_sidebar():
    """Affiche le profil utilisateur dans la sidebar avec option de déconnexion"""
    if st.session_state.authenticated:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 Profil Utilisateur")
        
        col_profile_1, col_profile_2 = st.sidebar.columns([2, 1])
        with col_profile_1:
            st.sidebar.markdown(f"**{st.session_state.username}**")
            st.sidebar.caption(f"🎭 {st.session_state.role}")
        
        st.sidebar.markdown("---")
        
        if st.sidebar.button("🔓 Déconnexion", use_container_width=True, type="secondary"):
            logout_user()
            st.rerun()


if not hasattr(mpl_cm, "get_cmap"):
    def _get_cmap(name, lut=None):
        cmap = colormaps.get_cmap(name)
        if lut is not None:
            return cmap.resampled(lut)
        return cmap

    mpl_cm.get_cmap = _get_cmap

# Masquer le bouton "Source code" et autres éléments de Streamlit
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Configuration de la page - Masquer le menu "About"
st.set_page_config(
    page_title="Jumeau Numérique - BV Sanaga",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": None
    }
)

# Thème couleurs / constantes
PLOTLY_TEMPLATE = "plotly_dark"
COLOR_RIVER   = "#1E88B5"
COLOR_CYAN    = "#3FC1D0"
COLOR_GREEN   = "#16A34A"
COLOR_AMBER   = "#F5A524"
COLOR_LATERITE = "#C1440E"
PLOTLY_PAPER_BG = "#10233A"
PLOTLY_PLOT_BG  = "#10233A"


def style_fig(fig, height=300):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        paper_bgcolor=PLOTLY_PAPER_BG,
        plot_bgcolor=PLOTLY_PLOT_BG,
        font=dict(family="Inter, sans-serif", color="#E7EEF6"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


# CSS & Style
def inject_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        :root {
            --bg-deep: #0A1929;
            --bg-panel: #10233A;
            --bg-panel-raised: #132F4C;
            --line: #23425F;
            --text-main: #E7EEF6;
            --text-dim: #8FA6BE;
            --river-blue: #1E88B5;
            --river-cyan: #3FC1D0;
            --hydro-green: #16A34A;
            --amber: #F5A524;
            --laterite: #C1440E;
        }
        html, body, [class*="css"]  {
            font-family: 'Inter', sans-serif;
            color: var(--text-main);
        }
        .river-flow { height: 4px; width: 100%; margin: 4px 0 22px 0; border-radius: 2px; background: linear-gradient(90deg, var(--laterite) 0%, var(--river-blue) 35%, var(--river-cyan) 60%, var(--hydro-green) 100%); background-size: 200% 200%; animation: flow 8s ease-in-out infinite; }
        @keyframes flow { 0% { background-position: 0% 0%; } 100% { background-position: 200% 0%; } }
        .main-title { font-family: 'Space Grotesk', sans-serif; font-size: 27px !important; font-weight: 700; color: var(--text-main); margin-bottom: 2px; }
        .main-subtitle { font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: var(--text-dim); letter-spacing: 0.5px; text-transform: uppercase; }
        .status-box { padding: 12px 14px; border-radius: 8px; text-align: center; font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 13px; border: 1px solid var(--line); }
        .status-sync { background: rgba(22, 163, 74, 0.12); color: #4ADE80; border-color: rgba(22, 163, 74, 0.35); }
        .status-alert { background: rgba(193, 68, 14, 0.14); color: #FF8B5E; border-color: rgba(193, 68, 14, 0.4); }
        [data-testid="stAppViewContainer"] { background: radial-gradient(circle at 15% 0%, #0E2338 0%, var(--bg-deep) 55%); }
        [data-testid="stSidebar"] { background: var(--bg-panel); border-right: 1px solid var(--line); }
        h3, .stMarkdown h3 { font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 18px; border-left: 3px solid var(--river-blue); padding-left: 10px; margin-top: 6px; }
        .stButton > button { font-family: 'Space Grotesk', sans-serif; font-weight: 600; border-radius: 7px; border: 1px solid var(--river-blue); }
        </style>
    """, unsafe_allow_html=True)


# Modules
def header(role):
    col_title, col_status, col_alert = st.columns([2, 1, 1])
    with col_title:
        st.markdown('<p class="main-title">HYPERVISEUR UNIFIÉ DU BASSIN VERSANT DE LA SANAGA</p>', unsafe_allow_html=True)
        st.markdown('<p class="main-subtitle">Jumeau numérique · surveillance continue · Cameroun</p>', unsafe_allow_html=True)
    with col_status:
        st.markdown('<div class="status-box status-sync">🛰️ STATUS : SYNCHRONISÉ (TEMPS RÉEL)</div>', unsafe_allow_html=True)
    with col_alert:
        st.markdown('<div class="status-box status-alert">🔔 2 ALERTES (MBAM / ÉDÉA)</div>', unsafe_allow_html=True)
    st.markdown('<div class="river-flow"></div>', unsafe_allow_html=True)


def module_hydrochemistry():
    st.subheader("🧪 Module d'Analyse Hydrochimique Quantitative")
    st.info("Téléversez vos données de laboratoire (formats .csv ou .xlsx). Le système calculera automatiquement le SAR, le MAR et l'IQE pour évaluer la qualité des eaux.")

    with st.expander("💡 Voir la structure de fichier requise (Exemple)"):
        exemple_data = {
            "Station": ["Nachtigal Amont", "Édéa Pont", "Lom Pangar"],
            "Calcium_meq": [2.1, 1.8, 2.5],
            "Magnesium_meq": [1.2, 1.5, 1.1],
            "Sodium_meq": [0.8, 1.4, 0.6],
            "pH": [7.2, 6.8, 7.4],
            "Conductivite_uS": [150, 210, 125]
        }
        st.dataframe(pd.DataFrame(exemple_data))

    uploaded_file = st.file_uploader("Glissez-déposez le fichier de résultats du laboratoire ici", type=["csv", "xlsx"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            st.success("✅ Fichier chargé avec succès !")
        except Exception:
            st.error("❌ Erreur lors de la lecture du fichier. Veuillez vérifier le format.")
            df = None
    else:
        st.warning("⚠️ Aucun fichier fourni. Affichage des données de simulation de la Sanaga.")
        df = pd.DataFrame({
            "Station": ["Mbam à Goura", "Sanaga à Nachtigal", "Sanaga à Édéa", "Djerem à Mbakaou"],
            "Calcium_meq": [1.5, 2.2, 2.0, 1.1],
            "Magnesium_meq": [0.9, 1.4, 1.8, 0.7],
            "Sodium_meq": [1.1, 0.7, 2.1, 0.5],
            "pH": [7.1, 7.3, 6.5, 6.9],
            "Conductivite_uS": [140, 160, 240, 95]
        })

    if df is not None:
        df = df.copy()
        for col in ['Calcium_meq', 'Magnesium_meq', 'Sodium_meq', 'pH', 'Conductivite_uS']:
            if col not in df.columns:
                df[col] = np.nan

        df['SAR'] = (df['Sodium_meq'] / np.sqrt((df['Calcium_meq'] + df['Magnesium_meq']) / 2)).round(2)
        df['MAR (%)'] = ((df['Magnesium_meq'] * 100) / (df['Calcium_meq'] + df['Magnesium_meq'])).round(1)

        penalite_ph = np.abs(df['pH'] - 7.0) * 15
        penalite_ec = (df['Conductivite_uS'] / 500) * 20
        df['IQE'] = (100 - (penalite_ph + penalite_ec)).clip(lower=0, upper=100).round(1)

        df['Aptitude Irrigation (SAR)'] = np.where(df['SAR'] < 10, "Excellent (S1)", 
                                                   np.where(df['SAR'] < 18, "Bon (S2)", "Médiocre (S3/S4)"))

        st.markdown("### 📊 Résultats des Évaluations Automatisées")
        st.dataframe(df, use_container_width=True)

        st.markdown("### 📉 Comparaison des indices du bassin")
        c_graph1, c_graph2 = st.columns(2)
        with c_graph1:
            fig_sar = go.Figure([go.Bar(x=df['Station'], y=df['SAR'], marker_color=COLOR_RIVER, text=df['SAR'], textposition='auto')])
            fig_sar.update_layout(title="Indice SAR par Station (Risque d'Alcalinisation)")
            style_fig(fig_sar, 300)
            st.plotly_chart(fig_sar, use_container_width=True)
        with c_graph2:
            fig_iqe = go.Figure([go.Bar(x=df['Station'], y=df['IQE'], marker_color=COLOR_GREEN, text=df['IQE'], textposition='auto')])
            fig_iqe.update_layout(title="Indice Général de Qualité de l'Eau (IQE / 100)")
            style_fig(fig_iqe, 300)
            st.plotly_chart(fig_iqe, use_container_width=True)


def module_map():
    st.set_page_config(layout="wide")
    col_graph, col_prod = st.columns([2, 1])

    with col_graph:
        st.subheader("Visualisation Cartographique du Réseau")

        locations = {
            "Lom Pangar (Barrage)": [5.383, 13.500],
            "Nachtigal (Barrage)": [4.350, 11.633],
            "Station Goura (Mbam)": [4.712, 11.250],
            "Zone Aval Édéa": [3.800, 10.133],
            "kikot":[4.1697057,11.0186578],
        }
        # 1. Définition des limites géographiques strictes (Sud-Ouest et Nord-Est du bassin)
        limites_de_limitation = [[3.0, 9.5], [7.5, 14.5]]

        # 2. Création de la carte avec blocage des mouvements en dehors du bassin
        m = folium.Map(
            location=[4.8, 11.8], 
            zoom_start=7, 
            min_zoom=6,
            max_zoom=10,
            tiles="CartoDB positron",
            max_bounds=True,
            bounds=limites_de_limitation
        )
        # 3. Ajout de la couche ESA WorldCover (Résolution 10m - Couvert végétal global)
        # Ce service WMS affiche instantanément les forêts, savanes et cultures du bassin
        url_wms_esa = "https://terrascope.be"

        folium.WmsTileLayer(
            url=url_wms_esa,
            layers="WORLDCOVER_2021_MAP",
            format="image/png",
            transparent=True,
            name="Couvert Végétal (ESA 10m)",
            attribution="© ESA WorldCover / Terrascope",
            overlay=True,
            control=True,
            show=True # Activé par défaut à l'écran
        ).add_to(m)
        # 3. Forcer la carte à se caler immédiatement sur ces limites
        m.fit_bounds(limites_de_limitation)
        # 5. AJOUT INDISPENSABLE : Le contrôle des couches (LayerControl)
        # Permet à l'utilisateur de cocher/décocher le couvert végétal en haut à droite
        folium.LayerControl(position="topright").add_to(m)
        #m = Map(location=[4.6, 11.8], zoom_start=7, tiles="CartoDB dark_matter")

        # COUCHE RASTER : MNT
        chemin_tif = "data/MNT_SANAGA_EPSG4326.tif"
        if os.path.exists(chemin_tif):
            try:
                with rasterio.open(chemin_tif) as src:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", message="Setting the shape on a NumPy array has been deprecated")
                        data = np.array(src.read(1), dtype="float32", copy=True)

                    nodata = src.nodata
                    if nodata is not None:
                        data[data == nodata] = np.nan

                    dst_crs = "EPSG:4326"
                    if src.crs and src.crs.to_string() != dst_crs:
                        transform, width, height = calculate_default_transform(
                            src.crs, dst_crs, src.width, src.height, *src.bounds
                        )
                        dst = np.empty((height, width), dtype=np.float32)
                        reproject(
                            source=data,
                            destination=dst,
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=transform,
                            dst_crs=dst_crs,
                            resampling=Resampling.bilinear,
                        )
                        data = dst
                        minx, miny, maxx, maxy = array_bounds(height, width, transform)
                    else:
                        b = src.bounds
                        minx, miny, maxx, maxy = (b.left, b.bottom, b.right, b.top)
                    
                    bounds = [[miny, minx], [maxy, maxx]]

                    if not np.all(np.isnan(data)):
                        vmin, vmax = np.nanmin(data), np.nanmax(data)
                        norm = Normalize(vmin=vmin, vmax=vmax, clip=True)
                        cmap = cm.get_cmap("Blues")
                        mapped = cmap(norm(np.nan_to_num(data, nan=vmin)))
                        mapped[..., 3] = np.where(np.isnan(data), 0.0, mapped[..., 3])
                        img = (mapped * 255).astype("uint8")

                        ImageOverlay(
                            image=img,
                            bounds=bounds,
                            opacity=0.4,
                            name="MNT / Bassin Versant",
                            mercator_project=True,
                        ).add_to(m)
            except Exception:
                st.warning("⚠️ Impossible de charger les données géospatiales")
        else:
            st.warning("❌ Données géospatiales non disponibles")

        # COUCHE VECTORIELLE : HYDROGRAPHIE
        shp_hydro_path = "data/Hydrographie sanaga.shp"
        gdf_hydro = None

        if os.path.exists(shp_hydro_path):
            try:
                gdf_hydro = gpd.read_file(shp_hydro_path)
            except Exception:
                st.warning("⚠️ Erreur de chargement de l'hydrographie")
        else:
            st.info("ℹ️ Données hydrographiques non disponibles")

        if gdf_hydro is not None and not gdf_hydro.empty:
            if gdf_hydro.crs is None or gdf_hydro.crs.to_string() != "EPSG:4326":
                gdf_hydro = gdf_hydro.to_crs("EPSG:4326")
            folium.GeoJson(
                gdf_hydro,
                name="Réseau Hydrographique",
                style_function=lambda feat: {
                    "color": COLOR_RIVER,
                    "weight": 2.5,
                    "opacity": 0.8,
                },
            ).add_to(m)

        # COUCHE VECTORIELLE : EXUTOIRES
        shp_exut_path = "data/exutoires de la Sanaga.shp"
        gdf_exutoires = None

        if os.path.exists(shp_exut_path):
            try:
                gdf_exutoires = gpd.read_file(shp_exut_path)
            except Exception:
                st.warning("⚠️ Erreur de chargement des exutoires")
        else:
            st.info("ℹ️ Données des exutoires non disponibles")

        if gdf_exutoires is not None and not gdf_exutoires.empty:
            if gdf_exutoires.crs is None or gdf_exutoires.crs.to_string() != "EPSG:4326":
                gdf_exutoires = gdf_exutoires.to_crs("EPSG:4326")
            
            colonnes_possibles = [c for c in gdf_exutoires.columns if any(x in c.lower() for x in ["nom", "stat", "id", "lab"])]
            colonne_cible = colonnes_possibles[0] if colonnes_possibles else None

            if colonne_cible:
                infobulle = folium.GeoJsonTooltip(
                    fields=[colonne_cible],
                    aliases=["Station : "],
                    localize=True
                )
            else:
                infobulle = folium.GeoJsonTooltip(fields=[gdf_exutoires.columns[0]], aliases=["Index : "])

            folium.GeoJson(
                gdf_exutoires,
                name="Exutoires du Bassin",
                marker=folium.CircleMarker(
                    radius=5,
                    color="#e31a1c",
                    fill=True,
                    fill_color="#e31a1c",
                    fill_opacity=0.9,
                ),
                tooltip=infobulle
            ).add_to(m)

        folium.Marker(
            locations["Lom Pangar (Barrage)"],
            popup="Lom Pangar - Statut OK",
            icon=folium.Icon(color="blue", icon="tint"),
        ).add_to(m)
        folium.Marker(
            locations["Nachtigal (Barrage)"],
            popup="Nachtigal - Statut OK",
            icon=folium.Icon(color="green", icon="flash"),
        ).add_to(m)
        folium.Marker(
            locations["Station Goura (Mbam)"],
            popup="Station Goura - Vigilance",
            icon=folium.Icon(color="orange", icon="warning-sign"),
        ).add_to(m)
        folium.Marker(
            locations["Zone Aval Édéa"],
            popup="Édéa - ALERTE CRUE",
            icon=folium.Icon(color="red", icon="exclamation-sign"),
        ).add_to(m)
        folium.Marker(
            locations["kikot"],
            popup="Kikot - Complexe industriel",
            icon=folium.Icon(color="purple", icon="industry", prefix="fa"),
        ).add_to(m)
        folium.LayerControl().add_to(m)
        
        st_folium(m, width="100%", height=600)

    with col_prod:
        st.subheader("🎛️ Module de Simulation")
        actif = st.selectbox("Sélectionner un actif", ["Barrage de Nachtigal", "Barrage de Lom Pangar", "Barrage de Song Loulou"])
        scenario = st.selectbox("Scénario", ["Ouverture des vannes", "Étiage sévère (Saison sèche)", "Crue décennale"])
        
        debit_simule = st.slider("Volume d'eau injecté / régulé (m³/s)", min_value=500, max_value=3000, value=1200, step=100)
        
        st.markdown("### 🔀 Propagation estimée")
        temps_calcul = 14 - int(debit_simule/300)
        hauteur_calcul = round(0.1 + (debit_simule/4000), 2)
        
        st.metric(label="⏱️ Temps d'arrivée à l'aval", value=f"+{temps_calcul}h 15min")
        st.metric(label="📈 Variation Hauteur Critique", value=f"+{hauteur_calcul} m", delta=f"{hauteur_calcul}m", delta_color="inverse")
        
        if st.button("⚡ SIMULER L'IMPACT SUR LE RÉSEAU", type="primary"):
            st.success("Simulation injectée dans le moteur de calcul hydrologique !")

    st.markdown("---")
    
    with col_graph:
        st.subheader("📈 Débit du fleuve (m³/s) — Station Goura (Mbam)")
        
        heures = [f"{h:02d}:00" for h in range(0, 25, 4)]
        debit_reel = [700, 850, 1400, 1650, 1300, 950, 800]
        seuil_alerte = [1200] * len(heures)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=heures, y=debit_reel, name="Débit Actuel (IoT)", line=dict(color=COLOR_RIVER, width=3)))
        fig.add_trace(go.Scatter(x=heures, y=seuil_alerte, name="Seuil d'Alerte", line=dict(color=COLOR_LATERITE, dash="dash")))
        
        if debit_simule > 1200:
            debit_predit = [d * (debit_simule/1200) for d in debit_reel]
            fig.add_trace(go.Scatter(x=heures, y=debit_predit, name="Impact Prédit", line=dict(color=COLOR_GREEN, dash="dot")))

        style_fig(fig, 250)
        st.plotly_chart(fig, use_container_width=True)
        
    with col_prod:
        st.subheader("⚡ Production Hydro Globale")
        st.progress(0.85, text="Nachtigal : 420 MW / 420 MW")
        st.progress(0.70, text="Song Loulou : 270 MW / 384 MW")
        st.progress(0.90, text="Édéa : 243 MW / 270 MW")
        st.metric(label="Total injecté au RIS (Réseau Interconnecté Sud)", value="933 MW", delta="Production Stable 🟢")


def module_3d():
    st.subheader("📐 Jumeau de Scène Immersif (Simulation Géométrique 3D)")
    st.info("Zone réservée — intégration WebGL (Cesium/Three.js) possible dans la version finale.")
    niveau_eau = st.slider("Ajuster le niveau de la retenue de Lom Pangar (mètres)", 650, 675, 668)
    fig_3d = go.Figure()
    fig_3d.add_trace(go.Bar(x=["Mur du Barrage"], y=[675], name="Structure Béton", marker_color="#5B7186", width=0.3))
    fig_3d.add_trace(go.Bar(x=["Niveau d'Eau Actuel"], y=[niveau_eau], name="Volume d'Eau", marker_color=COLOR_RIVER, width=0.3))
    fig_3d.update_layout(yaxis=dict(range=[640, 680]), barmode='group')
    style_fig(fig_3d, 350)
    st.plotly_chart(fig_3d, use_container_width=True)


def module_analytics():
    st.subheader("📊 Tableau de Bord de Gestion Intégrée des Ressources en Eau (GIRE)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume Global du Bassin", "8.4 Milliards m³", "Normal")
    c2.metric("Stress Hydrique Sectoriel", "Faible (Saison des pluies)", "-12% de risques")
    c3.metric("Indice de Qualité de l'Eau", "84 / 100", "Stable")

    st.markdown("### Répartition des usages de l'eau de la Sanaga (Demande vs Allocation)")
    labels = ['Hydroélectricité', 'Eau Potable (Camwater)', 'Agriculture & Irrigation', 'Besoins Écologiques']
    values = [75, 12, 8, 5]
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker_colors=[COLOR_RIVER, COLOR_CYAN, COLOR_AMBER, COLOR_GREEN])])
    style_fig(fig_pie, 350)
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### 🍃 Évaluation de l'Empreinte Carbone du Complexe Hydroélectrique")
    puissance_kw = 933000
    co2_evite_par_heure = round((puissance_kw * 0.750) / 1000, 2)
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.metric(label="📉 Émissions de CO₂ évitées en direct", value=f"{co2_evite_par_heure} Tonnes / heure", delta="Par rapport au Fioul/Gaz")
    with col_c2:
        st.metric(label="💨 Émissions endogènes estimées (Méthane CH₄)", value="12.4 g CO2eq / kWh", delta="Statut : Stable", delta_color="inverse")


def module_sensors():
    st.subheader("🛠️ État de Santé du Réseau IoT (Vue Terrain & Mobile)")
    st.warning("Cette vue bascule en format vertical condensé lorsqu'elle est ouverte sur un smartphone par les techniciens.")
    data_capteurs = {
        "Nom de la Station": ["Station Mbakaou", "Sonde Nachtigal Amont", "Station Goura", "Sonde Édéa Pont"],
        "Type de Capteur": ["Ultrason Niveau", "Radar Débit", "Limnimètre Connecté", "Hydrophone"],
        "Batterie": ["92%", "81%", "14% ⚠️", "100%"],
        "Statut": ["Opérationnel", "Opérationnel", "Maintenance Requise", "Opérationnel"]
    }
    df = pd.DataFrame(data_capteurs)
    st.dataframe(df, use_container_width=True)

    st.markdown("### Rédiger un rapport d'anomalie terrain")
    with st.form("maintenance_form"):
        station_select = st.selectbox("Station concernée", df["Nom de la Station"])
        incident = st.text_area("Description du problème (ex: Capteur obstrué par des sédiments ou problème d'alimentation solaire)")
        submit = st.form_submit_button("Envoyer l'alerte à la salle de contrôle")
        if submit:
            st.success("Rapport envoyé avec succès à la salle de contrôle !")


def sidebar_nav():
    st.sidebar.markdown("## 🌊 JUMEAU SANAGA")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧭 Modules intégrés")
    
    menu = st.sidebar.radio(
        "Navigation principale",
        ["🗺️ Carte Temps Réel (SIG)", "📐 Scène 3D & Simulation", "📊 Analytics & GIRE", "🧪 Hydrochimie & Labo", "🛠️ Capteurs & Alertes Mobile"]
    )
    
    return menu


def main():
    init_session_state()
    inject_css()
    
    if not st.session_state.authenticated:
        login_page()
        return
    
    menu = sidebar_nav()
    user_profile_sidebar()
    
    header(st.session_state.role)

    if menu == "🗺️ Carte Temps Réel (SIG)":
        module_map()
    elif menu == "📐 Scène 3D & Simulation":
        module_3d()
    elif menu == "📊 Analytics & GIRE":
        module_analytics()
    elif menu == "🧪 Hydrochimie & Labo":
        module_hydrochemistry()
    else:
        module_sensors()


if __name__ == "__main__":
    main()
