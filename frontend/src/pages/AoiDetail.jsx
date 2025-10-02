import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import apiClient from "../api/apiClient";

// Helper function for a clean timestamp format (reused from Dashboard)
const formatDate = (isoString) => {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

export default function AoiDetail() {
  // Get the AOI ID from the URL (e.g., from /aois/123)
  const { aoiId } = useParams();

  // State for data
  const [aoi, setAoi] = useState(null);
  const [featuresGeojson, setFeaturesGeojson] = useState(null);

  // State for UI
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAoiData = useCallback(async () => {
    setLoading(true);
    setError(null);

    // Use a Promise.all to fetch the AOI details and the features concurrently
    try {
      const [detailsResponse, featuresResponse] = await Promise.all([
        // 1. Fetch ALL AOIs and filter for the specific one (since we don't have a /aoi/<id> endpoint)
        // In a production app, you'd add a dedicated GET /api/aois/<id> endpoint.
        apiClient.get("/api/aois"),

        // 2. Fetch the latest road features GeoJSON
        apiClient.get(`/api/aois/${aoiId}/latest_features`),
      ]);

      // Filter the list of all AOIs to find the current one
      const currentAoi = detailsResponse.data.find(
        (a) => a.id === parseInt(aoiId),
      );

      if (!currentAoi) {
        setError(`AOI with ID ${aoiId} not found or you are unauthorized.`);
        setLoading(false);
        return;
      }

      setAoi(currentAoi);
      setFeaturesGeojson(featuresResponse.data);
    } catch (err) {
      console.error(`Error fetching data for AOI ${aoiId}:`, err);
      const errorMessage =
        err.response?.data?.error ||
        `Failed to load AOI ${aoiId} details or features.`;
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [aoiId]);

  useEffect(() => {
    fetchAoiData();
  }, [fetchAoiData]);

  if (loading) {
    return (
      <div className="p-8 text-center">
        <h1 className="text-3xl font-bold text-gray-800">
          Loading AOI Details...
        </h1>
        <p className="mt-4 text-gray-600">
          Retrieving features for AOI ID: {aoiId}
        </p>
        {/* Spinner */}
        <svg
          className="animate-spin h-8 w-8 mx-auto mt-8 text-indigo-500"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div
          className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"
          role="alert"
        >
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
        <Link
          to="/dashboard"
          className="mt-4 inline-block text-indigo-600 hover:text-indigo-800"
        >
          &larr; Back to Dashboard
        </Link>
      </div>
    );
  }

  // Features count for display
  const featureCount = featuresGeojson?.features?.length || 0;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <h1 className="text-3xl font-extrabold text-gray-900 truncate">
          AOI: {aoi.name}
        </h1>
        <Link
          to="/dashboard"
          className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
        >
          &larr; Back to Dashboard
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* -------------------- AOI Metadata Column -------------------- */}
        <div className="md:col-span-1 space-y-4">
          <h2 className="text-xl font-semibold text-gray-700 border-b pb-2">
            AOI Details
          </h2>
          <div className="text-sm space-y-2">
            <p>
              <strong>ID:</strong> {aoi.id}
            </p>
            <p>
              <strong>Image Name:</strong> {aoi.image_name}
            </p>
            <p>
              <strong>Frequency:</strong>{" "}
              <span className="font-bold bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full text-xs">
                {aoi.frequency}
              </span>
            </p>
            <p>
              <strong>Created:</strong> {formatDate(aoi.created_at)}
            </p>
            <p>
              <strong>Latest Features:</strong> {featureCount} roads detected
            </p>
            <p className="break-words text-xs text-gray-500 mt-2">
              <strong>BBOX (WKT):</strong> {aoi.bbox_wkt || "Not available"}
            </p>
          </div>

          <h2 className="text-xl font-semibold text-gray-700 border-b pb-2 pt-4">
            Actions
          </h2>
          <div className="space-y-3">
            {/* Placeholder for the change detection button */}
            <button className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50">
              Detect Changes (Requires 2+ Snapshots)
            </button>

            {/* Placeholder for the processing button */}
            <button className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50">
              Process New Snapshot (Simulate Schedule)
            </button>

            {/* Placeholder for the deletion button */}
            <button className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50">
              Delete AOI
            </button>
          </div>
        </div>

        {/* -------------------- Map/GeoJSON Visualization Column -------------------- */}
        <div className="md:col-span-2 bg-gray-100 p-4 rounded-lg shadow-inner h-[600px]">
          <h2 className="text-xl font-semibold text-gray-700 mb-4">
            Latest Road Features Map
          </h2>

          {/* !!! MAP INTEGRATION GOES HERE !!!
                        
                        You would integrate a library like:
                        1. Leaflet (with react-leaflet)
                        2. Mapbox GL JS (with react-map-gl)
                        
                        And pass 'featuresGeojson' to a GeoJSON layer to draw the features.
                        
                        For now, we'll display the raw GeoJSON data.
                    */}

          <div className="h-full overflow-y-scroll bg-white p-3 border rounded">
            <pre className="text-xs text-gray-700 whitespace-pre-wrap">
              {JSON.stringify(featuresGeojson, null, 2)}
            </pre>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            {featureCount > 0
              ? `Displaying raw GeoJSON for ${featureCount} features.`
              : "No features found in the latest snapshot."}
          </p>
        </div>
      </div>
    </div>
  );
}
