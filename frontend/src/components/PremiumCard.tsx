import * as React from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";

export interface PremiumCardProps extends HTMLMotionProps<"div"> {
  glowColor?: "red" | "purple" | "teal" | "amber" | "none";
  delayIndex?: number;
  hoverEffect?: "scale" | "lift" | "glow" | "none";
}

export const PremiumCard = React.forwardRef<HTMLDivElement, PremiumCardProps>(
  ({ className, children, glowColor = "none", delayIndex = 0, hoverEffect = "scale", ...props }, ref) => {
    const glowClasses = {
      none: "border-border/60 bg-card",
      red: "border-primary-red/30 shadow-[0_0_15px_rgba(230,57,70,0.12)] bg-card/90",
      purple: "border-purple/30 shadow-[0_0_15px_rgba(127,119,221,0.12)] bg-card/90",
      teal: "border-teal/30 shadow-[0_0_15px_rgba(29,158,117,0.12)] bg-card/90",
      amber: "border-amber/30 shadow-[0_0_15px_rgba(239,159,39,0.12)] bg-card/90",
    };

    const hoverAnimation = hoverEffect === "scale"
      ? { scale: 1.015, y: -2 }
      : hoverEffect === "lift"
      ? { y: -4 }
      : hoverEffect === "glow"
      ? { scale: 1.01, boxShadow: "0 0 25px rgba(255,255,255,0.06)" }
      : undefined;

    return (
      <motion.div
        ref={ref as any}
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: delayIndex * 0.04, ease: "easeOut" }}
        whileHover={hoverAnimation}
        className={cn(
          "rounded-xl border backdrop-blur-md p-5 transition-all duration-300 relative overflow-hidden",
          glowClasses[glowColor],
          className
        )}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

PremiumCard.displayName = "PremiumCard";
