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

if not hasattr(mpl_cm, "get_cmap"):
    def _get_cmap(name, lut=None):
        cmap = colormaps.get_cmap(name)
        if lut is not None:
            return cmap.resampled(lut)
        return cmap

    mpl_cm.get_cmap = _get_cmap
# ──────────────────────────────────────────────────────────────────────────
# CONFIGURATION DE LA PAGE
# ──────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Jumeau Numérique - BV Sanaga",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ──────────────────────────────────────────────────────────────────────────
# TOKENS DE DESIGN
#   Fond   : bleu-nuit profond (#0A1929 / #132F4C) — ambiance salle de contrôle
#   Accent : bleu-rivière (#1E88B5) pour les données, vert hydro (#16A34A) pour
#            les statuts OK, ambre (#F5A524) pour la vigilance, latérite
#            (#C1440E) réservée aux alertes — clin d'œil aux pistes de terre
#            rouge du bassin de la Sanaga.
#   Typo   : Space Grotesk (titres / chiffres), Inter (texte courant),
#            IBM Plex Mono (données brutes, horodatages, unités).
# ──────────────────────────────────────────────────────────────────────────
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

    /* ── Bandeau de flux — signature de la page ─────────────────────── */
    .river-flow {
        height: 4px;
        width: 100%;
        margin: 4px 0 22px 0;
        border-radius: 2px;
        background: linear-gradient(90deg, var(--laterite) 0%, var(--river-blue) 35%, var(--river-cyan) 60%, var(--hydro-green) 100%);
        background-size: 200% 100%;
        animation: flow 6s linear infinite;
    }
    @keyframes flow {
        0%   { background-position: 0% 0%; }
        100% { background-position: 200% 0%; }
    }
    @media (prefers-reduced-motion: reduce) {
        .river-flow { animation: none; }
    }

    /* ── Titre principal ─────────────────────────────────────────────── */
    .main-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 27px !important;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: var(--text-main);
        margin-bottom: 2px;
    }
    .main-subtitle {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12.5px;
        color: var(--text-dim);
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    /* ── Pastilles de statut (bandeau supérieur) ─────────────────────── */
    .status-box {
        padding: 12px 14px;
        border-radius: 8px;
        text-align: center;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 500;
        font-size: 13px;
        letter-spacing: 0.3px;
        border: 1px solid var(--line);
    }
    .status-sync {
        background: rgba(22, 163, 74, 0.12);
        color: #4ADE80;
        border-color: rgba(22, 163, 74, 0.35);
    }
    .status-alert {
        background: rgba(193, 68, 14, 0.14);
        color: #FF8B5E;
        border-color: rgba(193, 68, 14, 0.4);
    }

    /* ── Fond général de l'app ───────────────────────────────────────── */
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 15% 0%, #0E2338 0%, var(--bg-deep) 55%);
    }
    [data-testid="stHeader"] { background: transparent; }

    /* ── Barre latérale ───────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: var(--bg-panel);
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--text-main);
    }
    [data-testid="stSidebar"] hr { border-color: var(--line); }

    /* ── Cartes / conteneurs génériques (expander, forms) ────────────── */
    [data-testid="stExpander"], [data-testid="stForm"] {
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-radius: 10px;
    }

    /* ── Métriques ────────────────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-left: 3px solid var(--river-blue);
        border-radius: 8px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--text-main);
    }

    /* ── Tableaux ─────────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
    }

    /* ── Boutons ──────────────────────────────────────────────────────── */
    .stButton > button {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        border-radius: 7px;
        border: 1px solid var(--river-blue);
    }
    .stButton > button[kind="primary"] {
        background: var(--river-blue);
        border-color: var(--river-blue);
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--river-cyan);
        border-color: var(--river-cyan);
    }

    /* ── Barres de progression (production hydro) ────────────────────── */
    [data-testid="stProgress"] > div > div {
        background-color: var(--river-blue);
    }

    /* ── Titres de section ────────────────────────────────────────────── */
    h3, .stMarkdown h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 18px;
        border-left: 3px solid var(--river-blue);
        padding-left: 10px;
        margin-top: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# Palette Plotly cohérente avec le thème (utilisée par tous les graphiques)
PLOTLY_TEMPLATE = "plotly_dark"
COLOR_RIVER   = "#1E88B5"
COLOR_CYAN    = "#3FC1D0"
COLOR_GREEN   = "#16A34A"
COLOR_AMBER   = "#F5A524"
COLOR_LATERITE = "#C1440E"
PLOTLY_PAPER_BG = "#10233A"
PLOTLY_PLOT_BG  = "#10233A"

