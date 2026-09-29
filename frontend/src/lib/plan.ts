import { useUserStore } from "@/store/useAppStore";

export const PRO_UNLOCK_ALL = true;

export function useEffectivePlan(): string {
  const storePlan = useUserStore((s) => s.plan) || "free";
  return PRO_UNLOCK_ALL ? "pro" : storePlan;
}

export function getEffectivePlan(storePlan?: string): string {
  return PRO_UNLOCK_ALL ? "pro" : (storePlan || "free");
}
