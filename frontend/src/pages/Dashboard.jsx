import { useAuth } from "../context/AuthContext";
import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import apiClient from "../api/apiClient";

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

const AoiCard = ({ aoi }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300 border border-gray-100">
      <div className="flex justify-between items-start">
        <h2 className="text-xl font-semibold text-gray-900 line-clamp-1">
          {aoi.name}
        </h2>
        {/* Link to a detail page or action */}
        <Link
          to={`/aois/${aoi.id}`}
          className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
        >
          View Details &rarr;
        </Link>
      </div>
      <p className="text-sm text-gray-500 mt-1">ID: {aoi.id}</p>

      <div className="mt-4 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600 font-medium">Image:</span>
          <span className="text-gray-700 truncate max-w-[60%]">
            {aoi.image_name}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 font-medium">Frequency:</span>
          <span className="text-gray-700 font-bold bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full text-xs">
            {aoi.frequency}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 font-medium">Created:</span>
          <span className="text-gray-700">{formatDate(aoi.created_at)}</span>
        </div>
        {/* Optional: Show BBOX info */}
        {aoi.bbox_wkt && (
          <div className="pt-2 border-t border-dashed mt-2">
            <p className="text-xs text-gray-500 line-clamp-1">
              BBOX: {aoi.bbox_wkt.substring(0, 50)}...
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default function Dashboard() {
  const { user } = useAuth();
  const [aois, setAois] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Use useCallback to memoize the fetch function
  const fetchAois = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get("/api/aois");
      setAois(response.data);
    } catch (err) {
      console.error("Error fetching AOIs:", err);
      // Display a user-friendly error message
      const errorMessage =
        err.response?.data?.error ||
        "Failed to load AOIs. Check API connection and ensure you are logged in.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch data on component mount
  useEffect(() => {
    fetchAois();
  }, [fetchAois]);

  // --- Render Logic ---

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
        <p className="mt-4 text-gray-600">Loading AOIs...</p>
        <div className="mt-8 text-center text-indigo-500">
          {/* Simple loading spinner */}
          <svg
            className="animate-spin h-6 w-6 mx-auto"
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
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-extrabold text-gray-900">
          Your Areas of Interest (AOIs)
        </h1>
        <Link
          to="/create-aoi"
          className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-md hover:bg-indigo-700 transition duration-150"
        >
          + Create New AOI
        </Link>
      </div>

      <p className="mt-4 mb-8 text-lg text-gray-600">
        Welcome,{" "}
        <span className="font-semibold text-indigo-600">{user?.email}</span>.
        Here are the road monitoring areas you have configured.
      </p>

      {error && (
        <div
          className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4"
          role="alert"
        >
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {aois.length === 0 ? (
        <div className="mt-16 text-center py-10 border-2 border-dashed border-gray-300 rounded-lg">
          <p className="text-xl text-gray-500 font-medium">
            You haven't created any AOIs yet.
          </p>
          <p className="mt-2 text-gray-500">
            Click the "Create New AOI" button to get started with road feature
            monitoring.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {aois.map((aoi) => (
            <AoiCard key={aoi.id} aoi={aoi} />
          ))}
        </div>
      )}
    </div>
  );
}
