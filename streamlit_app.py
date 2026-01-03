import json
from pathlib import Path

import streamlit as st
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium

st.set_page_config(page_title="Berlin – Einrichtungen & Radiozone", layout="wide")

DEFAULT_CENTER = (52.5200, 13.4050)
DEFAULT_ZOOM = 11
DATA_DIR = Path("data")

LAYER_SPECS = [
    ("Feuerwachen", DATA_DIR / "feuerwehr.geojson"),
    ("Polizeiwachen", DATA_DIR / "polizei.geojson"),
    ("Schulen", DATA_DIR / "schulen.geojson"),
]

# Inline-SVG (Leuchtturm) als DivIcon -> keine Abhängigkeit von icons/ im Deploy
LIGHTHOUSE_SVG = """
<div style="
  transform: translate(-12px,-24px);
  width:24px;height:24px;
">
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <path fill="#111" d="M11 2h2v2h-2V2zm-1 3h4l1 4H9l1-4zm-1 5h6l1 12H8L9 10zm2 2v8h2v-8h-2z"/>
  <path fill="#111" d="M4 9l3-2v2L4 11V9zm16 0v2l-3-2V7l3 2z"/>
</svg>
</div>
"""

def load_geojson(path: Path):
    if not path.exists():
        return None, f"Datei nicht gefunden: {path} (liegt sie wirklich im GitHub-Repo?)"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"Fehler beim Laden {path}: {e}"

def add_points(m: folium.Map, geo: dict, layer_name: str):
    fg = folium.FeatureGroup(name=layer_name, show=True)
    for feat in geo.get("features", []):
        geom = feat.get("geometry", {}) or {}
        props = feat.get("properties", {}) or {}

        if geom.get("type") != "Point":
            continue

        coords = geom.get("coordinates", [])
        if not coords or len(coords) < 2:
            continue

        lon, lat = coords[0], coords[1]
        label = props.get("name") or props.get("titel") or props.get("title") or ""

        folium.Marker(
            location=(lat, lon),
            icon=DivIcon(html=LIGHTHOUSE_SVG),
            popup=folium.Popup(f"<strong>{layer_name}</strong><br>{label}", max_width=320),
        ).add_to(fg)

    fg.add_to(m)

st.title("Interaktive Karte Berlin: Feuerwachen, Polizeiwachen, Schulen + Radiozone")

with st.sidebar:
    st.header("Einstellungen")
    radius_km = st.slider("Radiozone (Radius in km)", 1, 20, 3, 1)
    if st.button("Zentrum zurücksetzen"):
        st.session_state["center"] = DEFAULT_CENTER
        st.session_state["last_click"] = None

# Session State
if "center" not in st.session_state:
    st.session_state["center"] = DEFAULT_CENTER
if "last_click" not in st.session_state:
    st.session_state["last_click"] = None

# Karte bauen
m = folium.Map(location=st.session_state["center"], zoom_start=DEFAULT_ZOOM, control_scale=True)

folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="&copy; OpenStreetMap-Mitwirkende",
    name="OpenStreetMap",
    control=False,
).add_to(m)

# Daten layern
for layer_name, path in LAYER_SPECS:
    geo, err = load_geojson(path)
    if err:
        st.warning(err)
        continue
    add_points(m, geo, layer_name)

# Radiozone
folium.Circle(
    location=st.session_state["center"],
    radius=radius_km * 1000,
    weight=2,
    fill=True,
    fill_opacity=0.2,
    popup=f"Radiozone: {radius_km} km",
).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# Rendern
out = st_folium(m, height=720, key="map")  # key hilft gegen instabile Reruns

# Klick verarbeiten – nur wenn NEU (verhindert Loops)
if out and out.get("last_clicked"):
    lat = float(out["last_clicked"]["lat"])
    lng = float(out["last_clicked"]["lng"])
    new_click = (round(lat, 6), round(lng, 6))

    if st.session_state["last_click"] != new_click:
        st.session_state["last_click"] = new_click
        st.session_state["center"] = (lat, lng)
        st.rerun()

st.caption("Daten: GeoJSON in /data (Koordinaten: [LON, LAT]). Basiskarte: OpenStreetMap.")
