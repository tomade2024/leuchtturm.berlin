import json
from pathlib import Path

import streamlit as st
import folium
from folium.features import CustomIcon
from streamlit_folium import st_folium

st.set_page_config(page_title="Berlin – Einrichtungen & Radiozone", layout="wide")

# -----------------------------
# Konfiguration / Defaults
# -----------------------------
DEFAULT_CENTER = (52.52, 13.405)  # Berlin Mitte
DEFAULT_ZOOM = 11

DATA_DIR = Path("data")
ICON_PATH = Path("icons") / "lighthouse.svg"

LAYER_SPECS = [
    ("Feuerwachen", DATA_DIR / "feuerwehr.geojson"),
    ("Polizeiwachen", DATA_DIR / "polizei.geojson"),
    ("Schulen", DATA_DIR / "schulen.geojson"),
]

# -----------------------------
# UI
# -----------------------------
st.title("Interaktive Karte Berlin: Feuerwachen, Polizeiwachen, Schulen + Radiozone")

with st.sidebar:
    st.header("Einstellungen")

    radius_km = st.slider("Radiozone (Radius in km)", min_value=1, max_value=20, value=3, step=1)

    st.caption("Zentrum der Radiozone per Klick auf die Karte setzen (siehe Karte).")
    if st.button("Zentrum zurücksetzen"):
        st.session_state["center"] = DEFAULT_CENTER

# Session-State für Zentrum
if "center" not in st.session_state:
    st.session_state["center"] = DEFAULT_CENTER

# -----------------------------
# Hilfsfunktionen
# -----------------------------
def load_geojson(path: Path):
    if not path.exists():
        return None, f"Datei nicht gefunden: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"Fehler beim Laden {path}: {e}"

def add_geojson_markers(m: folium.Map, geojson_obj: dict, layer_name: str, icon: CustomIcon):
    layer = folium.FeatureGroup(name=layer_name, show=True)
    features = geojson_obj.get("features", [])

    for feat in features:
        geom = feat.get("geometry", {})
        props = feat.get("properties", {}) or {}

        if geom.get("type") != "Point":
            continue

        # GeoJSON: [lon, lat]
        coords = geom.get("coordinates", [])
        if not coords or len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]

        label = props.get("name") or props.get("titel") or props.get("title") or ""
        popup_html = f"<strong>{layer_name}</strong><br>{label}"

        folium.Marker(
            location=(lat, lon),
            icon=icon,
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(layer)

    layer.add_to(m)

# -----------------------------
# Karte bauen
# -----------------------------
m = folium.Map(location=st.session_state["center"], zoom_start=DEFAULT_ZOOM, control_scale=True, tiles=None)

# Basemap (OSM)
folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="&copy; OpenStreetMap-Mitwirkende",
    name="OpenStreetMap",
    control=False,
).add_to(m)

# Leuchtturm-Icon (SVG)
if ICON_PATH.exists():
    lighthouse_icon = CustomIcon(str(ICON_PATH), icon_size=(26, 26), icon_anchor=(13, 26))
else:
    # Fallback: Standard-Marker, falls Icon fehlt
    lighthouse_icon = None

# Daten-Layer
for layer_name, path in LAYER_SPECS:
    geo, err = load_geojson(path)
    if err:
        st.warning(err)
        continue

    if lighthouse_icon:
        add_geojson_markers(m, geo, layer_name, lighthouse_icon)
    else:
        # Fallback ohne CustomIcon
        layer = folium.FeatureGroup(name=layer_name, show=True)
        for feat in geo.get("features", []):
            geom = feat.get("geometry", {})
            props = feat.get("properties", {}) or {}
            if geom.get("type") != "Point":
                continue
            coords = geom.get("coordinates", [])
            if not coords or len(coords) < 2:
                continue
            lon, lat = coords[0], coords[1]
            label = props.get("name") or ""
            folium.Marker(
                location=(lat, lon),
                popup=f"<strong>{layer_name}</strong><br>{label}",
            ).add_to(layer)
        layer.add_to(m)

# Radiozone (Kreis)
folium.Circle(
    location=st.session_state["center"],
    radius=radius_km * 1000,  # Meter
    color="#ff6600",
    fill=True,
    fill_opacity=0.2,
    weight=2,
    popup=f"Radiozone: {radius_km} km",
).add_to(m)

# Klick-Handler-Hinweis (kleine Tooltip-Markierung am Zentrum)
folium.Marker(
    location=st.session_state["center"],
    tooltip="Zentrum der Radiozone (klicken Sie irgendwo auf die Karte, um es zu ändern)",
).add_to(m)

# Layer Control
folium.LayerControl(collapsed=False).add_to(m)

# -----------------------------
# Render + Interaktion
# -----------------------------
col1, col2 = st.columns([3, 1])

with col1:
    # st_folium liefert u.a. last_clicked zurück
    out = st_folium(m, height=720, width=None)

    # Wenn geklickt, Zentrum updaten
    if out and out.get("last_clicked"):
        lat = out["last_clicked"]["lat"]
        lng = out["last_clicked"]["lng"]
        st.session_state["center"] = (lat, lng)

with col2:
    st.subheader("Status")
    st.write("Zentrum:", f"{st.session_state['center'][0]:.5f}, {st.session_state['center'][1]:.5f}")
    st.write("Radius:", f"{radius_km} km")
    st.caption("Hinweis: Die Radiozone ist eine grobe Visualisierung (Kreis).")

st.caption("Datenquellen: GeoJSON-Dateien in /data. Basiskarte: OpenStreetMap.")
