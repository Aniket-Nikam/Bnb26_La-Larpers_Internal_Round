import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

export function TicketCard({ children, onClick, className = '' }: { children: ReactNode, onClick?: () => void, className?: string }) {
  return (
    <motion.div 
      whileHover={onClick ? { scale: 0.99 } : {}}
      whileTap={onClick ? { scale: 0.97 } : {}}
      onClick={onClick}
      className={`relative bg-[#161616] rounded-[2.5rem] overflow-hidden ${className}`}
    >
      {children}
    </motion.div>
  );
}

export function TicketDivider() {
  return (
    <div className="relative w-full h-10 flex items-center my-2">
      {/* Dashed line connecting the cutouts */}
      <div className="absolute w-full border-t-2 border-dashed border-white/[0.15] z-0"></div>
      
      {/* True seamless punched holes matching the pure black canvas */}
      <div className="absolute -left-6 w-12 h-12 bg-black rounded-full z-10" />
      <div className="absolute -right-6 w-12 h-12 bg-black rounded-full z-10" />
    </div>
  );
}
