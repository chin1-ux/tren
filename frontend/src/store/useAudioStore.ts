import { create } from "zustand";

export interface AudioTrack {
  id: string | number;
  title: string;
  artist: string;
  coverUrl?: string;
  instagramAudioId?: string;
  viralStartSec: number;
  viralDurationSec: number;
  previewUrl?: string | null;
  sourceType?: "catalog" | "original" | "stream";
}

interface AudioStoreState {
  currentTrack: AudioTrack | null;
  isPlaying: boolean;
  isLoading: boolean;
  currentTime: number;
  duration: number;
  isLooping: boolean;
  isMuted: boolean;
  error: string | null;

  // Actions
  setTrack: (track: AudioTrack) => void;
  playTrack: (track: AudioTrack) => void;
  togglePlay: () => void;
  pause: () => void;
  resume: () => void;
  seek: (seconds: number) => void;
  toggleLoop: () => void;
  stop: () => void;
  updateProgress: (currentTime: number, duration: number) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

// Global Audio Singleton instance
let globalAudio: HTMLAudioElement | null = null;

function getAudio(): HTMLAudioElement | null {
  if (typeof window === "undefined") return null;
  if (!globalAudio) {
    globalAudio = new Audio();
    globalAudio.preload = "auto";
  }
  return globalAudio;
}

/**
 * Prime audio element synchronously inside a user gesture (click event)
 * to unlock audio on mobile Safari and Chrome before an asynchronous network fetch.
 */
export function primeAudio() {
  const audio = getAudio();
  if (!audio) return;
  try {
    if (!audio.src) {
      audio.src = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
    }
    const p = audio.play();
    if (p !== undefined) {
      p.catch(() => {});
    }
  } catch {
    // Ignore initial priming errors
  }
}

export const useAudioStore = create<AudioStoreState>((set, get) => {
  // Bind native audio event listeners when on client
  if (typeof window !== "undefined") {
    const audio = getAudio();
    if (audio) {
      audio.ontimeupdate = () => {
        const cur = audio.currentTime;
        const dur = audio.duration || 30;
        const { currentTrack, isLooping } = get();

        if (currentTrack && isLooping && currentTrack.viralStartSec !== undefined) {
          const windowEnd = currentTrack.viralStartSec + (currentTrack.viralDurationSec || 15);
          if (cur >= windowEnd && windowEnd > currentTrack.viralStartSec) {
            audio.currentTime = currentTrack.viralStartSec;
            set({ currentTime: currentTrack.viralStartSec });
            return;
          }
        }
        set({ currentTime: cur, duration: dur });
      };

      audio.oncanplay = () => {
        set({ isLoading: false });
      };

      audio.onwaiting = () => {
        set({ isLoading: true });
      };

      audio.onended = () => {
        const { isLooping, currentTrack } = get();
        if (isLooping && currentTrack) {
          audio.currentTime = currentTrack.viralStartSec || 0;
          audio.play().catch(() => {});
        } else {
          set({ isPlaying: false });
        }
      };

      audio.onerror = (e) => {
        console.warn("[useAudioStore] Audio error:", e);
        set({ isPlaying: false, isLoading: false, error: "Preview unavailable" });
      };
    }
  }

  return {
    currentTrack: null,
    isPlaying: false,
    isLoading: false,
    currentTime: 0,
    duration: 0,
    isLooping: true, // Default to true for creators to hear the viral hook loop
    isMuted: false,
    error: null,

    setTrack: (track) => set({ currentTrack: track, error: null }),

    playTrack: (track) => {
      const audio = getAudio();
      const current = get().currentTrack;

      if (current && String(current.id) === String(track.id) && audio?.src === track.previewUrl) {
        // Toggle play/pause for same track
        if (get().isPlaying) {
          audio?.pause();
          set({ isPlaying: false });
        } else {
          audio?.play().then(() => set({ isPlaying: true })).catch(() => {});
        }
        return;
      }

      // New track
      set({
        currentTrack: track,
        isPlaying: Boolean(track.previewUrl),
        isLoading: Boolean(track.previewUrl),
        currentTime: track.viralStartSec || 0,
        error: null,
      });

      if (!audio || !track.previewUrl) {
        set({ isLoading: false });
        return;
      }

      audio.src = track.previewUrl;
      audio.currentTime = track.viralStartSec || 0;
      audio
        .play()
        .then(() => {
          set({ isPlaying: true, isLoading: false });
        })
        .catch((err) => {
          console.warn("[useAudioStore] play() error:", err);
          set({ isPlaying: false, isLoading: false, error: "Unable to play audio" });
        });
    },

    togglePlay: () => {
      const audio = getAudio();
      if (!audio || !get().currentTrack?.previewUrl) return;

      if (get().isPlaying) {
        audio.pause();
        set({ isPlaying: false });
      } else {
        audio
          .play()
          .then(() => set({ isPlaying: true }))
          .catch((err) => {
            console.warn("[useAudioStore] resume play error:", err);
          });
      }
    },

    pause: () => {
      const audio = getAudio();
      audio?.pause();
      set({ isPlaying: false });
    },

    resume: () => {
      const audio = getAudio();
      if (audio && get().currentTrack?.previewUrl) {
        audio.play().then(() => set({ isPlaying: true })).catch(() => {});
      }
    },

    seek: (seconds: number) => {
      const audio = getAudio();
      if (audio) {
        audio.currentTime = seconds;
      }
      set({ currentTime: seconds });
    },

    toggleLoop: () => set((state) => ({ isLooping: !state.isLooping })),

    stop: () => {
      const audio = getAudio();
      if (audio) {
        audio.pause();
        audio.removeAttribute("src");
      }
      set({ currentTrack: null, isPlaying: false, currentTime: 0, isLoading: false });
    },

    updateProgress: (currentTime: number, duration: number) => {
      set({ currentTime, duration: duration || get().duration });
    },

    setLoading: (isLoading: boolean) => set({ isLoading }),
    setError: (error: string | null) => set({ error, isLoading: false, isPlaying: false }),
  };
});
