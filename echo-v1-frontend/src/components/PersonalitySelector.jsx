import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAI } from '../context/AIContext';
import { Sparkles, User, ChevronDown } from 'lucide-react';

const personalities = [
  { 
    id: 'echo', 
    name: 'Echo', 
    desc: 'Empathetic & Balanced', 
    icon: Sparkles,
    color: '#8b5cf6'
  },
  { 
    id: 'suzi', 
    name: 'Suzi', 
    desc: 'Bold & Playful', 
    icon: User,
    color: '#ec4899'
  }
];

const PersonalitySelector = () => {
  const { personality, setPersonality } = useAI();
  const [isOpen, setIsOpen] = React.useState(false);
  
  const activePersonality = personalities.find(p => p.id === personality.toLowerCase()) || personalities[0];

  return (
    <div className="relative">
      {/* Trigger */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-3 px-4 py-2 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all duration-300"
      >
        <div 
          className="w-6 h-6 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${activePersonality.color}20` }}
        >
          <activePersonality.icon className="w-3.5 h-3.5" style={{ color: activePersonality.color }} />
        </div>
        <div className="text-left hidden xs:block">
          <p className="text-[10px] font-bold text-text-muted uppercase tracking-widest leading-none mb-1">Active Neural Link</p>
          <p className="text-xs font-black text-white uppercase tracking-tighter">{activePersonality.name}</p>
        </div>
        <ChevronDown className={`w-4 h-4 text-text-muted transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop for mobile */}
            <div 
              className="fixed inset-0 z-40 md:hidden" 
              onClick={() => setIsOpen(false)} 
            />
            
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="absolute right-0 mt-3 w-64 z-50 glass-card p-2 border-white/10 overflow-hidden shadow-2xl"
            >
              <div className="px-3 py-2 mb-2">
                <p className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em]">Select Personality</p>
              </div>
              
              <div className="space-y-1">
                {personalities.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setPersonality(p.id);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center space-x-4 p-3 rounded-xl transition-all duration-300 group ${
                      personality.toLowerCase() === p.id 
                        ? 'bg-white/10 border-white/10' 
                        : 'hover:bg-white/5 border-transparent'
                    } border`}
                  >
                    <div 
                      className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform duration-300"
                      style={{ backgroundColor: `${p.color}20` }}
                    >
                      <p.icon className="w-5 h-5" style={{ color: p.color }} />
                    </div>
                    <div className="text-left">
                      <p className="text-sm font-bold text-white leading-none mb-1">{p.name}</p>
                      <p className="text-[10px] text-text-muted font-medium">{p.desc}</p>
                    </div>
                    {personality.toLowerCase() === p.id && (
                      <div className="ml-auto w-1.5 h-1.5 rounded-full bg-solace-purple shadow-glow-purple" />
                    )}
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PersonalitySelector;
