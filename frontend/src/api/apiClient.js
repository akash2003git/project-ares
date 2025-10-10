import axios from "axios";
const API_BASE_URL = "http://127.0.0.1:5000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 Unauthorized globally
    if (error.response && error.response.status === 401) {
      console.error("401 Unauthorized: Session invalid or expired.");
    }
    return Promise.reject(error);
  },
);

export default apiClient;