def style_fig(fig, height):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        paper_bgcolor=PLOTLY_PAPER_BG,
        plot_bgcolor=PLOTLY_PLOT_BG,
        font=dict(family="Inter, sans-serif", color="#E7EEF6"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig

# ──────────────────────────────────────────────────────────────────────────
# BARRE LATÉRALE : MENU DE NAVIGATION 5-EN-1 & PROFILS
# ──────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🌊 JUMEAU SANAGA")
role = st.sidebar.selectbox("👤 Profil Utilisateur", ["Superviseur GIRE", "Ingénieur Barrage (NHPC/EDC)", "Hydrochimiste / Labo", "Agent de Terrain", "Décideur / Ministère"])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧭 Modules intégrés")
menu = st.sidebar.radio(
    "Navigation principale",
    ["🗺️ Carte Temps Réel (SIG)", "📐 Scène 3D & Simulation", "📊 Analytics & GIRE", "🧪 Hydrochimie & Labo", "🛠️ Capteurs & Alertes Mobile"]
)

st.sidebar.markdown("---")
st.sidebar.info(f"Rôle actuel : **{role}**\n\nInterface optimisée pour le bassin de la Sanaga.")

# ──────────────────────────────────────────────────────────────────────────
# BANDEAU SUPÉRIEUR (TOP BAR)
# ──────────────────────────────────────────────────────────────────────────
col_title, col_status, col_alert = st.columns([2, 1, 1])
with col_title:
    st.markdown('<p class="main-title">HYPERVISEUR UNIFIÉ DU BASSIN VERSANT DE LA SANAGA</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Jumeau numérique · surveillance continue · Cameroun</p>', unsafe_allow_html=True)
with col_status:
    st.markdown('<div class="status-box status-sync">🛰️ STATUS : SYNCHRONISÉ (TEMPS RÉEL)</div>', unsafe_allow_html=True)
with col_alert:
    st.markdown('<div class="status-box status-alert">🔔 2 ALERTES (MBAM / ÉDÉA)</div>', unsafe_allow_html=True)

st.markdown('<div class="river-flow"></div>', unsafe_allow_html=True)
# ──────────────────────────────────────────────────────────────────────────
# MODULE 4 : HYDROCHIMIE & LABO (NOUVEAU)
# ──────────────────────────────────────────────────────────────────────────
if menu == "🧪 Hydrochimie & Labo":
    st.subheader("🧪 Module d'Analyse Hydrochimique Quantitative")
    st.info("Téléversez vos données de laboratoire (formats .csv ou .xlsx). Le système calculera automatiquement le SAR, le MAR et l'IQE pour évaluer la qualité des eaux de la Sanaga.")

    # Exemple de structure attendue pour guider l'utilisateur
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

    # Zone de téléversement
    uploaded_file = st.file_uploader("Glissez-déposez le fichier de résultats du laboratoire ici", type=["csv", "xlsx"])

    # Données par défaut si aucun fichier n'est téléversé
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_labo = pd.read_csv(uploaded_file)
            else:
                df_labo = pd.read_excel(uploaded_file)
            st.success("✅ Fichier chargé avec succès !")
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")
            df_labo = None
    else:
        st.warning("⚠️ Aucun fichier fourni. Affichage des données de simulation de la Sanaga.")
        df_labo = pd.DataFrame({
            "Station": ["Mbam à Goura", "Sanaga à Nachtigal", "Sanaga à Édéa", "Djerem à Mbakaou"],
            "Calcium_meq": [1.5, 2.2, 2.0, 1.1],
            "Magnesium_meq": [0.9, 1.4, 1.8, 0.7],
            "Sodium_meq": [1.1, 0.7, 2.1, 0.5],
            "pH": [7.1, 7.3, 6.5, 6.9],
            "Conductivite_uS": [140, 160, 240, 95]
        })

    if df_labo is not None:
        # --- CALCULS HYDROCHIMIQUES ---
        # 1. Calcul du SAR
        df_labo['SAR'] = df_labo['Sodium_meq'] / np.sqrt((df_labo['Calcium_meq'] + df_labo['Magnesium_meq']) / 2)
        df_labo['SAR'] = df_labo['SAR'].round(2)

        # 2. Calcul du MAR
        df_labo['MAR (%)'] = (df_labo['Magnesium_meq'] * 100) / (df_labo['Calcium_meq'] + df_labo['Magnesium_meq'])
        df_labo['MAR (%)'] = df_labo['MAR (%)'].round(1)

        # 3. Calcul de l'IQE (Formule indicielle empirique simplifiée pour la maquette)
        # Idéal pH = 7 (note max). Pénalité si trop acide ou alcalin + pénalité conductivité
        penalite_ph = np.abs(df_labo['pH'] - 7.0) * 15
        penalite_ec = (df_labo['Conductivite_uS'] / 500) * 20
        df_labo['IQE'] = (100 - (penalite_ph + penalite_ec)).clip(lower=0, upper=100).round(1)

        # Interprétation de la qualité pour l'agriculture (SAR)
        df_labo['Aptitude Irrigation (SAR)'] = np.where(df_labo['SAR'] < 10, "Excellent (S1)", 
                                               np.where(df_labo['SAR'] < 18, "Bon (S2)", "Médiocre (S3/S4)"))

        # Affichage du tableau de bord chimique mis à jour
        st.markdown("### 📊 Résultats des Évaluations Automatisées")
        st.dataframe(df_labo, use_container_width=True)

        # Visualisation graphique comparative
        st.markdown("### 📉 Comparaison des indices du bassin")
        c_graph1, c_graph2 = st.columns(2)
        
        with c_graph1:
            fig_sar = go.Figure([go.Bar(x=df_labo['Station'], y=df_labo['SAR'], marker_color=COLOR_RIVER, text=df_labo['SAR'], textposition='auto')])
            fig_sar.update_layout(title="Indice SAR par Station (Risque d'Alcalinisation)")
            style_fig(fig_sar, 300)
            st.plotly_chart(fig_sar, use_container_width=True)
            
        with c_graph2:
            fig_iqe = go.Figure([go.Bar(x=df_labo['Station'], y=df_labo['IQE'], marker_color=COLOR_GREEN, text=df_labo['IQE'], textposition='auto')])
            fig_iqe.update_layout(title="Indice Général de Qualité de l'Eau (IQE / 100)")
            style_fig(fig_iqe, 300)
            st.plotly_chart(fig_iqe, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────
# MODULE 1 : CARTE TEMPS RÉEL (SIG) & SIMULATION DOCK
# ──────────────────────────────────────────────────────────────────────────
elif menu == "🗺️ Carte Temps Réel (SIG)":
    
    col_map, col_ctrl = st.columns([2, 1])
    
    with col_map:
        st.subheader("Visualisation Cartographique du Réseau")
        
        # Coordonnées approximatives des points clés sur la Sanaga
        locations = {
            "Lom Pangar (Barrage)": [5.383, 13.500],
            "Nachtigal (Barrage)": [4.350, 11.633],
            "Station Goura (Mbam)": [4.712, 11.250],
            "Zone Aval Édéa": [3.800, 10.133],
            "kikot": [4.1697057,11.0186578]
        }
        # base map
        m = Map(location=[4.6, 11.8], zoom_start=7, tiles="CartoDB dark_matter")

        # Création de la carte Folium centrée sur le Cameroun / Sanaga
        # allow upload or use local path
        # 1. COUCHE RASTER : GÉOTIFF DU MNT / BASSIN VERSANT
        uploaded_tif = st.file_uploader(
       "Charger un fichier GeoTIFF (Bassin)", type=["tif", "tiff"]
        )
        chemin_tif = None

        if uploaded_tif is not None:
                chemin_tif = uploaded_tif
        elif os.path.exists("data/MNT_SANAGA_EPSG4326.tif"):
                chemin_tif = "data/MNT_SANAGA_EPSG4326.tif"

        if chemin_tif:
            try:
                with rasterio.open(chemin_tif) as src:
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            message="Setting the shape on a NumPy array has been deprecated",
                        )
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
                       minx, miny, maxx, maxy = (b.left,b.bottom,b.right,b.top,)
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
        except Exception as e:
                st.warning(f"Impossible de charger le calque du bassin versant : {e}")

        # 2. COUCHE VECTORIELLE : HYDROGRAPHIE DE LA SANAGA
        shp_hydro_path = "data/hydrographie sanaga.shp"
        gdf_hydro = None

        if os.path.exists(shp_hydro_path):
            try:
                gdf_hydro = gpd.read_file(shp_hydro_path)
            except Exception as e:
                st.warning(f"Erreur lecture hydrographie locale : {e}")
        else:
            uploaded_hydro = st.file_uploader(
                "Uploader hydrographie (.zip)", type=["zip"], key="hydro_zip"
            )
            if uploaded_hydro is not None:
                with tempfile.NamedTemporaryFile(
                    suffix=".zip", delete=False
                ) as tmp:
                    tmp.write(uploaded_hydro.getbuffer())
                    tmp_zip = tmp.name
                try:
                    gdf_hydro = gpd.read_file(f"zip://{tmp_zip}")
                except Exception as e:
                    st.warning(f"Erreur lecture zip hydrographie : {e}")
                finally:
                    os.remove(tmp_zip)

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

        # 3. COUCHE VECTORIELLE : EXUTOIRES DE LA SANAGA (Double Détection)
        shp_exut_path = "data/exutoires de la sanaga.shp"
        gdf_exutoires = None

        if os.path.exists(shp_exut_path):
            try:
                gdf_exutoires = gpd.read_file(shp_exut_path)
            except Exception as e:
                st.warning(f"Erreur lecture exutoires locaux : {e}")
        else:
            uploaded_exut = st.file_uploader(
                "Uploader exutoires (.zip)", type=["zip"], key="exut_zip"
            )
            if uploaded_exut is not None:
                with tempfile.NamedTemporaryFile(
                    suffix=".zip", delete=False
                ) as tmp:
                    tmp.write(uploaded_exut.getbuffer())
                    tmp_zip = tmp.name
                try:
                    gdf_exutoires = gpd.read_file(f"zip://{tmp_zip}")
                except Exception as e:
                    st.warning(f"Erreur lecture zip exutoires : {e}")
                finally:
                    os.remove(tmp_zip)

            if gdf_exutoires is not None and not gdf_exutoires.empty:
                if gdf_exutoires.crs is None or gdf_exutoires.crs.to_string() != "EPSG:4326":
                    gdf_exutoires = gdf_exutoires.to_crs("EPSG:4326")
            
                # --- DETECTION AUTOMATIQUE DE LA COLONNE DE NOM ---
                # On cherche une colonne qui contient 'nom', 'station', 'id' ou 'label' (sans s'occuper des majuscules)
                colonnes_possibles = [c for c in gdf_exutoires.columns if any(x in c.lower() for x in ["nom", "stat", "id", "lab"])]
                colonne_cible = colonnes_possibles[0] if colonnes_possibles else None

                # Configuration dynamique de l'infobulle
                if colonne_cible:
                    infobulle = folium.GeoJsonTooltip(
                        fields=[colonne_cible],
                        aliases=["Station : "],
                        localize=True
                     )
                else:
                    infobulle = folium.GeoJsonTooltip(fields=[gdf_exutoires.columns[0]], aliases=["Index : "])

                # Ajout à la carte
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
    # Add your markers
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

    st_folium(m, width="100%", height=600)
    with col_ctrl:
        st.subheader("🎛️ Module de Simulation")
        actif = st.selectbox("Sélectionner un actif", ["Barrage de Nachtigal", "Barrage de Lom Pangar", "Barrage de Song Loulou"])
        scenario = st.selectbox("Scénario", ["Ouverture des vannes", "Étiage sévère (Saison sèche)", "Crue décennale"])
        
        debit_simule = st.slider("Volume d'eau injecté / régulé (m³/s)", min_value=500, max_value=3000, value=1200, step=100)
        
        st.markdown("### 🔀 Propagation estimée")
        # Calculs fictifs pour l'animation de la maquette
        temps_calcul = 14 - int(debit_simule/300)
        hauteur_calcul = round(0.1 + (debit_simule/4000), 2)
        
        st.metric(label="⏱️ Temps d'arrivée à l'aval", value=f"+{temps_calcul}h 15min")
        st.metric(label="📈 Variation Hauteur Critique", value=f"+{hauteur_calcul} m", delta=f"{hauteur_calcul}m", delta_color="inverse")
        
        if st.button("⚡ SIMULER L'IMPACT SUR LE RÉSEAU", type="primary"):
            st.success("Simulation injectée dans le moteur de calcul hydrologique !")

    st.markdown("---")
    
    with col_graph:
        st.subheader("📈 Débit du fleuve (m³/s) — Station Goura (Mbam)")
        
        # Données de débits fictives pour le graphique
        heures = [f"{h:02d}:00" for h in range(0, 25, 4)]
        debit_reel = [700, 850, 1400, 1650, 1300, 950, 800]
        seuil_alerte = [1200] * len(heures)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=heures, y=debit_reel, name="Débit Actuel (IoT)", line=dict(color=COLOR_RIVER, width=3)))
        fig.add_trace(go.Scatter(x=heures, y=seuil_alerte, name="Seuil d'Alerte", line=dict(color=COLOR_LATERITE, dash="dash")))
        
        # Si l'utilisateur clique sur le bouton de simulation, on trace une courbe prédictive
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

