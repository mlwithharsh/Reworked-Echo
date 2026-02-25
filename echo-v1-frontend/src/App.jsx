import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Toaster } from 'react-hot-toast';
import Sidebar from './components/Sidebar';
import TextMode from './components/TextMode';
import { AIProvider } from './context/AIContext';
import { 
  Terminal, 
  Cpu, 
  Layers, 
  Box, 
  Settings, 
  Bell,
  Maximize2,
  ChevronRight,
  ShieldAlert
} from 'lucide-react';

const App = () => {
  return (
    <AIProvider>
      <div className="relative w-screen h-screen bg-background overflow-hidden font-sans selection:bg-empathy-purple-light selection:text-purple-900">
        {/* Soft Empathetic Background */}
        <div className="absolute inset-0 bg-gradient-empathy z-0" />
        
        {/* Animated Soft Floating Orbs */}
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-empathy-purple/10 rounded-full blur-[120px] animate-float" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-empathy-blue/10 rounded-full blur-[120px] animate-float" style={{ animationDelay: '-4s' }} />

        {/* Top Navigation Bar */}
        <header className="absolute top-0 left-0 right-0 h-16 flex items-center justify-between px-8 z-50 glass-panel border-t-0 border-x-0 rounded-none bg-white/40 backdrop-blur-md">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-3 group cursor-default">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-empathy-purple to-empathy-blue flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-500 relative overflow-hidden">
                <Terminal className="w-5 h-5 text-white relative z-10" />
                <div className="absolute inset-0 bg-white/10 animate-pulse" />
              </div>
              <div className="flex flex-col">
                <h1 className="text-xl font-bold tracking-tight text-slate-800 uppercase">
                  ECHO <span className="text-empathy-purple">V1</span>
                </h1>
                <div className="flex items-center space-x-1">
                  <span className="text-[8px] font-medium text-slate-400 uppercase tracking-widest">Empathetic Intelligence</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-white/50 px-4 py-2 rounded-2xl border border-white/50 shadow-sm">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-[10px] font-semibold text-slate-500 tracking-widest uppercase">Core_Secure</span>
            </div>
            <NavIconButton icon={Bell} />
            <NavIconButton icon={Settings} />
            <div className="w-10 h-10 rounded-full border-2 border-white p-0.5 shadow-md overflow-hidden cursor-pointer hover:scale-105 transition-transform duration-300">
              <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Harsh" alt="Avatar" className="w-full h-full rounded-full bg-slate-100" />
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="absolute inset-0 pt-24 pb-8 px-8 flex space-x-8 z-10 overflow-hidden">
          <Sidebar />
          
          <div className="flex-1 relative h-full flex flex-col overflow-hidden">
            {/* Context Info Header */}
            <div className="flex items-center justify-between mb-4 px-4">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  <Box className="w-3 h-3" />
                  <span>Interface</span>
                  <ChevronRight className="w-3 h-3" />
                  <span className="text-empathy-purple font-bold">Textual_Synapse</span>
                </div>
              </div>
              <div className="flex items-center space-x-6">
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-medium text-slate-300 uppercase tracking-widest">Access:</span>
                  <span className="text-[10px] font-bold text-empathy-blue uppercase tracking-widest">Standard_User</span>
                </div>
                <Maximize2 className="w-4 h-4 text-slate-300 hover:text-slate-500 cursor-pointer transition-colors" />
              </div>
            </div>

            {/* Viewport - Only TextMode */}
            <div className="flex-1 flex gap-8 h-full min-h-0">
              <TextMode />
            </div>
          </div>
        </main>

        {/* Global Toaster */}
        <Toaster 
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'rgba(15, 23, 42, 0.9)',
              color: '#fff',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(10px)',
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontWeight: 'bold',
            },
            success: {
              iconTheme: {
                primary: '#8B5CF6',
                secondary: '#fff',
              },
            },
          }}
        />

        {/* Subtle Decorative Elements */}
        <div className="fixed bottom-4 left-4 flex items-center space-x-2 pointer-events-none opacity-20">
          <ShieldAlert className="w-4 h-4 text-red-500" />
          <span className="text-[8px] font-mono text-white tracking-[0.5em] uppercase">Security_Protocol_v4.2.1_Active</span>
        </div>
      </div>
    </AIProvider>
  );
};

const TabButton = ({ active, onClick, label, icon: Icon }) => (
  <button
    onClick={onClick}
    className={`flex items-center space-x-2 px-6 py-2 rounded-xl transition-all duration-500 relative group overflow-hidden ${
      active ? 'text-white' : 'text-white/40 hover:text-white/60'
    }`}
  >
    {active && (
      <motion.div 
        layoutId="activeTab"
        className="absolute inset-0 bg-white/10 border border-white/20 rounded-xl"
        transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
      />
    )}
    <Icon className={`w-4 h-4 relative z-10 ${active ? 'text-neon-purple animate-pulse' : 'text-white/40'}`} />
    <span className="text-xs font-bold uppercase tracking-widest relative z-10">{label}</span>
    {!active && <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-neon-purple transition-all duration-300 group-hover:w-full opacity-50" />}
  </button>
);

const NavIconButton = ({ icon: Icon }) => (
  <button className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-300 text-white/60 hover:text-white group relative">
    <Icon className="w-5 h-5 group-hover:scale-110 transition-transform duration-300" />
    <div className="absolute top-2 right-2 w-1.5 h-1.5 bg-neon-purple rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
  </button>
);

export default App;
