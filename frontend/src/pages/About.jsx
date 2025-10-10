import React from "react";
import { MapPin } from "lucide-react";

export default function About() {
  return (
    <div className="min-h-screen bg-gray-50 py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <section
          id="about"
          className="bg-white shadow-xl rounded-xl p-8 md:p-12"
        >
          <div className="text-center">
            <h2 className="text-sm font-semibold text-indigo-600 uppercase tracking-wider">
              Our Final Year Project
            </h2>
            <p className="mt-2 text-4xl font-extrabold text-gray-900 sm:text-5xl">
              Road Network Change Detection System
            </p>
            <p className="mt-4 text-xl text-gray-500">
              A geospatial analysis tool to automate the monitoring and updating
              of infrastructure maps.
            </p>
          </div>

          <div className="mt-16 space-y-12">
            {/* PROBLEM STATEMENT */}
            <div className="p-6 bg-indigo-50 border-l-4 border-indigo-600 rounded-lg">
              <h3 className="text-2xl font-bold text-indigo-800 mb-4 flex items-center">
                <MapPin className="w-6 h-6 mr-3" />
                The Problem We Solve
              </h3>
              <p className="mt-2 text-lg text-indigo-700">
                In rapidly developing regions, keeping{" "}
                <b>geographic information system (GIS) data</b> current is a
                major challenge. Traditional methods for identifying new roads
                or decommissioned paths are{" "}
                <b>manual, time-consuming, and prone to human error</b>. This
                lag in data accuracy impacts urban planning, infrastructure
                maintenance, disaster response, and logistics planning. Our
                project aims to <b>automate this critical update process</b>{" "}
                using deep learning and geospatial analysis.
              </p>
            </div>

            {/* KEY FEATURES */}
            <div>
              <h3 className="text-2xl font-bold text-gray-800 mb-6 border-b pb-2">
                Core Features
              </h3>
              <ul className="grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-6 text-lg text-gray-600">
                <li className="flex items-start">
                  <span className="flex-shrink-0 mr-3 text-green-500 font-extrabold text-xl">
                    ✓
                  </span>
                  <div>
                    <strong className="text-gray-900">
                      Automated Change Detection:
                    </strong>{" "}
                    Compares two GeoJSON road network files from different time
                    periods (Time A and Time B) to instantly identify
                    <b>ADDITIONS</b> and <b>DELETIONS</b>.
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 mr-3 text-green-500 font-extrabold text-xl">
                    ✓
                  </span>
                  <div>
                    <strong className="text-gray-900">
                      Geospatial Accuracy:
                    </strong>{" "}
                    Leverages <b>advanced geometric algorithms</b> (e.g.,
                    buffering, topological overlay) to ensure changes are
                    detected precisely.
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 mr-3 text-green-500 font-extrabold text-xl">
                    ✓
                  </span>
                  <div>
                    <strong className="text-gray-900">
                      Interactive Map Visualization:
                    </strong>{" "}
                    Displays the base data, comparison data, and the final
                    changes using <b>Leaflet</b>, allowing users to visually
                    verify results.
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 mr-3 text-green-500 font-extrabold text-xl">
                    ✓
                  </span>
                  <div>
                    <strong className="text-gray-900">
                      AOI Management Dashboard:
                    </strong>{" "}
                    Enables authenticated users to upload, manage, and schedule
                    recurring change detection tasks for specific{" "}
                    <b>Areas of Interest (AOIs)</b>.
                  </div>
                </li>
              </ul>
            </div>

            {/* FUTURE SCOPE */}
            <div>
              <h3 className="text-2xl font-bold text-gray-800 mb-6 border-b pb-2">
                Future Scope & Enhancements
              </h3>
              <ul className="grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-6 text-lg text-gray-600">
                <li className="flex items-start">
                  <span className="flex-shrink-0 mr-3 text-yellow-500 font-extrabold text-xl">
                    →
                  </span>
                  <div>
                    <strong className="text-gray-900">
                      Satellite Integration:
                    </strong>{" "}
                    Connect directly to satellite imagery APIs (e.g., Bhoonidhi,
                    Sentinel, Planet) to automatically generate road network
                    GeoJSON files for a given date.
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 mr-3 text-yellow-500 font-extrabold text-xl">
                    →
                  </span>
                  <div>
                    <strong className="text-gray-900">
                      Road Quality Metrics:
                    </strong>{" "}
                    Implement algorithms to detect{" "}
                    <b>road surface deterioration</b> (e.g., new potholes,
                    widening/narrowing) beyond simple presence/absence.
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 mr-3 text-yellow-500 font-extrabold text-xl">
                    →
                  </span>
                  <div>
                    <strong className="text-gray-900">
                      API Access & Webhooks:
                    </strong>{" "}
                    Provide programmatic access to the change detection engine
                    for integration with third-party GIS applications.
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 mr-3 text-yellow-500 font-extrabold text-xl">
                    →
                  </span>
                  <div>
                    <strong className="text-gray-900">
                      Interactive Reporting:
                    </strong>{" "}
                    Generate detailed PDF or interactive reports summarizing
                    total change length, cost estimates, and map views.
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
