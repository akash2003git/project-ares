import { useState, useEffect, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import apiClient from "../api/apiClient";

// Define the available frequency options (reused from CreateAoi)
const FREQUENCY_OPTIONS = ["Manual", "Weekly", "Monthly", "Quarterly"];

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
  const { aoiId } = useParams();
  const navigate = useNavigate();

  // State for data
  const [aoi, setAoi] = useState(null);
  const [featuresGeojson, setFeaturesGeojson] = useState(null);

  // State for Update Form
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editFrequency, setEditFrequency] = useState("");

  // State for UI
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // --- Data Fetching Logic ---

  const fetchAoiData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Note: We still fetch the list and filter, as we don't have the dedicated /aois/<id> route.
      const [detailsResponse, featuresResponse] = await Promise.all([
        apiClient.get("/api/aois"),
        apiClient.get(`/api/aois/${aoiId}/latest_features`),
      ]);

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

      // Initialize edit state with current AOI data
      setEditName(currentAoi.name);
      setEditFrequency(currentAoi.frequency);
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

  // --- Delete Functionality ---

  const handleDelete = async () => {
    if (
      !window.confirm(
        `Are you sure you want to permanently delete the AOI "${aoi.name}"? This action cannot be undone.`,
      )
    ) {
      return;
    }

    setIsDeleting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Send DELETE request to the backend endpoint /api/aois/<aoiId>
      await apiClient.delete(`/api/aois/${aoiId}`);

      // On successful deletion, redirect to the dashboard
      navigate("/dashboard", {
        state: {
          successMessage: `AOI "${aoi.name}" (ID: ${aoiId}) was successfully deleted.`,
        },
      });
    } catch (err) {
      console.error("AOI Deletion Error:", err);
      const errorMessage =
        err.response?.data?.error || "Failed to delete AOI. Please try again.";
      setError(errorMessage);
    } finally {
      setIsDeleting(false);
    }
  };

  // --- Update Functionality (with fix for RangeError) ---

  const handleUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    const updateData = {
      name: editName,
      frequency: editFrequency,
    };

    try {
      // Send PUT request
      const response = await apiClient.put(`/api/aois/${aoiId}`, updateData);

      // CRITICAL FIX: Merge the returned data with the existing state to preserve 'created_at'
      setAoi((prevAoi) => ({
        ...prevAoi, // Keep all existing fields (like created_at)
        ...response.data, // Overwrite with updated fields (name, frequency)
      }));

      setSuccessMessage(`AOI "${editName}" updated successfully.`);
      setIsEditing(false); // Close the edit form
    } catch (err) {
      console.error("AOI Update Error:", err);
      const errorMessage =
        err.response?.data?.error ||
        "Failed to update AOI. Please check the input and try again.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // --- NEW Download Functionality ---
  const handleDownloadGeoJSON = () => {
    if (!featuresGeojson) return;

    // 1. Convert the GeoJSON object to a JSON string
    const geoJsonString = JSON.stringify(featuresGeojson, null, 2);

    // 2. Create a Blob (Binary Large Object) from the string
    const blob = new Blob([geoJsonString], { type: "application/json" });

    // 3. Create a temporary URL for the Blob
    const url = URL.createObjectURL(blob);

    // 4. Create a temporary <a> tag to trigger the download
    const link = document.createElement("a");
    link.href = url;

    // Use the AOI name and ID for a clean filename
    const filename = `${aoi.name.replace(/\s/g, "_")}_AOI_${aoi.id}_features.geojson`;
    link.download = filename;

    // 5. Append to body, click, and remove the temporary link
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 6. Clean up the object URL
    URL.revokeObjectURL(url);
  };
  // ------------------------------------

  // --- Render Logic ---

  if (loading && !aoi) {
    // ... (existing loading state)
    return (
      <div className="p-8 text-center">
        <h1 className="text-3xl font-bold text-gray-800">
          Loading AOI Details...
        </h1>
        <p className="mt-4 text-gray-600">
          Retrieving features for AOI ID: {aoiId}
        </p>
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

  if (error && !aoi) {
    // ... (existing error state)
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

  if (!aoi) return null; // Should be handled by loading/error, but defensive check

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

      {successMessage && (
        <div
          className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4"
          role="alert"
        >
          <span className="block sm:inline">{successMessage}</span>
          <button
            onClick={() => setSuccessMessage(null)}
            className="absolute top-0 bottom-0 right-0 px-4 py-3 text-green-700 hover:text-green-900"
          >
            &times;
          </button>
        </div>
      )}

      {error && (
        <div
          className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4"
          role="alert"
        >
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* -------------------- AOI Metadata & Update Column -------------------- */}
        <div className="md:col-span-1 space-y-6">
          {/* --- DETAILS BLOCK --- */}
          <div className="bg-white p-6 rounded-lg shadow-md border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-700 border-b pb-2 mb-3">
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
          </div>

          {/* --- UPDATE FORM BLOCK --- */}
          <div className="bg-white p-6 rounded-lg shadow-md border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-700 border-b pb-2 mb-3">
              Update AOI
            </h2>

            {!isEditing ? (
              <button
                onClick={() => setIsEditing(true)}
                className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Edit Details
              </button>
            ) : (
              <form onSubmit={handleUpdate} className="space-y-4">
                <div>
                  <label
                    htmlFor="editName"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Name
                  </label>
                  <input
                    id="editName"
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    required
                    disabled={loading}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                  />
                </div>
                <div>
                  <label
                    htmlFor="editFrequency"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Frequency
                  </label>
                  <select
                    id="editFrequency"
                    value={editFrequency}
                    onChange={(e) => setEditFrequency(e.target.value)}
                    disabled={loading}
                    className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 sm:text-sm rounded-md"
                  >
                    {FREQUENCY_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex space-x-3">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                  >
                    {loading ? "Saving..." : "Save Changes"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    disabled={loading}
                    className="flex-1 justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* --- ACTIONS BLOCK --- */}
          <div className="bg-white p-6 rounded-lg shadow-md border border-gray-100 space-y-3">
            <h2 className="text-xl font-semibold text-gray-700 border-b pb-2">
              Management
            </h2>

            {/* Delete Button */}
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
            >
              {isDeleting ? "Deleting..." : "Delete AOI"}
            </button>

            {/* Placeholder buttons for future functionality */}
            <button
              disabled
              className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-400"
            >
              Detect Changes (Future Feature)
            </button>
          </div>
        </div>

        {/* -------------------- Map/GeoJSON Visualization Column -------------------- */}
        <div className="md:col-span-2 bg-gray-100 p-4 rounded-lg shadow-inner h-[600px]">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              Latest Road Features
            </h2>

            {/* Download Button */}
            <button
              onClick={handleDownloadGeoJSON}
              disabled={!featuresGeojson || featureCount === 0}
              className="flex items-center space-x-2 px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              <span>Download GeoJSON ({featureCount})</span>
            </button>
          </div>

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