# ──────────────────────────────────────────────────────────────────────────
# MODULE 2 : SCÈNE 3D (SIMULACRE)
# ──────────────────────────────────────────────────────────────────────────
elif menu == "📐 Scène 3D & Simulation":
    st.subheader("📐 Jumeau de Scène Immersif (Simulation Géométrique 3D)")
    st.info("Dans l'application finale, cette zone intègre un moteur WebGL (Cesium/Three.js) chargé de restituer le relief du lit du fleuve et les structures des barrages.")
    
    # Simulation graphique d'une section du barrage
    st.markdown("### Coupe schématique de la retenue d'eau (Simulation Visuelle)")
    niveau_eau = st.slider("Ajuster le niveau de la retenue de Lom Pangar (mètres)", 650, 675, 668)
    
    # Création d'un graphique à barres simulant le niveau d'eau contre la structure
    fig_3d = go.Figure()
    fig_3d.add_trace(go.Bar(x=["Mur du Barrage"], y=[675], name="Structure Béton", marker_color="#5B7186", width=0.3))
    fig_3d.add_trace(go.Bar(x=["Niveau d'Eau Actuel"], y=[niveau_eau], name="Volume d'Eau", marker_color=COLOR_RIVER, width=0.3))
    fig_3d.update_layout(yaxis=dict(range=[640, 680]), barmode='group')
    style_fig(fig_3d, 350)
    st.plotly_chart(fig_3d, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────
# MODULE 3 : ANALYTICS & GIRE
# ──────────────────────────────────────────────────────────────────────────
elif menu == "📊 Analytics & GIRE":
    st.subheader("📊 Tableau de Bord de Gestion Intégrée des Ressources en Eau (GIRE)")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume Global du Bassin", "8.4 Milliards m³", "Normal")
    c2.metric("Stress Hydrique Sectoriel", "Faible (Saison des pluies)", "-12% de risques")
    c3.metric("Indice de Qualité de l'Eau", "84 / 100", "Stable")
    
    st.markdown("### Répartition des usages de l'eau de la Sanaga (Demande vs Allocation)")
    labels = ['Hydroélectricité', 'Eau Potable (Camwater)', 'Agriculture & Irrigation', 'Besoins Écologiques']
    values = [75, 12, 8, 5]
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4,
                                      marker_colors=[COLOR_RIVER, COLOR_CYAN, COLOR_AMBER, COLOR_GREEN])])
    style_fig(fig_pie, 350)
    st.plotly_chart(fig_pie, use_container_width=True)
    # À insérer dans l'onglet "Analytics & GIRE" de votre app.py
    st.markdown("### 🍃 Évaluation de l'Empreinte Carbone du Complexe Hydroélectrique")

    # Calcul fictif basé sur la production globale affichée (933 MW soit 933 000 kW)
    puissance_kw = 933000 

     # Émissions moyennes évitées par rapport au thermique (environ 750g de CO2 par kWh)
    co2_evite_par_heure = round((puissance_kw * 0.750) / 1000, 2) # en tonnes de CO2

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.metric(
            label="📉 Émissions de CO₂ évitées en direct", 
            value=f"{co2_evite_par_heure} Tonnes / heure",
            delta="Par rapport au Fioul/Gaz"
         )
    with col_c2:
        # Simulation des émissions internes des sédiments du réservoir
        st.metric(
            label="💨 Émissions endogènes estimées (Méthane CH₄)", 
            value="12.4 g CO2eq / kWh",
            delta="Statut : Stable",
            delta_color="inverse"
         )
# ──────────────────────────────────────────────────────────────────────────
# MODULE 5 : CAPTEURS & MAINTENANCE (VUE RESPONSIVE)
# ──────────────────────────────────────────────────────────────────────────
else:
    st.subheader("🛠️ État de Santé du Réseau IoT (Vue Terrain & Mobile)")
    st.warning("Cette vue bascule en format vertical condensé lorsqu'elle est ouverte sur un smartphone par les techniciens.")
    
    # Tableau de maintenance des stations
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
    
        incident = st.text_area(
        "Description du problème (ex: Capteur obstrué par des sédiments ou problème d'alimentation solaire)"
        )
    
    # Correction de la fonction ici ⬇️
        submit = st.form_submit_button("Envoyer l'alerte à la salle de contrôle")
    
        if submit:
            st.success(f"Rapport envoyé avec succès pour la {station_select} !")
