import React, { useState, useEffect, useCallback } from "react";
// Assuming Tailwind CSS is available in the environment

const API_BASE_URL = "/api";

/**
 * Custom hook to simulate fetching existing AOIs (as the backend routes were omitted for brevity).
 */
const useAOIs = () => {
  const [aois, setAois] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real application, this would fetch from /api/aois
    setTimeout(() => {
      setAois([
        {
          id: 1,
          name: "Area 51 - Test Track",
          image_name: "area_51_w1.tiff",
          snapshot_count: 2,
        },
        {
          id: 2,
          name: "Dubai Jebel Ali - Port Expansion",
          image_name: "dubai_port_w1.tiff",
          snapshot_count: 3,
        },
        {
          id: 3,
          name: "Remote Town Site - Needs Second Snapshot",
          image_name: "remote_town_w1.tiff",
          snapshot_count: 1,
        },
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  return { aois, loading, setAois };
};

// --- Sub-Components ---

/**
 * Component to display GeoJSON results as formatted JSON.
 */
const JsonDisplay = ({ data, title }) => (
  <div className="bg-gray-800 p-4 rounded-lg shadow-inner font-mono text-xs text-green-300 h-96 overflow-y-scroll">
    <h3 className="text-sm font-semibold mb-2 text-white border-b border-gray-700 pb-1">
      {title}
    </h3>
    <pre>{JSON.stringify(data, null, 2)}</pre>
  </div>
);

/**
 * Component for the stateless GeoJSON file upload and detection.
 */
const DemoUploader = () => {
  const [fileOld, setFileOld] = useState(null);
  const [fileNew, setFileNew] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleDetect = useCallback(async () => {
    if (!fileOld || !fileNew) {
      setError("Please select both 'Old' and 'New' GeoJSON files.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file_old", fileOld);
    formData.append("file_new", fileNew);

    try {
      const response = await fetch(`${API_BASE_URL}/demo/change_detection`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Stateless detection failed.");
      }
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [fileOld, fileNew]);

  return (
    <div className="p-6 bg-white rounded-xl shadow-lg border border-gray-100">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">
        Stateless GeoJSON Demo
      </h2>
      <p className="text-sm text-gray-500 mb-6">
        Upload two GeoJSON road network files for immediate, database-free
        change detection using the dedicated API route.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Snapshot A (Old)
          </label>
          <input
            type="file"
            accept=".geojson"
            onChange={(e) => setFileOld(e.target.files[0])}
            className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Snapshot B (New)
          </label>
          <input
            type="file"
            accept=".geojson"
            onChange={(e) => setFileNew(e.target.files[0])}
            className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
          />
        </div>
      </div>

      <button
        onClick={handleDetect}
        disabled={loading || !fileOld || !fileNew}
        className="w-full px-4 py-2 bg-indigo-600 text-white font-semibold rounded-full hover:bg-indigo-700 transition duration-150 disabled:bg-indigo-300 disabled:cursor-not-allowed"
      >
        {loading ? "Processing Changes..." : "Run Stateless Detection"}
      </button>

      {error && (
        <p className="mt-4 text-red-600 text-sm font-medium">{error}</p>
      )}

      <div className="mt-6">
        <JsonDisplay
          data={result || {}}
          title="Detection Result (GeoJSON FeatureCollection)"
        />
      </div>
    </div>
  );
};

/**
 * Component for interacting with a specific AOI and its database snapshots.
 */
const AOIChangeDetector = ({ aois, loadingAOIs, refreshAOIs }) => {
  const [selectedAoiId, setSelectedAoiId] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const selectedAoi = aois.find((a) => a.id === parseInt(selectedAoiId));

  // 1. Database Diff Handler
  const handleDetectDatabase = useCallback(async () => {
    if (!selectedAoiId || selectedAoi.snapshot_count < 2) {
      setError(
        "AOI must be selected and must have at least 2 snapshots for comparison.",
      );
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/aois/${selectedAoiId}/detect_changes`,
        {
          method: "GET",
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Database change detection failed.");
      }
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedAoiId, selectedAoi]);

  // 2. Scheduled Processing Simulation Handler
  const handleProcessNewSnapshot = useCallback(async () => {
    if (!selectedAoiId) {
      setError("Please select an AOI to process a new snapshot.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/aois/${selectedAoiId}/process_new_snapshot`,
        {
          method: "POST",
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "New snapshot processing failed.");
      }

      setResult(data);
      refreshAOIs(data.aoi_id); // Update the AOI list to show the new snapshot count (simulated)
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedAoiId, refreshAOIs]);

  return (
    <div className="p-6 bg-white rounded-xl shadow-lg border border-gray-100">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">
        AOI Monitoring & Database Diff
      </h2>
      <p className="text-sm text-gray-500 mb-6">
        Test the scheduled processing simulation and the primary
        database-to-database change detection route.
      </p>

      <div className="mb-6">
        <label
          htmlFor="aoi-select"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Select AOI
        </label>
        <select
          id="aoi-select"
          value={selectedAoiId}
          onChange={(e) => setSelectedAoiId(e.target.value)}
          disabled={loadingAOIs || loading}
          className="w-full p-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="" disabled>
            {loadingAOIs ? "Loading AOIs..." : "Choose an Area of Interest"}
          </option>
          {aois.map((aoi) => (
            <option key={aoi.id} value={aoi.id}>
              {aoi.name} ({aoi.snapshot_count} snapshots)
            </option>
          ))}
        </select>
        {selectedAoi && selectedAoi.snapshot_count < 2 && (
          <p className="mt-2 text-yellow-600 text-xs">
            Requires at least 2 snapshots to run database comparison.
          </p>
        )}
      </div>

      <div className="flex flex-col space-y-3 mb-6">
        <button
          onClick={handleProcessNewSnapshot}
          disabled={loading || !selectedAoiId}
          className="px-4 py-2 bg-green-600 text-white font-semibold rounded-full hover:bg-green-700 transition duration-150 disabled:bg-green-300 disabled:cursor-not-allowed"
        >
          {loading
            ? "Simulating..."
            : "1. Simulate New Snapshot Process (POST)"}
        </button>
        <button
          onClick={handleDetectDatabase}
          disabled={
            loading || !selectedAoiId || selectedAoi?.snapshot_count < 2
          }
          className="px-4 py-2 bg-blue-600 text-white font-semibold rounded-full hover:bg-blue-700 transition duration-150 disabled:bg-blue-300 disabled:cursor-not-allowed"
        >
          {loading
            ? "Detecting Changes..."
            : "2. Run Database Change Detection (GET)"}
        </button>
      </div>

      {error && (
        <p className="mt-4 text-red-600 text-sm font-medium">{error}</p>
      )}

      <div className="mt-6">
        <JsonDisplay data={result || {}} title="API Response" />
      </div>
    </div>
  );
};

const App = () => {
  const { aois, loading: loadingAOIs, setAois } = useAOIs();

  // Simple function to simulate updating the snapshot count after processing
  const refreshAOIs = useCallback(
    (aoiId) => {
      setAois((prevAois) =>
        prevAois.map((aoi) =>
          aoi.id === aoiId
            ? { ...aoi, snapshot_count: aoi.snapshot_count + 1 }
            : aoi,
        ),
      );
    },
    [setAois],
  );

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans">
      <header className="text-center mb-10">
        <h1 className="text-4xl font-extrabold text-gray-900">
          Project Ares: Change Detection Testing Console
        </h1>
        <p className="text-lg text-gray-600 mt-2">
          Verify PostGIS differential analysis and monitoring workflows.
        </p>
      </header>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
        <DemoUploader />
        <AOIChangeDetector
          aois={aois}
          loadingAOIs={loadingAOIs}
          refreshAOIs={refreshAOIs}
        />
      </div>

      <div className="max-w-7xl mx-auto mt-10 p-6 bg-yellow-50 border-l-4 border-yellow-400 rounded-lg">
        <h3 className="text-lg font-semibold text-yellow-800">
          Visualization Note
        </h3>
        <p className="text-sm text-yellow-700">
          In a production environment, the GeoJSON results in the JSON Display
          would be fed to a map library (like Leaflet or Mapbox) to visually
          highlight the added (e.g., green) and removed (e.g., red) roads on top
          of the base map imagery.
        </p>
      </div>
    </div>
  );
};

export default App;
