import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import { useState, useEffect, useCallback } from "react";
import L from "leaflet";

// --- Leaflet Setup ---
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Helper: Auto-fit bounds when new data is loaded
function FitBounds({ data }) {
  const map = useMap();
  useEffect(() => {
    if (data && data.type === "FeatureCollection" && data.features.length > 0) {
      try {
        const geoJsonLayer = L.geoJSON(data);
        map.fitBounds(geoJsonLayer.getBounds(), {
          padding: [40, 40],
          maxZoom: 15,
        });
      } catch (e) {
        console.error("Could not fit bounds: Invalid GeoJSON structure.", e);
      }
    }
  }, [data, map]);
  return null;
}

const defaultPosition = [21.01, 79.11]; // Nagpur fallback

export default function App() {
  const [week1Data, setWeek1Data] = useState(null);
  const [week2Data, setWeek2Data] = useState(null);
  const [changes, setChanges] = useState(null);
  const [statusMessage, setStatusMessage] = useState(
    "Upload two GeoJSON files and click 'Detect Changes'.",
  );
  const [fileName1, setFileName1] = useState("Week 1 File (GeoJSON)");
  const [fileName2, setFileName2] = useState("Week 2 File (GeoJSON)");

  // --- File Handling ---
  const handleFileUpload = (event, setData, setFileName) => {
    const file = event.target.files[0];
    if (!file) return;

    setFileName(file.name);
    setStatusMessage(`Loading ${file.name}...`);
    setData(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target.result);
        if (!json.type || !json.features) {
          throw new Error(
            "Invalid GeoJSON format: Missing 'type' or 'features'.",
          );
        }
        setData(json);
        setStatusMessage(
          `Successfully loaded ${file.name}. Ready for detection.`,
        );
      } catch (error) {
        setData(null);
        setFileName("Error loading file");
        setStatusMessage(
          `Error parsing GeoJSON from ${file.name}: ${error.message}`,
        );
        console.error("File parsing error:", error);
      }
    };
    reader.onerror = () => {
      setStatusMessage("Failed to read file.");
      setData(null);
      setFileName("File read error");
    };
    reader.readAsText(file);
  };

  // --- Call backend for change detection ---
  const detectChanges = useCallback(async () => {
    if (!week1Data || !week2Data) {
      setStatusMessage("Please upload both Week 1 and Week 2 GeoJSON files.");
      return;
    }

    setStatusMessage("Uploading files to backend for change detection...");
    setChanges(null);

    const formData = new FormData();
    formData.append("file_old", document.getElementById("file1").files[0]);
    formData.append("file_new", document.getElementById("file2").files[0]);

    try {
      const res = await fetch(
        "http://127.0.0.1:5000/api/demo/change_detection",
        {
          method: "POST",
          body: formData,
        },
      );

      if (!res.ok) {
        throw new Error(`Backend error: ${res.status}`);
      }

      const data = await res.json();
      setChanges(data);
      setStatusMessage("Change detection complete. Visualizing results.");
    } catch (err) {
      console.error("Error calling backend:", err);
      setStatusMessage(`Error: ${err.message}`);
    }
  }, [week1Data, week2Data]);

  // Styles
  const newRoadsStyle = {
    color: "#10B981",
    weight: 5,
    opacity: 1,
    dashArray: "8, 8",
  };
  const removedRoadsStyle = {
    color: "#EF4444",
    weight: 5,
    opacity: 1,
    dashArray: "12, 6",
  };

  // Pick data to fit bounds: prefer detected changes, else uploaded files
  const dataForBounds =
    changes ||
    (week1Data &&
      week2Data && {
        type: "FeatureCollection",
        features: [...week1Data.features, ...week2Data.features],
      });

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
      <header className="bg-white shadow p-4 sticky top-0 z-10">
        <h1 className="text-3xl font-bold text-gray-800 tracking-tight">
          <span className="text-indigo-600">GeoRoad</span> Change Detection
        </h1>
      </header>

      <main className="flex flex-1 flex-col lg:flex-row p-4 space-y-4 lg:space-y-0 lg:space-x-4 overflow-hidden">
        {/* Control Panel */}
        <div className="lg:w-1/3 xl:w-1/4 bg-white p-6 rounded-xl shadow-lg space-y-6 flex flex-col">
          <h2 className="text-xl font-semibold text-gray-700 border-b pb-2 mb-2">
            Upload Data
          </h2>

          {/* Upload Week 1 */}
          <div className="space-y-2">
            <label
              htmlFor="file1"
              className="block text-sm font-medium text-gray-700"
            >
              <span className="font-bold text-indigo-600">Week 1 Data</span>{" "}
              (Baseline)
            </label>
            <input
              id="file1"
              type="file"
              accept=".geojson, .json"
              onChange={(e) => handleFileUpload(e, setWeek1Data, setFileName1)}
              className="hidden"
            />
            <button
              onClick={() => document.getElementById("file1").click()}
              className="w-full text-left p-3 border-2 border-dashed border-gray-300 rounded-lg hover:border-indigo-500 transition text-sm text-gray-600 hover:text-indigo-600 truncate"
            >
              <span
                className={
                  week1Data ? "text-green-600 font-medium" : "text-gray-500"
                }
              >
                {week1Data ? "Loaded: " : "Upload: "}
              </span>
              {fileName1}
            </button>
          </div>

          {/* Upload Week 2 */}
          <div className="space-y-2">
            <label
              htmlFor="file2"
              className="block text-sm font-medium text-gray-700"
            >
              <span className="font-bold text-indigo-600">Week 2 Data</span>{" "}
              (Comparison)
            </label>
            <input
              id="file2"
              type="file"
              accept=".geojson, .json"
              onChange={(e) => handleFileUpload(e, setWeek2Data, setFileName2)}
              className="hidden"
            />
            <button
              onClick={() => document.getElementById("file2").click()}
              className="w-full text-left p-3 border-2 border-dashed border-gray-300 rounded-lg hover:border-indigo-500 transition text-sm text-gray-600 hover:text-indigo-600 truncate"
            >
              <span
                className={
                  week2Data ? "text-green-600 font-medium" : "text-gray-500"
                }
              >
                {week2Data ? "Loaded: " : "Upload: "}
              </span>
              {fileName2}
            </button>
          </div>

          {/* Detect Button */}
          <button
            onClick={detectChanges}
            disabled={
              !week1Data || !week2Data || statusMessage.includes("Detecting")
            }
            className="mt-6 w-full py-3 px-4 bg-indigo-600 text-white font-semibold rounded-lg shadow-md hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed"
          >
            {statusMessage.includes("Detecting")
              ? "Processing..."
              : "Detect Changes"}
          </button>

          <p className="text-center text-sm text-gray-500 border-t pt-4 italic">
            {statusMessage}
          </p>

          {/* Change Report */}
          {changes && (
            <div className="mt-6 p-4 bg-gray-50 rounded-lg shadow-inner border">
              <h3 className="text-lg font-bold mb-3 text-gray-800">
                Change Report
              </h3>
              <div className="space-y-2">
                <p className="text-green-600 flex justify-between">
                  <span>New Roads:</span>
                  <span className="font-mono font-bold">
                    {changes?.metadata?.new_length_m?.toFixed(2) ?? 0} m
                  </span>
                </p>
                <p className="text-red-600 flex justify-between">
                  <span>Removed Roads:</span>
                  <span className="font-mono font-bold">
                    {changes?.metadata?.removed_length_m?.toFixed(2) ?? 0} m
                  </span>
                </p>
                <p className="text-gray-800 font-bold flex justify-between border-t mt-2 pt-2">
                  <span>Total Change:</span>
                  <span className="font-mono">
                    {changes?.metadata?.total_change_m?.toFixed(2) ?? 0} m
                  </span>
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Map */}
        <div className="lg:flex-1 h-[60vh] lg:h-auto rounded-xl shadow-xl overflow-hidden">
          <MapContainer
            center={defaultPosition}
            zoom={13}
            scrollWheelZoom={true}
            minZoom={10}
            maxZoom={17}
            className="w-full h-full"
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
            />

            {/* Render Features by Change Type */}
            {changes && (
              <>
                <GeoJSON
                  key="new"
                  data={{
                    type: "FeatureCollection",
                    features: changes.features.filter(
                      (f) => f.properties.change_type === "ADDED",
                    ),
                  }}
                  style={newRoadsStyle}
                />
                <GeoJSON
                  key="removed"
                  data={{
                    type: "FeatureCollection",
                    features: changes.features.filter(
                      (f) => f.properties.change_type === "DELETED",
                    ),
                  }}
                  style={removedRoadsStyle}
                />
              </>
            )}

            {/* Fit bounds to changes, else uploaded baseline+comparison */}
            {dataForBounds && <FitBounds data={dataForBounds} />}
          </MapContainer>
        </div>
      </main>
    </div>
  );
}
