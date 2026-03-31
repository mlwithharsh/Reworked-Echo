import React from 'react';
import { motion } from 'framer-motion';
import { useAI } from '../context/AIContext';
import { 
  Activity, 
  User, 
  Clock, 
  Trash2, 
  ShieldCheck, 
  Brain, 
  History,
  AlertCircle
} from 'lucide-react';

const Sidebar = () => {
  const { 
    status, 
    personality, 
    setPersonality, 
    clearMemory,
    history
  } = useAI();

  const personalities = [
    { name: 'Echo', icon: Brain, color: '#c084fc' },
    { name: 'Suzi', icon: User, color: '#f472b6' },
    { name: 'Legal Advisor', icon: ShieldCheck, color: '#60a5fa' },
    { name: 'Philosopher Mentor', icon: Activity, color: '#2dd4bf' },
  ];

  return (
    <motion.div 
      initial={{ x: -300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-80 h-full glass-panel flex flex-col p-6 space-y-8 z-10"
    >
      {/* System Status */}
      <div className="space-y-4">
        <h3 className="text-[10px] font-bold tracking-[0.2em] text-slate-400 uppercase">System Status</h3>
        <div className="flex items-center space-x-3 bg-white/50 p-4 rounded-2xl border border-white shadow-sm">
          <div className={`w-2.5 h-2.5 rounded-full animate-pulse ${status === 'online' ? 'bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]' : 'bg-red-400'}`} />
          <span className="font-bold text-xs text-slate-600 tracking-tight">
            {status === 'online' ? 'ECHO_READY' : 'ECHO_STANDBY'}
          </span>
        </div>
      </div>

      {/* Personality Selector */}
      <div className="space-y-4">
        <h3 className="text-[10px] font-bold tracking-[0.2em] text-slate-400 uppercase">Personality Matrix</h3>
        <div className="grid grid-cols-1 gap-2">
          {personalities.map((p) => {
            const Icon = p.icon;
            const isSelected = personality === p.name;
            return (
              <motion.button
                key={p.name}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setPersonality(p.name)}
                className={`flex items-center space-x-3 p-3 rounded-2xl transition-all duration-300 ${isSelected ? 'bg-white shadow-sm border-white' : 'hover:bg-white/40 border-transparent'}`}
                style={{ borderLeft: isSelected ? `4px solid ${p.color}` : '4px solid transparent' }}
              >
                <Icon className={`w-4 h-4 ${isSelected ? '' : 'text-slate-400'}`} style={{ color: isSelected ? p.color : '' }} />
                <span className={`text-xs font-semibold ${isSelected ? 'text-slate-800' : 'text-slate-500'}`}>{p.name}</span>
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* History Preview */}
      <div className="flex-1 space-y-4 overflow-hidden flex flex-col">
        <div className="flex items-center space-x-2">
          <History className="w-4 h-4 text-slate-400" />
          <h3 className="text-[10px] font-bold tracking-[0.2em] text-slate-400 uppercase">Recent Flows</h3>
        </div>
        <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-hide">
          {history.slice(0, 3).map((item, i) => (
            <div key={i} className="p-3 bg-white/40 rounded-2xl border border-white/60 space-y-1">
              <p className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">{item.timestamp || 'Synapse_Node'}</p>
              <p className="text-xs text-slate-600 line-clamp-2 italic leading-relaxed">"{item.input_text || item.text}"</p>
            </div>
          ))}
          {history.length === 0 && (
            <div className="flex flex-col items-center justify-center h-20 text-slate-300">
              <AlertCircle className="w-5 h-5 mb-2 opacity-50" />
              <span className="text-[9px] uppercase tracking-[0.2em] font-bold">No active synapses</span>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <motion.button
        whileHover={{ scale: 1.02, backgroundColor: 'rgba(251, 113, 133, 0.1)' }}
        whileTap={{ scale: 0.98 }}
        onClick={clearMemory}
        className="w-full flex items-center justify-center space-x-2 p-4 bg-white/50 border border-red-100 rounded-2xl text-red-400 text-[10px] font-bold tracking-[0.2em] uppercase transition-all duration-300 hover:text-red-500 hover:shadow-sm"
      >
        <Trash2 className="w-4 h-4" />
        <span>Purge Nodes</span>
      </motion.button>
    </motion.div>
  );
};

export default Sidebar;
