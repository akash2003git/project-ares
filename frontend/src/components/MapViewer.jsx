import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import { useState, useEffect, useCallback } from "react";
const L = window.L;

// Leaflet Setup
if (L && L.Icon && L.Icon.Default) {
  delete L.Icon.Default.prototype._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl:
      "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  });
}

// Helper: Auto-fit bounds when new data is loaded
function FitBounds({ data }) {
  const map = useMap();
  useEffect(() => {
    // Check if the data is valid GeoJSON with features
    if (
      data &&
      data.type === "FeatureCollection" &&
      data.features.length > 0 &&
      L
    ) {
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

// --- Main Application Component ---
const defaultPosition = [21.01, 79.11]; // Nagpur fallback

export default function MapViewer() {
  // Renamed state variables
  const [baseData, setBaseData] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  const [changes, setChanges] = useState(null);
  const [statusMessage, setStatusMessage] = useState(
    "Upload two GeoJSON files and click 'Detect Changes'.",
  );
  // Renamed filename states
  const [baseFileName, setBaseFileName] = useState("Base Data File (Time A)");
  const [comparisonFileName, setComparisonFileName] = useState(
    "Comparison Data File (Time B)",
  );

  // --- File Handling ---

  // Reads a file and parses it as GeoJSON, updating the corresponding state.
  const handleFileUpload = (event, setData, setFileName) => {
    const file = event.target.files[0];
    if (!file) return;

    // Clear changes when a new file is uploaded
    setChanges(null);
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

  // Sends the uploaded files to the backend API for processing.
  const detectChanges = useCallback(async () => {
    if (!baseData || !comparisonData) {
      setStatusMessage(
        "Please upload both Base Data and Comparison Data GeoJSON files.",
      );
      return;
    }

    setStatusMessage("Uploading files to backend for change detection...");
    setChanges(null);

    const formData = new FormData();
    // Retrieve files directly from the input elements
    const file1 = document.getElementById("file1").files[0];
    const file2 = document.getElementById("file2").files[0];

    if (!file1 || !file2) {
      setStatusMessage("Error: Files are missing from input fields.");
      return;
    }

    formData.append("file_old", file1);
    formData.append("file_new", file2);

    try {
      const res = await fetch(
        "http://127.0.0.1:5000/api/demo/change_detection",
        {
          method: "POST",
          body: formData,
        },
      );

      if (!res.ok) {
        // Attempt to read error message from backend
        const errorText = await res.text();
        throw new Error(
          `Backend error (${res.status}): ${errorText.substring(0, 100)}...`,
        );
      }

      const data = await res.json();
      setChanges(data);
      setStatusMessage("Change detection complete. Visualizing results.");
    } catch (err) {
      console.error("Error calling backend:", err);
      setChanges(null); // Clear changes on error
      setStatusMessage(`Error: ${err.message}`);
    }
  }, [baseData, comparisonData]);

  // --- Styles ---
  // Styles for detected changes (visible after detection)
  const newRoadsStyle = {
    color: "#10B981", // Emerald Green
    weight: 5,
    opacity: 1,
    dashArray: "8, 8",
  };
  const removedRoadsStyle = {
    color: "#EF4444", // Red
    weight: 5,
    opacity: 1,
    dashArray: "12, 6",
  };

  // Styles for uploaded raw files
  const baseStyle = {
    color: "#4F46E5", // Indigo Blue
    weight: 2,
    opacity: 0.6,
  };
  const comparisonStyle = {
    // Renamed style
    color: "#FBBF24", // Amber Yellow
    weight: 2,
    opacity: 0.6,
  };

  // Pick data to fit bounds: prioritize detected changes, otherwise combine uploaded files
  let dataForBounds = null;
  if (changes) {
    // If changes exist, use the combined features from the changes object
    dataForBounds = changes;
  } else if (baseData && comparisonData) {
    // If files are loaded but no changes are detected yet, combine them to fit the area of interest
    dataForBounds = {
      type: "FeatureCollection",
      features: [...baseData.features, ...comparisonData.features],
    };
  } else if (baseData) {
    dataForBounds = baseData;
  } else if (comparisonData) {
    dataForBounds = comparisonData;
  }

  // Boolean flags for UI state
  const isDetecting =
    statusMessage.includes("Detecting") || statusMessage.includes("Uploading");
  // showRawData is true if files are loaded and change detection hasn't been run yet
  const showRawData = !changes && (baseData || comparisonData);
  const hasChanges = changes?.features?.length > 0;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
      <header className="bg-white shadow p-4 sticky top-0 z-10">
        <h1 className="text-3xl font-bold text-gray-800 tracking-tight">
          Change Detection Demo
        </h1>
      </header>

      <main className="flex flex-1 flex-col lg:flex-row p-4 space-y-4 lg:space-y-0 lg:space-x-4 overflow-hidden">
        {/* Control Panel */}
        <div className="lg:w-1/3 xl:w-1/4 bg-white p-6 rounded-xl shadow-lg space-y-6 flex flex-col">
          <h2 className="text-xl font-semibold text-gray-700 border-b pb-2 mb-2">
            Upload & Process
          </h2>

          {/* Upload Base Data */}
          <div className="space-y-2">
            <label
              htmlFor="file1"
              className="block text-sm font-medium text-gray-700"
            >
              <span className="font-bold text-indigo-600">
                Base Data (Time A)
              </span>
            </label>
            <input
              id="file1"
              type="file"
              accept=".geojson, .json"
              onChange={(e) =>
                handleFileUpload(e, setBaseData, setBaseFileName)
              }
              className="hidden"
            />
            <button
              onClick={() => document.getElementById("file1").click()}
              className="w-full text-left p-3 border-2 border-dashed border-gray-300 rounded-lg hover:border-indigo-500 transition text-sm text-gray-600 hover:text-indigo-600 truncate"
            >
              <span
                className={
                  baseData ? "text-green-600 font-medium" : "text-gray-500"
                }
              >
                {baseData ? "Loaded: " : "Upload: "}{" "}
              </span>
              {baseFileName}
            </button>
          </div>

          {/* Upload Comparison Data */}
          <div className="space-y-2">
            <label
              htmlFor="file2"
              className="block text-sm font-medium text-gray-700"
            >
              <span className="font-bold text-indigo-600">
                Comparison Data (Time B)
              </span>
            </label>
            <input
              id="file2"
              type="file"
              accept=".geojson, .json"
              onChange={(e) =>
                handleFileUpload(e, setComparisonData, setComparisonFileName)
              }
              className="hidden"
            />
            <button
              onClick={() => document.getElementById("file2").click()}
              className="w-full text-left p-3 border-2 border-dashed border-gray-300 rounded-lg hover:border-indigo-500 transition text-sm text-gray-600 hover:text-indigo-600 truncate"
            >
              <span
                className={
                  comparisonData
                    ? "text-green-600 font-medium"
                    : "text-gray-500"
                }
              >
                {comparisonData ? "Loaded: " : "Upload: "}{" "}
              </span>
              {comparisonFileName}
            </button>
          </div>

          {/* Detect Button */}
          <button
            onClick={detectChanges}
            disabled={!baseData || !comparisonData || isDetecting}
            className="mt-6 w-full py-3 px-4 bg-indigo-600 text-white font-semibold rounded-lg shadow-md hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed transition duration-150"
          >
            {isDetecting ? "Processing..." : "Detect Changes"}
          </button>

          <p className="text-center text-sm text-gray-500 border-t pt-4 italic">
            {statusMessage}
          </p>

          {/* Legend */}
          <div className="pt-4 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Map Legend
            </h3>
            <ul className="text-xs space-y-1">
              <li
                className={`flex items-center ${showRawData ? "font-semibold" : "opacity-50"}`}
              >
                <span
                  className="w-6 h-1 mr-2 rounded"
                  style={{
                    backgroundColor: baseStyle.color,
                    opacity: baseStyle.opacity,
                  }}
                ></span>
                <span className="text-gray-600">Base Data (Time A)</span>
              </li>
              <li
                className={`flex items-center ${showRawData ? "font-semibold" : "opacity-50"}`}
              >
                <span
                  className="w-6 h-1 mr-2 rounded"
                  style={{
                    backgroundColor: comparisonStyle.color,
                    opacity: comparisonStyle.opacity,
                  }}
                ></span>
                <span className="text-gray-600">Comparison Data (Time B)</span>
              </li>
              <li
                className={`flex items-center ${hasChanges ? "font-semibold" : "opacity-50"}`}
              >
                <span
                  className="w-6 h-1 mr-2 rounded"
                  style={{ backgroundColor: newRoadsStyle.color }}
                ></span>
                <span className="text-green-600 font-medium">
                  New Road (ADDED)
                </span>
              </li>
              <li
                className={`flex items-center ${hasChanges ? "font-semibold" : "opacity-50"}`}
              >
                <span
                  className="w-6 h-1 mr-2 rounded"
                  style={{ backgroundColor: removedRoadsStyle.color }}
                ></span>
                <span className="text-red-600 font-medium">
                  Removed Road (DELETED)
                </span>
              </li>
            </ul>
          </div>

          {/* Change Report */}
          {hasChanges && (
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

            {/* Render Base Data */}
            {baseData && (
              <GeoJSON key="base" data={baseData} style={baseStyle} />
            )}
            {/* Render Comparison Data */}
            {comparisonData && (
              <GeoJSON
                key="comparison"
                data={comparisonData}
                style={comparisonStyle}
              />
            )}

            {/* Overlay detected changes on top */}
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

            {/* Fit bounds to data */}
            {dataForBounds && <FitBounds data={dataForBounds} />}
          </MapContainer>
        </div>
      </main>
    </div>
  );
}
