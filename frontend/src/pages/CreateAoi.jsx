import { useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/apiClient"; // Your configured axios instance

// --- DEMO-SPECIFIC IMAGE OPTIONS ---
// The available TIFF files located in the backend root directory
const DEMO_IMAGE_OPTIONS = [
  "test_image_1.tif",
  "test_image_2.tif",
  "test_image_3.tif",
  "test_image_4.tif",
  // We'll also include an empty/default option
];

// Define the available frequency options
const FREQUENCY_OPTIONS = ["Manual", "Weekly", "Monthly", "Quarterly"];

export default function CreateAoi() {
  const [name, setName] = useState("");
  // Initialize image selection with the first demo image (or a placeholder)
  const [imageName, setImageName] = useState(DEMO_IMAGE_OPTIONS[0]);
  const [frequency, setFrequency] = useState(FREQUENCY_OPTIONS[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Basic validation
    if (!name || !imageName || imageName === "") {
      setError("Please provide a name for the AOI and select a demo image.");
      setLoading(false);
      return;
    }

    const aoiData = {
      name: name,
      image_name: imageName, // This will be the selected value from the dropdown
      frequency: frequency,
    };

    try {
      // Send POST request to the backend endpoint /api/aois
      const response = await apiClient.post("/api/aois", aoiData);

      console.log("AOI created successfully:", response.data);

      // On success, redirect to the dashboard
      navigate("/dashboard", {
        state: {
          successMessage: `AOI "${name}" created and processing started.`,
        },
      });
    } catch (err) {
      console.error("AOI Creation Error:", err);
      // Extract a specific error message from the backend response if available
      const errorMessage =
        err.response?.data?.error ||
        "Failed to create AOI. Please check the image file is accessible by the backend.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-3xl font-extrabold text-gray-900 mb-6">
        Create New Area of Interest (Demo)
      </h1>
      <p className="text-gray-600 mb-8">
        Select a name and a demo image to start road feature monitoring.
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

      <form
        onSubmit={handleSubmit}
        className="space-y-6 bg-white p-8 rounded-lg shadow-xl"
      >
        <div>
          <label
            htmlFor="name"
            className="block text-sm font-medium text-gray-700"
          >
            AOI Name
          </label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            placeholder="e.g., Central Park Road Network"
          />
        </div>

        <div>
          <label
            htmlFor="imageName"
            className="block text-sm font-medium text-gray-700"
          >
            Source Image Selection (Demo)
          </label>
          <select
            id="imageName"
            value={imageName}
            onChange={(e) => setImageName(e.target.value)}
            required
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
          >
            <option value="" disabled>
              -- Select a Demo Image --
            </option>
            {DEMO_IMAGE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs text-gray-500">
            In a production environment, this would be a map area selection.
          </p>
        </div>

        <div>
          <label
            htmlFor="frequency"
            className="block text-sm font-medium text-gray-700"
          >
            Monitoring Frequency
          </label>
          <select
            id="frequency"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
          >
            {FREQUENCY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {loading ? (
            <svg
              className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
          ) : (
            "Create AOI & Process Initial Snapshot"
          )}
        </button>
      </form>
    </div>
  );
}
