import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import Home from "./pages/Home";
import ChangeDetectionDemo from "./pages/ChangeDetectionDemo";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Router>
      <div className="flex flex-col min-h-screen">
        {/* Navbar */}
        <header className="bg-white shadow p-4 flex justify-between">
          <Link to="/" className="text-xl font-bold text-indigo-600">
            ARES
          </Link>
          <nav className="space-x-4">
            <Link to="/" className="text-gray-600 hover:text-indigo-600">
              Home
            </Link>
            <Link
              to="/change-detection-demo"
              className="text-gray-600 hover:text-indigo-600"
            >
              Change Detection Demo
            </Link>
          </nav>
        </header>

        {/* Routes */}
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route
              path="/change-detection-demo"
              element={<ChangeDetectionDemo />}
            />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
