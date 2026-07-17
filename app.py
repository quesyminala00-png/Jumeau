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
# -----------------------------
# Configuration générale
# -----------------------------
st.set_page_config(
    page_title="Jumeau Numérique - BV Sanaga",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
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


# -----------------------------
# CSS & Style
# -----------------------------
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
        .river-flow { height: 4px; width: 100%; margin: 4px 0 22px 0; border-radius: 2px; background: linear-gradient(90deg, var(--laterite) 0%, var(--river-blue) 35%, var(--river-cyan) 60%, var(--hydro-green) 100%); background-size: 200% 100%; animation: flow 6s linear infinite; }
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


# -----------------------------
# Modules (chacun est une fonction)
# -----------------------------

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
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")
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
        # Calculs
        df = df.copy()
        # éviter les erreurs si colonnes manquantes
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

col_map, col_ctrl = st.columns([2, 1])

with col_map:
    st.subheader("Visualisation Cartographique du Réseau")

    # usual markers
    locations = {
        "Lom Pangar (Barrage)": [5.383, 13.500],
        "Nachtigal (Barrage)": [4.350, 11.633],
        "Station Goura (Mbam)": [4.712, 11.250],
        "Zone Aval Édéa": [3.800, 10.133],
    }

    # base map
    m = Map(location=[4.6, 11.8], zoom_start=7, tiles="CartoDB dark_matter")

    # allow upload or use local path
    uploaded = st.file_uploader("Charger un fichier GeoTIFF (single-band)", type=["tif", "tiff"])
    chemin_tif = None
    if uploaded is not None:
        # rasterio can open file-like objects
        chemin_tif = uploaded
    else:
        # fallback to a path on disk — set this if you want an automatic local test file
        # chemin_tif = "MNT_SANAGA_EPSG4326.tif"
        chemin_tif = None

    if chemin_tif:
        try:
            # Open (uploaded BytesIO or path) with rasterio
            import warnings  # add near the top of the file if not present

            with rasterio.open(chemin_tif) as src:
                # read the first band as float (handle nodata)
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message="Setting the shape on a NumPy array has been deprecated",
                        category=DeprecationWarning,
                    )
                    # make an explicit copy-in-dtype to avoid shape/view surprises
                    data = np.array(src.read(1), dtype="float32", copy=True)
                nodata = src.nodata
                if nodata is not None:
                    data[data == nodata] = np.nan

                # optionally downsample for performance (uncomment / tune)
                # max_pixels = 1024 * 1024
                # if src.width * src.height > max_pixels:
                #     scale = (max_pixels / (src.width * src.height)) ** 0.5
                #     out_shape = (int(src.count), int(src.height * scale), int(src.width * scale))
                #     data = src.read(1, out_shape=out_shape[1:]).astype('float32')

                # Reproject to EPSG:4326 if needed
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
                    # compute bounds (minx, miny, maxx, maxy) for the reprojected image
                    minx, miny, maxx, maxy = array_bounds(height, width, transform)
                else:
                    # already EPSG:4326 or no CRS — use original bounds
                    b = src.bounds  # left, bottom, right, top
                    minx, miny, maxx, maxy = b.left, b.bottom, b.right, b.top

                # prepare bounds for folium: [[south, west], [north, east]]
                bounds = [[miny, minx], [maxy, maxx]]

                # Handle case where all data is nan
                if np.all(np.isnan(data)):
                    st.warning("Raster contains only nodata / NaN values.")
                else:
                    # Normalize and apply colormap to produce RGBA image (0-255 uint8)
                    vmin = np.nanmin(data)
                    vmax = np.nanmax(data)
                    norm = Normalize(vmin=vmin, vmax=vmax, clip=True)
                    cmap = cm.get_cmap("Blues")  # choose any matplotlib colormap
                    # map normalized data to RGBA floats in [0,1]; nan -> transparent
                    mapped = cmap(norm(np.nan_to_num(data, nan=vmin)))
                    # set alpha to 0 where data was NaN to make transparent background
                    mapped[..., 3] = np.where(np.isnan(data), 0.0, mapped[..., 3])
                    img = (mapped * 255).astype("uint8")  # shape (H, W, 4)

                    # Create the overlay
                    ImageOverlay(
                        image=img,
                        bounds=bounds,
                        opacity=0.6,
                        name="Bassin Versant",
                        mercator_project=True,  # folium will handle WebMercator tiling if needed
                    ).add_to(m)

                    folium.LayerControl().add_to(m)

        except Exception as e:
            st.warning(f"Impossible de charger le calque du bassin versant (Erreur : {e}). Vérifiez le fichier .tif")
    try:
        # Lecture du shapefile des cours d'eau
        gdf_hydro = gpd.read_file("data/Hydrographie sanaga.shp")

        # Reprojection automatique en EPSG:4326 (Indispensable pour Folium)
        if gdf_hydro.crs != "EPSG:4326":
            gdf_hydro = gdf_hydro.to_crs("EPSG:4326")

        # Ajout du tracé des rivières sur la carte (en bleu)
        folium.GeoJson(
            gdf_hydro,
            name="Réseau Hydrographique",
            style_function=lambda feature: {
                "color": "#1f78b4",  # Bleu rivière
                "weight": 2.5,  # Épaisseur de la ligne
                "opacity": 0.8,
            },
        ).add_to(m)
    except Exception as e:
        st.warning(f"Erreur lors du chargement de l'hydrographie : {e}")

    # 2. CHARGEMENT ET AFFICHAGE DES EXUTOIRES (.SHP)
    try:
        # Lecture du shapefile des exutoires (points)
        gdf_exutoires = gpd.read_file("data/exutoires de la sanaga.shp")

        if gdf_exutoires.crs != "EPSG:4326":
            gdf_exutoires = gdf_exutoires.to_crs("EPSG:4326")

        # Ajout des exutoires sous forme de petits cercles colorés
        folium.GeoJson(
            gdf_exutoires,
            name="Exutoires du Bassin",
            marker=folium.CircleMarker(
                radius=5,
                color="#e31a1c",  # Rouge exutoire
                fill=True,
                fill_color="#e31a1c",
                fill_opacity=0.9,
            ),
            tooltip=folium.GeoJsonTooltip(
                fields=["NOM"] if "NOM" in gdf_exutoires.columns else None,
                aliases=["Station :"] if "NOM" in gdf_exutoires.columns else None,
            ),
        ).add_to(m)
    except Exception as e:
        st.warning(f"Erreur lors du chargement des exutoires : {e}")
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

    # render map
    st_folium(m, width="100%", height=600)

