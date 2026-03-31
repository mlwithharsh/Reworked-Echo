import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAI } from '../context/AIContext';
import { 
  Mic, 
  MicOff, 
  Play, 
  Pause, 
  Activity, 
  Smile, 
  MessageSquare, 
  Target,
  Loader2,
  CheckCircle2
} from 'lucide-react';

const VoiceMode = () => {
  const { 
    isProcessing, 
    processVoice, 
    recordingDuration, 
    lastResponse,
    status 
  } = useAI();
  
  const [isRecording, setIsRecording] = useState(false);
  const [timeLeft, setTimeLeft] = useState(recordingDuration);
  const [audioURL, setAudioURL] = useState(null);
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    setTimeLeft(recordingDuration);
  }, [recordingDuration]);

  const startRecording = async () => {
    if (status === 'offline') return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream);
      chunks.current = [];

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };

      mediaRecorder.current.onstop = () => {
        const audioBlob = new Blob(chunks.current, { type: 'audio/wav' });
        processVoice(audioBlob);
        setAudioURL(URL.createObjectURL(audioBlob));
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.current.start();
      setIsRecording(true);
      setTimeLeft(recordingDuration);

      timerRef.current = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            stopRecording();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

    } catch (err) {
      console.error('Error accessing microphone:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && isRecording) {
      mediaRecorder.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  return (
    <div className="flex-1 glass-panel p-8 flex flex-col items-center space-y-12 overflow-y-auto scrollbar-hide">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold tracking-tighter text-neon-purple uppercase italic drop-shadow-[0_0_10px_rgba(139,92,246,0.5)]">Neural Voice Link</h2>
        <p className="text-xs font-mono text-white/40 tracking-widest uppercase">Direct bio-acoustic interface active</p>
      </div>

      {/* 3D Recording Button Area */}
      <div className="relative flex items-center justify-center py-8">
        {/* Pulsing Rings */}
        <AnimatePresence>
          {isRecording && (
            <>
              {[1, 2, 3].map((ring) => (
                <motion.div
                  key={ring}
                  initial={{ scale: 0.8, opacity: 0.6 }}
                  animate={{ scale: 2, opacity: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: ring * 0.4 }}
                  className="absolute w-32 h-32 rounded-full border border-neon-purple/50"
                />
              ))}
            </>
          )}
        </AnimatePresence>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing || status === 'offline'}
          className={`relative z-10 w-48 h-48 rounded-full flex flex-col items-center justify-center transition-all duration-500 shadow-2xl overflow-hidden group ${
            isRecording 
              ? 'bg-red-500/20 border-2 border-red-500 shadow-[0_0_50px_rgba(239,68,68,0.4)]' 
              : 'bg-neon-purple/20 border-2 border-neon-purple/50 shadow-[0_0_30px_rgba(139,92,246,0.3)] hover:shadow-neon-purple'
          } ${status === 'offline' ? 'opacity-50 grayscale cursor-not-allowed' : ''}`}
        >
          {isRecording ? (
            <MicOff className="w-16 h-16 text-red-500 mb-2 drop-shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
          ) : (
            <Mic className="w-16 h-16 text-white mb-2 drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
          )}
          <span className="text-xs font-bold tracking-widest uppercase font-mono">
            {isRecording ? `00:${timeLeft.toString().padStart(2, '0')}` : 'Initiate Link'}
          </span>
          
          {/* Animated Background Mesh */}
          <div className="absolute inset-0 bg-gradient-to-t from-white/5 to-transparent opacity-20" />
        </motion.button>
      </div>

      {/* Waveform Animation during processing */}
      <AnimatePresence>
        {isProcessing && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-center space-x-2 h-12"
          >
            {[...Array(12)].map((_, i) => (
              <motion.div
                key={i}
                animate={{ height: [10, 40, 10] }}
                transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.05 }}
                className="w-1.5 bg-neon-purple rounded-full shadow-neon-purple"
              />
            ))}
            <span className="ml-4 text-xs font-mono text-white/60 uppercase tracking-widest flex items-center">
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Processing Signal...
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* AI Response Card */}
      <AnimatePresence>
        {lastResponse && !isProcessing && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="w-full space-y-6"
          >
            {/* Metric Cards */}
            <div className="grid grid-cols-3 gap-4">
              <MetricCard 
                icon={Smile} 
                label="Emotion" 
                value={lastResponse.emotion || 'NEUTRAL'} 
                color="#8B5CF6" 
              />
              <MetricCard 
                icon={Target} 
                label="Intent" 
                value={lastResponse.intent || 'QUERY'} 
                color="#3B82F6" 
              />
              <MetricCard 
                icon={Activity} 
                label="Sentiment" 
                value={lastResponse.sentiment || '0.85'} 
                color="#22D3EE" 
              />
            </div>

            {/* Response Display */}
            <div className="glass-panel p-6 bg-white/5 border-white/10 relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-1 h-full bg-neon-purple group-hover:w-2 transition-all duration-300 shadow-neon-purple" />
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <MessageSquare className="w-4 h-4 text-neon-purple" />
                  <span className="text-xs font-bold uppercase tracking-widest text-white/40">Response Stream</span>
                </div>
                <div className="flex items-center space-x-1">
                  <CheckCircle2 className="w-3 h-3 text-green-400" />
                  <span className="text-[10px] font-mono text-green-400 uppercase tracking-tighter">Verified_Response</span>
                </div>
              </div>
              <p className="text-white/90 leading-relaxed font-medium">
                {lastResponse.response || lastResponse.text}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const MetricCard = ({ icon: Icon, label, value, color }) => (
  <div className="glass-panel p-4 bg-white/5 border-white/5 flex flex-col items-center justify-center space-y-2 group hover:bg-white/10 transition-all duration-300">
    <Icon className="w-5 h-5 opacity-60 group-hover:opacity-100 transition-all duration-300" style={{ color }} />
    <span className="text-[10px] uppercase font-bold tracking-widest text-white/30">{label}</span>
    <span className="text-xs font-mono font-bold uppercase" style={{ color }}>{value}</span>
  </div>
);

export default VoiceMode;
