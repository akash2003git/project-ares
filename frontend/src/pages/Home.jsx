import { Link } from "react-router-dom";
import { Bell, Database, Satellite } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Home() {
  const { user } = useAuth();

  // user will be null if not logged in, or an object if logged in.
  const isLoggedIn = !!user;
  const ctaPath = isLoggedIn ? "/dashboard" : "/signup";
  const ctaText = isLoggedIn ? "Go to Dashboard" : "Get Started";

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      {/* Call to Action */}
      <section
        className="py-20 text-white text-center bg-cover bg-center"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1663427929868-3941f957bb36?q=80&w=1632&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D')",
        }}
      >
        <div className="py-20 px-6 rounded-xl">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to revolutionize road monitoring?
          </h2>
          <p className="text-lg md:text-xl mb-6">
            Join Project ARES today and experience the future of automated
            infrastructure intelligence.
          </p>
          <Link
            to={ctaPath}
            className="bg-indigo-600 text-white px-8 py-3 rounded-lg font-semibold shadow-lg hover:bg-indigo-500 transition"
          >
            {ctaText}
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 bg-white">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-800 mb-12">
            Why Project ARES?
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="p-6 bg-white rounded-xl shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1">
              <Satellite className="h-10 w-10 text-indigo-600 mb-4" />
              <h3 className="text-xl font-semibold mb-2">
                Automated Road Extraction
              </h3>
              <p className="text-gray-600">
                Leverages high-resolution satellite imagery to automatically
                identify and map roads, reducing manual survey effort.
              </p>
            </div>

            <div className="p-6 bg-white rounded-xl shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1">
              <Database className="h-10 w-10 text-indigo-600 mb-4" />
              <h3 className="text-xl font-semibold mb-2">
                GIS Database Integration
              </h3>
              <p className="text-gray-600">
                Keeps road databases up to date, ensuring accuracy for planning,
                navigation, and emergency services.
              </p>
            </div>

            <div className="p-6 bg-white rounded-xl shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1">
              <Bell className="h-10 w-10 text-indigo-600 mb-4" />
              <h3 className="text-xl font-semibold mb-2">
                Change Detection & Alerts
              </h3>
              <p className="text-gray-600">
                Detects new or altered roads and instantly alerts stakeholders
                for faster response and planning.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-800 mb-12">
            Key Use Cases
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="space-y-6">
              <div className="p-6 bg-white rounded-xl shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1">
                <h3 className="text-xl font-semibold mb-2 text-indigo-600">
                  Urban & Rural Planning
                </h3>
                <p className="text-gray-600">
                  Monitor unauthorized constructions and update zoning decisions
                  with the most current infrastructure data.
                </p>
              </div>

              <div className="p-6 bg-white rounded-xl shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1">
                <h3 className="text-xl font-semibold mb-2 text-indigo-600">
                  Disaster Management
                </h3>
                <p className="text-gray-600">
                  Identify accessible routes after disasters, aiding evacuation
                  and relief logistics.
                </p>
              </div>
            </div>

            <div className="space-y-6">
              <div className="p-6 bg-white rounded-xl shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1">
                <h3 className="text-xl font-semibold mb-2 text-indigo-600">
                  Environmental Monitoring
                </h3>
                <p className="text-gray-600 mb-0">
                  Detect illegal road construction in protected areas to prevent
                  deforestation and habitat fragmentation.
                </p>
              </div>

              <div className="p-6 bg-white rounded-xl shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1">
                <h3 className="text-xl font-semibold mb-2 text-indigo-600">
                  Infrastructure Maintenance
                </h3>
                <p className="text-gray-600">
                  Automate road inventory updates to improve maintenance
                  scheduling and resource allocation.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto bg-gradient-to-r from-indigo-700 via-indigo-800 to-indigo-900 text-white py-10 shadow-inner">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center">
          <p className="text-center md:text-left mb-4 md:mb-0">
            &copy; 2025 Project ARES. All rights reserved.
          </p>
          <div className="flex space-x-4">
            <Link
              to="#"
              className="hover:text-gray-300 transition font-semibold"
            >
              Privacy
            </Link>
            <Link
              to="#"
              className="hover:text-gray-300 transition font-semibold"
            >
              Terms
            </Link>
            <Link
              to="/contact"
              className="hover:text-gray-300 transition font-semibold"
            >
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
