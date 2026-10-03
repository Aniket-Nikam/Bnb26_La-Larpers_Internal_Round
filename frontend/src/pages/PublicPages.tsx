import { motion } from 'framer-motion';
import { ShieldCheck, Ticket, ChevronRight, Lock } from 'lucide-react';
import { Link } from 'react-router-dom';
import { TicketCard, TicketDivider } from '../components/Ticket';
import { DEV_FIXTURES } from '../fixtures';

export function LandingPage() {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="space-y-16 pt-16">
      <div className="space-y-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#161616] text-white rounded-full text-[12px] font-bold uppercase tracking-widest">
          <ShieldCheck className="w-4 h-4" />
          <span>Provably Fair</span>
        </div>
        <h1 className="text-6xl md:text-[5.5rem] font-bold tracking-tighter text-white leading-[0.95]">
          Enter once. <br />
          <span className="text-white/30">Verify securely.</span>
        </h1>
        <p className="text-[18px] text-white/50 max-w-xl leading-relaxed font-medium">
          Verify your invitation, enter the drop once, and rely on cryptographic commitments to ensure a completely fair outcome.
        </p>
      </div>
      
      <div className="mt-20">
        <Link to={`/drops/${DEV_FIXTURES.drops[0].id}`}>
          <TicketCard className="cursor-pointer group hover:bg-[#1C1C1E] transition-colors">
            <div className="p-10 pb-6">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <div className="text-white/40 text-[11px] font-bold uppercase tracking-[0.2em] mb-3">Featured Drop</div>
                  <div className="text-3xl font-bold text-white tracking-tighter">{DEV_FIXTURES.drops[0].name}</div>
                </div>
                <div className="w-14 h-14 rounded-full bg-white text-black flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
                  <Ticket className="w-6 h-6" />
                </div>
              </div>
            </div>
            
            <TicketDivider />
            
            <div className="p-10 pt-6">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <span className="w-2.5 h-2.5 rounded-full bg-white animate-pulse"></span>
                  <span className="text-[13px] font-bold text-white tracking-widest uppercase">Accepting Entries</span>
                </div>
                <div className="w-12 h-12 rounded-full border border-white/20 flex items-center justify-center text-white group-hover:bg-white group-hover:text-black transition-colors">
                  <ChevronRight className="w-5 h-5" />
                </div>
              </div>
            </div>
          </TicketCard>
        </Link>
      </div>
    </motion.div>
  );
}

export function DropDetail() {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4 }} className="max-w-2xl mx-auto pt-10">
      <TicketCard className="cursor-default">
        <div className="p-12 pb-8">
          <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center text-black mb-10">
            <Ticket className="w-8 h-8" strokeWidth={2.5} />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tighter mb-4 text-white leading-tight">FairDrop <br/>Inaugural Event</h1>
          <div className="grid grid-cols-2 gap-8 mt-10">
            <div>
              <div className="text-white/40 text-[11px] font-bold uppercase tracking-[0.2em] mb-2">Status</div>
              <div className="text-[16px] font-semibold text-white flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-white" /> Open
              </div>
            </div>
            <div>
              <div className="text-white/40 text-[11px] font-bold uppercase tracking-[0.2em] mb-2">Capacity</div>
              <div className="text-[16px] font-semibold text-white">100 Seats</div>
            </div>
          </div>
        </div>
        
        <TicketDivider />
        
        <div className="p-12 pt-8">
          <div className="mb-10">
            <h3 className="font-bold mb-3 text-[12px] uppercase tracking-widest text-white/40">Eligibility Rules</h3>
            <p className="text-[16px] text-white/80 leading-relaxed font-medium">
              You must hold a valid invitation credential to enter. Each person is allowed exactly one entry.
            </p>
          </div>
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="w-full bg-white text-black py-5 rounded-full font-bold text-[16px] uppercase tracking-widest hover:bg-gray-200">
            Enter Drop
          </motion.button>
        </div>
      </TicketCard>
    </motion.div>
  );
}

export function SignInPage() {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-md mx-auto pt-20">
      <TicketCard className="cursor-default">
        <div className="p-12 pb-8 text-center">
          <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center text-black mx-auto mb-8">
            <Lock className="w-8 h-8" strokeWidth={2.5} />
          </div>
          <h1 className="text-3xl font-bold mb-3 tracking-tighter text-white">Sign In</h1>
          <p className="text-[15px] text-white/50 font-medium">Enter your secure credentials</p>
        </div>
        
        <TicketDivider />
        
        <div className="p-12 pt-8">
          <form className="space-y-8">
            <div>
              <label className="block text-[11px] font-bold text-white/50 mb-3 uppercase tracking-[0.2em]">Invitation Credential</label>
              <input type="text" className="w-full bg-black border border-transparent focus:border-white focus:ring-1 focus:ring-white rounded-2xl px-5 py-4 text-[16px] text-white placeholder-white/20 outline-none font-mono transition-all" placeholder="0x..." />
            </div>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="w-full bg-white text-black py-4 rounded-full font-bold text-[14px] uppercase tracking-widest hover:bg-gray-200">
              Verify & Sign In
            </motion.button>
          </form>
        </div>
      </TicketCard>
    </motion.div>
  );
}
