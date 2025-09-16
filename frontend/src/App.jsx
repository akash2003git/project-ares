import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import { useState, useEffect } from "react";
import L from "leaflet";
import "./App.css";

// Fix default Leaflet icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png",
});

// Helper: Auto-fit bounds when new data is loaded
function FitBounds({ data }) {
  const map = useMap();
  useEffect(() => {
    if (data && data.coordinates && data.coordinates.length > 0) {
      const geoJsonLayer = L.geoJSON(data);
      map.fitBounds(geoJsonLayer.getBounds(), { padding: [20, 20] });
    }
  }, [data, map]);
  return null;
}

function App() {
  const [changes, setChanges] = useState(null);

  useEffect(() => {
    fetch("http://localhost:5000/api/detect_changes?week1=1&week2=2")
      .then((response) => response.json())
      .then((data) => setChanges(data))
      .catch((error) => console.error("Error fetching data:", error));
  }, []);

  const newRoadsStyle = { color: "green", weight: 4, opacity: 0.9 };
  const removedRoadsStyle = { color: "red", weight: 4, opacity: 0.9 };

  const defaultPosition = [21.01, 79.11]; // fallback

  return (
    <div className="App">
      <h1>Road Change Detection</h1>
      <div className="map-container">
        <MapContainer
          center={defaultPosition}
          zoom={14}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
          />

          {changes && changes.new_roads && (
            <>
              <GeoJSON data={changes.new_roads} style={newRoadsStyle} />
              <FitBounds data={changes.new_roads} />
            </>
          )}
          {changes && changes.removed_roads && (
            <GeoJSON data={changes.removed_roads} style={removedRoadsStyle} />
          )}
        </MapContainer>
      </div>

      {changes && (
        <div className="report">
          <h2>Change Report</h2>
          <p style={{ color: "green" }}>
            New Roads Length: {changes.new_length_m} m
          </p>
          <p style={{ color: "red" }}>
            Removed Roads Length: {changes.removed_length_m} m
          </p>
          <p>Total Change: {changes.total_change_m} m</p>
          {changes.alert ? (
            <p style={{ color: "orange", fontWeight: "bold" }}>
              Significant change detected!
            </p>
          ) : (
            <p style={{ color: "gray" }}> No significant changes.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
