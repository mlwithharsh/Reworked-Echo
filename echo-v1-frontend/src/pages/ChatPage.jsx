import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useAI } from '../context/AIContext';
import PersonalitySelector from '../components/PersonalitySelector';
import { 
  Send, 
  ArrowLeft, 
  Sparkles, 
  Loader2, 
  User, 
  Heart,
  Smile,
  Target,
  Activity
} from 'lucide-react';

const ChatPage = () => {
  const [inputText, setInputText] = useState('');
  const { isProcessing, processText, lastResponse, history } = useAI();
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [history, isProcessing]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || isProcessing) return;
    
    const text = inputText;
    setInputText('');
    try {
      await processText(text);
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
    <div className="h-screen flex flex-col bg-background overflow-hidden pt-20">
      {/* Chat Header */}
      <header className="px-6 py-4 border-b border-white/5 flex items-center justify-between bg-background/50 backdrop-blur-md relative z-20">
        <div className="flex items-center space-x-4">
          <Link to="/" className="p-2 rounded-full hover:bg-white/5 text-text-secondary hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-widest">Textual Synapse</h2>
            <div className="flex items-center space-x-2">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <span className="text-[10px] text-text-muted font-bold uppercase tracking-tighter">Emotion-aware AI Active</span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2 px-4 py-1.5 rounded-full bg-solace-purple/10 border border-solace-purple/20">
            <Sparkles className="w-3 h-3 text-solace-purple-glow" />
            <span className="text-[10px] font-bold text-solace-purple-glow uppercase tracking-widest">ECHO_Link_Stable</span>
          </div>
          <PersonalitySelector />
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-8 space-y-8 scrollbar-hide">
        <div className="max-w-4xl mx-auto space-y-8">
          {history.length === 0 && !isProcessing && (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-6">
              <div className="w-20 h-20 rounded-3xl bg-white/5 flex items-center justify-center animate-pulse">
                <Heart className="w-10 h-10 text-solace-purple/40" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-white">How are you feeling today?</h3>
                <p className="text-text-secondary text-sm max-w-xs mx-auto">
                  I'm here to listen. Share your thoughts, feelings, or just say hello.
                </p>
              </div>
            </div>
          )}

          {history.map((msg, idx) => (
            <div key={idx} className="space-y-4">
              {/* User Message */}
              <motion.div 
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex justify-end"
              >
                <div className="max-w-[80%] px-6 py-4 rounded-3xl rounded-tr-none bg-white/5 border border-white/10 text-white shadow-sm">
                  <p className="text-sm leading-relaxed">{msg.input_text || msg.text}</p>
                </div>
              </motion.div>

              {/* AI Message */}
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex justify-start space-y-4 flex-col"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-solace-purple to-solace-blue flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest">ECHO AI</span>
                </div>
                
                <div className="max-w-[80%] px-6 py-4 rounded-3xl rounded-tl-none bg-background-soft border border-solace-purple/20 text-text-primary shadow-glow-purple/10">
                  <p className="text-sm leading-relaxed">{msg.response}</p>
                </div>

                {/* Metrics for each message */}
                <div className="flex space-x-3 overflow-x-auto pb-2 scrollbar-hide">
                  <MetricChip icon={Smile} label="Emotion" value={msg.emotion || 'CALM'} color="#8b5cf6" />
                  <MetricChip icon={Target} label="Intent" value={msg.intent || 'SUPPORT'} color="#3b82f6" />
                  <MetricChip icon={Activity} label="Sentiment" value={msg.sentiment || 'POSITIVE'} color="#06b6d4" />
                </div>
              </motion.div>
            </div>
          ))}

          {isProcessing && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-start space-x-3"
            >
              <div className="w-8 h-8 rounded-xl bg-white/5 flex items-center justify-center">
                <Loader2 className="w-4 h-4 text-solace-purple animate-spin" />
              </div>
              <div className="px-6 py-4 rounded-3xl rounded-tl-none bg-white/5 border border-white/5">
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 bg-solace-purple rounded-full animate-bounce" />
                  <div className="w-1.5 h-1.5 bg-solace-purple rounded-full animate-bounce [animation-delay:0.2s]" />
                  <div className="w-1.5 h-1.5 bg-solace-purple rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="p-6 bg-background relative z-20">
        <div className="max-w-4xl mx-auto relative">
          <form onSubmit={handleSubmit} className="relative group">
            <textarea
              ref={textareaRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Share your thoughts..."
              className="w-full bg-background-soft border border-white/10 rounded-[2rem] px-8 py-6 pr-20 text-white placeholder-text-muted resize-none outline-none focus:border-solace-purple/30 focus:shadow-glow-purple transition-all duration-500 min-h-[80px] max-h-[200px]"
              rows="1"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isProcessing}
              className={`absolute right-4 bottom-4 p-4 rounded-2xl transition-all duration-300 ${
                !inputText.trim() || isProcessing
                  ? 'bg-white/5 text-text-muted cursor-not-allowed'
                  : 'bg-gradient-to-r from-solace-purple to-solace-blue text-white shadow-glow-purple scale-100 hover:scale-105 active:scale-95'
              }`}
            >
              {isProcessing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </form>
          <p className="mt-3 text-[10px] text-center text-text-muted uppercase tracking-widest">
            Your conversations are confidential and encrypted.
          </p>
        </div>
      </div>
    </div>
  );
};

const MetricChip = ({ icon: Icon, label, value, color }) => (
  <div 
    className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 shrink-0"
    style={{ borderColor: `${color}20` }}
  >
    <Icon className="w-3 h-3" style={{ color }} />
    <span className="text-[9px] font-bold text-text-muted uppercase tracking-tighter">{label}:</span>
    <span className="text-[9px] font-black uppercase tracking-widest" style={{ color }}>{value}</span>
  </div>
);

export default ChatPage;
