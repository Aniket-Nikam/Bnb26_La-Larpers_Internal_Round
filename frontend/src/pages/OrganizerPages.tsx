import { motion } from 'framer-motion';
import { ShieldAlert, Users, Bot, Download, Play, Square } from 'lucide-react';
import { LineChart, Line, XAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { TicketCard, TicketDivider } from '../components/Ticket';
import { DEV_FIXTURES } from '../fixtures';

const mockMetrics = [
  { time: '0s', humans: 0, bots: 0 },
  { time: '5s', humans: 10, bots: 50 },
  { time: '10s', humans: 25, bots: 120 },
  { time: '15s', humans: 45, bots: 300 },
  { time: '20s', humans: 60, bots: 500 },
];

export function OrganizerDashboard() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-10 pt-10">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-bold tracking-tighter text-white">Organizer Dashboard</h1>
          <p className="text-white/50 mt-2 font-medium">Manage your cryptographic drops and analyze entry integrity.</p>
        </div>
        <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="bg-white text-black px-6 py-3 rounded-full font-bold text-sm uppercase tracking-widest hover:bg-gray-200">
          Create Drop
        </motion.button>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="bg-[#161616] p-8 rounded-3xl">
          <div className="text-white/40 text-[11px] font-bold uppercase tracking-[0.2em] mb-4">Total Drops</div>
          <div className="text-4xl font-bold tracking-tighter">1</div>
        </div>
        <div className="bg-[#161616] p-8 rounded-3xl">
          <div className="text-white/40 text-[11px] font-bold uppercase tracking-[0.2em] mb-4">Total Participants</div>
          <div className="text-4xl font-bold tracking-tighter">1,042</div>
        </div>
        <div className="bg-[#161616] p-8 rounded-3xl">
          <div className="text-white/40 text-[11px] font-bold uppercase tracking-[0.2em] mb-4">Sybil Rejections</div>
          <div className="text-4xl font-bold tracking-tighter text-white">8,930</div>
        </div>
      </div>

      <div className="bg-[#161616] rounded-[2rem] overflow-hidden">
        <table className="w-full text-left">
          <thead className="border-b border-white/5 bg-[#1C1C1E]">
            <tr>
              <th className="p-8 text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">Drop Name</th>
              <th className="p-8 text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">Status</th>
              <th className="p-8 text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">Capacity</th>
              <th className="p-8 text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="p-8 font-bold text-[18px] tracking-tight">{DEV_FIXTURES.drops[0].name}</td>
              <td className="p-8">
                <span className="inline-flex items-center gap-2 px-3 py-1 bg-white text-black rounded-full text-[10px] font-bold uppercase tracking-widest">
                  {DEV_FIXTURES.drops[0].status}
                </span>
              </td>
              <td className="p-8 font-mono text-white/60 text-[16px]">{DEV_FIXTURES.drops[0].capacity}</td>
              <td className="p-8">
                <button className="text-white/50 hover:text-white font-bold text-[12px] uppercase tracking-widest border border-white/20 px-4 py-2 rounded-full">Manage</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

export function AttackLab() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-10 pt-10">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-bold tracking-tighter text-white flex items-center gap-4">
            <ShieldAlert className="w-8 h-8" /> Attack Lab
          </h1>
          <p className="text-white/50 mt-2 font-medium max-w-xl">
            Simulate high-volume Sybil attacks against the PoW solver and bot-scoring module to verify ingress defense integrity.
          </p>
        </div>
        <div className="flex gap-4">
          <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="flex items-center gap-2 bg-black border border-white/20 text-white px-6 py-3 rounded-full font-bold text-sm uppercase tracking-widest hover:bg-white/10">
            <Square className="w-4 h-4" /> Stop
          </motion.button>
          <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="flex items-center gap-2 bg-white text-black px-6 py-3 rounded-full font-bold text-sm uppercase tracking-widest hover:bg-gray-200">
            <Play className="w-4 h-4" /> Run Simulation
          </motion.button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-[#161616] p-10 rounded-[2.5rem]">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-white/40 text-[11px] font-bold uppercase tracking-[0.2em]">Ingress Metrics (RPS)</h3>
            <div className="flex gap-4 text-[12px] font-bold uppercase tracking-widest">
              <span className="flex items-center gap-2"><div className="w-2 h-2 bg-white rounded-full"></div> Humans</span>
              <span className="flex items-center gap-2 text-white/40"><div className="w-2 h-2 bg-white/40 rounded-full"></div> Bots</span>
            </div>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockMetrics}>
                <XAxis dataKey="time" stroke="#ffffff40" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#000', border: '1px solid #ffffff20', borderRadius: '1rem', color: '#fff' }}
                  itemStyle={{ color: '#fff', fontSize: '14px', fontWeight: 'bold' }}
                />
                <Line type="monotone" dataKey="humans" stroke="#ffffff" strokeWidth={4} dot={false} />
                <Line type="monotone" dataKey="bots" stroke="#ffffff40" strokeWidth={4} dot={false} strokeDasharray="5 5" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <TicketCard className="flex flex-col">
          <div className="p-8 pb-6 flex-1">
            <h3 className="text-white/40 text-[11px] font-bold uppercase tracking-[0.2em] mb-6">Simulation Status</h3>
            <div className="text-5xl font-bold tracking-tighter mb-2">RUNNING</div>
            <div className="text-white/50 font-mono text-[13px]">Target: localhost:3000</div>
            
            <div className="mt-10 space-y-5">
              <div className="flex justify-between items-center border-b border-white/10 pb-4">
                <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest"><Users className="w-4 h-4" /> Humans</span>
                <span className="font-mono text-lg">60 / 60</span>
              </div>
              <div className="flex justify-between items-center border-b border-white/10 pb-4">
                <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-white/50"><Bot className="w-4 h-4" /> Bots</span>
                <span className="font-mono text-lg text-white/50">0 / 500</span>
              </div>
            </div>
          </div>
          <TicketDivider />
          <div className="p-8 pt-6">
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="flex items-center justify-center gap-2 w-full bg-black text-white py-4 rounded-full font-bold text-[12px] uppercase tracking-widest hover:bg-white/10">
              <Download className="w-4 h-4" /> Export Report
            </motion.button>
          </div>
        </TicketCard>
      </div>
    </motion.div>
  );
}