def module_simulation():
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
            st.success(f"Rapport envoyé avec succès pour la {station_select} !")


# -----------------------------
# Barre latérale + Navigation
# -----------------------------

def sidebar_nav():
    st.sidebar.markdown("## 🌊 JUMEAU SANAGA")
    role = st.sidebar.selectbox("👤 Profil Utilisateur", ["Superviseur GIRE", "Ingénieur Barrage (NHPC/EDC)", "Hydrochimiste / Labo", "Agent de Terrain", "Décideur / Ministère"]) 
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧭 Modules intégrés")
    menu = st.sidebar.radio(
        "Navigation principale",
        ["Accueil", "🗺️ Carte Temps Réel (SIG)", "📐 Scène 3D & Simulation", "📊 Analytics & GIRE", "🧪 Hydrochimie & Labo", "🛠️ Capteurs & Alertes Mobile"]
    )
    st.sidebar.markdown("---")
    st.sidebar.info(f"Rôle actuel : **{role}**\n\nInterface optimisée pour le bassin de la Sanaga.")
    return menu, role


# -----------------------------
# Main
# -----------------------------

def main():
    inject_css()
    menu, role = sidebar_nav()
    header(role)

    if menu == "Accueil":
        st.title("Tableau de bord — Jumeau numérique de la Sanaga")
        st.write("Bienvenue — utilisez la navigation latérale pour ouvrir les modules.")

    elif menu == "🗺️ Carte Temps Réel (SIG)":
        col_map, col_ctrl = st.columns([2, 1])
        with col_map:
            module_map()
        with col_ctrl:
            module_simulation()

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
