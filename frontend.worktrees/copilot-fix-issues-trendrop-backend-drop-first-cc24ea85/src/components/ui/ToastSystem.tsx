import { toast as sonnerToast } from "sonner";

export const showToast = {
  success: (message: string, description?: string) => {
    sonnerToast.success(message, {
      description,
      style: {
        background: "#111118",
        border: "1px solid rgba(29, 158, 117, 0.25)",
        boxShadow: "0 4px 20px rgba(29, 158, 117, 0.08)",
        color: "#f0f0ff",
      },
    });
  },
  error: (message: string, description?: string) => {
    sonnerToast.error(message, {
      description,
      style: {
        background: "#111118",
        border: "1px solid rgba(230, 57, 70, 0.25)",
        boxShadow: "0 4px 20px rgba(230, 57, 70, 0.08)",
        color: "#f0f0ff",
      },
    });
  },
  warning: (message: string, description?: string) => {
    sonnerToast.warning(message, {
      description,
      style: {
        background: "#111118",
        border: "1px solid rgba(239, 159, 39, 0.25)",
        boxShadow: "0 4px 20px rgba(239, 159, 39, 0.08)",
        color: "#f0f0ff",
      },
    });
  },
  info: (message: string, description?: string) => {
    sonnerToast.info(message, {
      description,
      style: {
        background: "#111118",
        border: "1px solid rgba(127, 119, 221, 0.25)",
        boxShadow: "0 4px 20px rgba(127, 119, 221, 0.08)",
        color: "#f0f0ff",
      },
    });
  },
  trendAlert: (message: string, songName: string) => {
    sonnerToast(message, {
      description: `🔥 New rising trend detected: "${songName}"!`,
      style: {
        background: "#111118",
        border: "1px solid rgba(230, 57, 70, 0.4)",
        boxShadow: "0 6px 24px rgba(230, 57, 70, 0.15)",
        color: "#f0f0ff",
      },
    });
  },
};
