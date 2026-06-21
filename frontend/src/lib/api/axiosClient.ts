import axios from "axios";

export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ||
  (import.meta.env.DEV ? "http://localhost:8000" : "");

const axiosClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

axiosClient.interceptors.request.use(
  (config) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("trendrop_token") : null;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Global API error interception
    const message = error.response?.data?.message || error.message || "An unexpected network error occurred";
    console.error("[API Error]", {
      url: error.config?.url,
      status: error.response?.status,
      message,
    });
    return Promise.reject(error);
  }
);

export default axiosClient;
