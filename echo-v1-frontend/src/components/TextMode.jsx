import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAI } from '../context/AIContext';
import { 
  Send, 
  MessageSquare, 
  Smile, 
  Target, 
  Activity, 
  Loader2, 
  Sparkles,
  Command,
  Zap
} from 'lucide-react';

const TextMode = () => {
  const [inputText, setInputText] = useState('');
  const { isProcessing, processText, lastResponse, status } = useAI();
  const textareaRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || isProcessing) return;
    
    try {
      await processText(inputText);
      setInputText('');
    } catch (err) {
      console.error('Failed to send text', err);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex-1 glass-panel p-8 flex flex-col space-y-8 h-full overflow-hidden">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-2xl font-bold tracking-tight text-slate-800 italic uppercase">Textual Synapse</h2>
          <p className="text-[10px] font-bold text-slate-400 tracking-[0.2em] uppercase">Empathetic Communication Link</p>
        </div>
        <div className="flex items-center space-x-2 bg-white/60 px-4 py-2 rounded-2xl border border-white shadow-sm">
          <Zap className="w-3.5 h-3.5 text-empathy-blue" />
          <span className="text-[10px] font-bold text-slate-500 tracking-wider">SYNC_ACTIVE</span>
        </div>
      </div>

      {/* Response Area */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-4 scrollbar-hide">
        <AnimatePresence mode="wait">
          {lastResponse && !isProcessing ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98 }}
              className="space-y-6"
            >
              {/* Metric Chips - Horizontal */}
              <div className="flex space-x-4 overflow-x-auto pb-2 scrollbar-hide">
                <MetricChip icon={Smile} label="Emotion" value={lastResponse.emotion || 'SOFT'} color="#c084fc" />
                <MetricChip icon={Target} label="Intent" value={lastResponse.intent || 'SUPPORT'} color="#60a5fa" />
                <MetricChip icon={Activity} label="Sentiment" value={lastResponse.sentiment || '0.92'} color="#2dd4bf" />
              </div>

              {/* AI Message Bubble */}
              <div className="relative group">
                <div className="glass-panel p-6 relative border-white bg-white shadow-sm overflow-hidden rounded-2xl rounded-tl-none">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-empathy-purple to-empathy-blue flex items-center justify-center shadow-md">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-800">ECHO_V1</span>
                      <span className="text-[8px] font-bold text-slate-400 uppercase tracking-tighter">EMPATHY_CORE_NODE</span>
                    </div>
                  </div>
                  <p className="text-slate-700 leading-relaxed font-medium">
                    {lastResponse.response || lastResponse.text}
                  </p>
                </div>
              </div>
            </motion.div>
          ) : isProcessing ? (
            <div className="flex flex-col items-center justify-center h-full space-y-4">
              <div className="relative">
                <div className="w-12 h-12 rounded-full border-4 border-empathy-purple/20 border-t-empathy-purple animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-2 h-2 bg-empathy-purple rounded-full animate-ping" />
                </div>
              </div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-[0.2em] animate-pulse">Deepening understanding...</span>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full space-y-4 opacity-40">
              <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-inner">
                <MessageSquare className="w-8 h-8 text-slate-300" />
              </div>
              <div className="text-center">
                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-[0.2em]">Ready to listen</p>
                <p className="text-[8px] uppercase tracking-[0.1em] mt-1 italic text-slate-300">Awaiting your thoughts...</p>
              </div>
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="relative mt-auto pt-4 group">
        <div className="relative glass-panel bg-white border-white rounded-3xl overflow-hidden shadow-lg hover:shadow-xl transition-shadow duration-500">
          <textarea
            ref={textareaRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Share what's on your mind..."
            disabled={isProcessing}
            className="w-full bg-transparent p-6 text-slate-700 placeholder-slate-300 resize-none outline-none min-h-[140px] font-medium leading-relaxed"
          />
          <div className="flex items-center justify-between px-6 pb-6">
            <div className="flex items-center space-x-3 text-slate-300 text-[10px] font-bold tracking-tight">
              <div className="flex items-center space-x-1">
                <Command className="w-3 h-3" />
                <span>+</span>
                <span className="px-1.5 py-0.5 bg-slate-50 border border-slate-100 rounded text-slate-400">ENTER</span>
                <span className="ml-1">to send</span>
              </div>
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              disabled={!inputText.trim() || isProcessing}
              className={`btn-empathy flex items-center space-x-2 text-xs uppercase tracking-widest ${
                !inputText.trim() || isProcessing
                  ? 'opacity-40 grayscale cursor-not-allowed shadow-none'
                  : ''
              }`}
            >
              {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span>Transmit</span>
            </motion.button>
          </div>
        </div>
      </form>
    </div>
  );
};

const MetricChip = ({ icon: Icon, label, value, color }) => (
  <div className="flex-shrink-0 flex items-center space-x-3 px-4 py-2 glass-panel bg-white/5 border-white/5 hover:bg-white/10 transition-all duration-300 cursor-default">
    <Icon className="w-4 h-4" style={{ color }} />
    <div className="flex flex-col">
      <span className="text-[8px] font-bold uppercase tracking-widest text-white/30 leading-none mb-1">{label}</span>
      <span className="text-[10px] font-mono font-bold uppercase leading-none" style={{ color }}>{value}</span>
    </div>
  </div>
);

export default TextMode;
