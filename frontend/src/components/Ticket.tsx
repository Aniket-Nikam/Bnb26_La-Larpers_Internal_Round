import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

export function TicketCard({
  children,
  onClick,
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      whileHover={!reduce && onClick ? { y: -2 } : {}}
      whileTap={!reduce && onClick ? { scale: 0.985 } : {}}
      onClick={onClick}
      className={`surface relative overflow-hidden ${className}`}
    >
      {children}
    </motion.div>
  );
}

export function TicketDivider() {
  return (
    <div className="relative my-2 flex h-10 w-full items-center">
      <div className="absolute z-0 w-full border-t border-dashed border-white/15" />
      <div className="absolute -left-6 z-10 h-12 w-12 rounded-full bg-[rgb(var(--canvas))]" />
      <div className="absolute -right-6 z-10 h-12 w-12 rounded-full bg-[rgb(var(--canvas))]" />
    </div>
  );
}
