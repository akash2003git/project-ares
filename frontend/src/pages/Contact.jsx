import React, { useState } from "react";
import { Mail, MapPin, Phone, Github, Send } from "lucide-react";

export default function Contact() {
  // State for the dummy contact form
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    message: "",
  });
  const [status, setStatus] = useState(null); // 'submitting', 'success' or 'error'

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Dummy submission function
  const handleSubmit = (e) => {
    e.preventDefault();

    if (!formData.name || !formData.email || !formData.message) {
      setStatus("error");
      return;
    }

    setStatus("submitting");

    // Simulate an API delay
    setTimeout(() => {
      console.log("Form data collected (not sent):", formData);
      setStatus("success");
      setFormData({ name: "", email: "", message: "" }); // Clear form
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="lg:grid lg:grid-cols-2 lg:gap-16">
          {/* Contact Info */}
          <div className="max-w-md mx-auto sm:max-w-none sm:mx-0 py-8">
            <h2 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
              Get In Touch
            </h2>
            <p className="mt-4 text-lg text-gray-500">
              We are the student developers behind this project. We welcome
              feedback, questions, and academic inquiries regarding the
              underlying algorithms and future development plans.
            </p>
            <div className="mt-8 space-y-6">
              <div className="flex items-center">
                <Mail className="flex-shrink-0 h-6 w-6 text-indigo-600" />
                <span className="ml-3 text-base text-gray-700">
                  example@gmail.com
                </span>
              </div>
              <div className="flex items-center">
                <Phone className="flex-shrink-0 h-6 w-6 text-indigo-600" />
                <span className="ml-3 text-base text-gray-700">
                  +91 xxxxxxxxxx
                </span>
              </div>
              <div className="flex items-center">
                <MapPin className="flex-shrink-0 h-6 w-6 text-indigo-600" />
                <span className="ml-3 text-base text-gray-700">
                  Department of Electronics Engineering, [YCCE, Nagpur]
                </span>
              </div>
              <div className="flex items-center pt-4">
                <Github className="flex-shrink-0 h-6 w-6 text-indigo-600" />
                <a
                  href="https://github.com/akash2003git/project-ares"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-3 text-base text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  https://github.com/akash2003git/project-ares
                </a>
              </div>
            </div>
          </div>

          {/* Dummy Contact Form */}
          <div className="mt-12 lg:mt-0 bg-white p-8 rounded-xl shadow-xl">
            <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-y-6">
              <h3 className="text-2xl font-bold text-gray-800 mb-2 border-b pb-2">
                Send us a message
              </h3>

              {/* Name Input */}
              <div>
                <label htmlFor="name" className="sr-only">
                  Full name
                </label>
                <input
                  type="text"
                  name="name"
                  id="name"
                  autoComplete="name"
                  value={formData.name}
                  onChange={handleChange}
                  className="block w-full shadow-sm py-3 px-4 placeholder-gray-500 focus:ring-indigo-500 focus:border-indigo-500 border border-gray-300 rounded-md"
                  placeholder="Full name"
                />
              </div>

              {/* Email Input */}
              <div>
                <label htmlFor="email" className="sr-only">
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="block w-full shadow-sm py-3 px-4 placeholder-gray-500 focus:ring-indigo-500 focus:border-indigo-500 border border-gray-300 rounded-md"
                  placeholder="Email address"
                />
              </div>

              {/* Message Textarea */}
              <div>
                <label htmlFor="message" className="sr-only">
                  Message
                </label>
                <textarea
                  id="message"
                  name="message"
                  rows={4}
                  value={formData.message}
                  onChange={handleChange}
                  className="block w-full shadow-sm py-3 px-4 placeholder-gray-500 focus:ring-indigo-500 focus:border-indigo-500 border border-gray-300 rounded-md"
                  placeholder="Message/Inquiry"
                />
              </div>

              {/* Status Message */}
              {(status === "submitting" ||
                status === "success" ||
                status === "error") && (
                <div className="p-3 rounded-lg" role="alert">
                  {status === "submitting" && (
                    <p className="text-indigo-600 font-medium flex items-center">
                      <svg
                        className="animate-spin h-5 w-5 mr-3 text-indigo-400"
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
                      Sending message...
                    </p>
                  )}
                  {status === "success" && (
                    <p className="text-green-600 font-medium">
                      Thank you! Your inquiry has been noted. We'll be in touch
                      soon.
                    </p>
                  )}
                  {status === "error" && (
                    <p className="text-red-600 font-medium">
                      Please fill out all fields before submitting.
                    </p>
                  )}
                </div>
              )}

              {/* Submit Button */}
              <div>
                <button
                  type="submit"
                  disabled={status === "submitting"}
                  className="inline-flex items-center justify-center w-full px-6 py-3 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                >
                  <Send className="w-5 h-5 mr-2" />
                  Submit Inquiry
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
