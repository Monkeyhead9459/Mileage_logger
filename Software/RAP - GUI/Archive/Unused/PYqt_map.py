import sys
import os
import requests
import folium
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView

GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"  # Replace with your actual key

# Raw GPS points
gps_points = [
    (-43.574744, 172.549143),
    (-43.574500, 172.550000),
    (-43.574200, 172.551200),
    (-43.573900, 172.552300),
]

# Call Roads API
def get_snapped_points(gps_points):
    path = "|".join(f"{lat},{lng}" for lat, lng in gps_points)
    url = "https://roads.googleapis.com/v1/snapToRoads"
    params = {
        "path": path,
        "interpolate": "true",
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    return [
        (p["location"]["latitude"], p["location"]["longitude"])
        for p in data.get("snappedPoints", [])
    ]

# Generate map
def create_map(snapped_points, filename="snapped_map.html"):
    m = folium.Map(location=snapped_points[0], zoom_start=16)
    folium.PolyLine(snapped_points, color="blue", weight=4).add_to(m)
    folium.Marker(snapped_points[0], popup="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(snapped_points[-1], popup="End", icon=folium.Icon(color="red")).add_to(m)
    m.save(filename)

# PyQt GUI to display map
class MapWindow(QMainWindow):
    def __init__(self, html_file):
        super().__init__()
        self.setWindowTitle("Snapped GPS Route")
        self.setGeometry(100, 100, 800, 600)
        browser = QWebEngineView()
        browser.load(f"file:///{os.path.abspath(html_file)}")
        self.setCentralWidget(browser)

if __name__ == "__main__":
    snapped = get_snapped_points(gps_points)
    create_map(snapped)

    app = QApplication(sys.argv)
    window = MapWindow("snapped_map.html")
    window.show()
    sys.exit(app.exec_())