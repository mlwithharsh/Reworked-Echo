import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { coreAPI, feedbackAPI, modelAPI, textAPI, userAPI } from '../api/client';
import toast from 'react-hot-toast';
const rawBackend = import.meta.env.VITE_BACKEND_URL || 'https://reworked-echo.onrender.com';
const BACKEND = rawBackend.endsWith('/') ? rawBackend.slice(0, -1) : rawBackend;


const AIContext = createContext();


// Cold start timeout — Render free tier can take up to 60s
const COLD_START_TIMEOUT = 15000;

export const AIProvider = ({ children }) => {
  const [status, setStatus] = useState('connecting');
  const [userId, setUserId] = useState(() => localStorage.getItem('helix_user_id') || 'guest-user');
  const [personality, setPersonality] = useState('helix');
  const [history, setHistory] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastResponse, setLastResponse] = useState(null);
  const [profile, setProfile] = useState(null);
  const [systemLabel, setSystemLabel] = useState('');
  const [isColdStart, setIsColdStart] = useState(false);
  const coldStartTimerRef = useRef(null);
  const hasConnectedOnce = useRef(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await coreAPI.getStatus();
      setStatus(res.data.status || 'online');
      setIsColdStart(false);
      hasConnectedOnce.current = true;
      if (coldStartTimerRef.current) {
        clearTimeout(coldStartTimerRef.current);
        coldStartTimerRef.current = null;
      }
    } catch (err) {
      if (!hasConnectedOnce.current) {
        setStatus('connecting');
      } else {
        setStatus('offline');
      }
    }
  }, []);

  // Warm up the backend on first mount — fires an early ping to wake Render
  useEffect(() => {
    const warmUp = async () => {
      // Start cold start detection timer
      coldStartTimerRef.current = setTimeout(() => {
        if (!hasConnectedOnce.current) {
          setIsColdStart(true);
        }
      }, COLD_START_TIMEOUT);

      // Fire 3 pings with delay to warm up Render backend
      for (let i = 0; i < 3; i++) {
        try {
          const res = await coreAPI.getStatus();
          if (res.data?.status) {
            setStatus(res.data.status);
            setIsColdStart(false);
            hasConnectedOnce.current = true;
            if (coldStartTimerRef.current) {
              clearTimeout(coldStartTimerRef.current);
              coldStartTimerRef.current = null;
            }
            break;
          }
        } catch {
          // Wait longer between retries during cold start
          await new Promise(r => setTimeout(r, 5000));
        }
      }
    };
    warmUp();

    return () => {
      if (coldStartTimerRef.current) {
        clearTimeout(coldStartTimerRef.current);
      }
    };
  }, []);

  const fetchProfile = useCallback(async () => {
    try {
      const res = await userAPI.getProfile(userId);
      setProfile(res.data);
    } catch (err) {
      console.warn('Failed to fetch profile', err);
    }
  }, [userId]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await userAPI.getHistory(userId);
      const items = res.data.items || [];
      setHistory(
        items.map((item) => ({
          interaction_id: item.id,
          input_text: item.input_text,
          response: item.response_text,
          model_version: item.model_version,
          metadata: item.metadata || {},
        }))
      );
    } catch (err) {
      console.warn('Failed to fetch history', err);
    }
  }, [userId]);

  useEffect(() => {
    // Sync userId from localStorage
    const handleStorageChange = () => {
      const id = localStorage.getItem('helix_user_id') || 'guest-user';
      setUserId(id);
    };
    window.addEventListener('storage', handleStorageChange);
    
    fetchStatus();
    if (userId !== 'guest-user') {
      fetchProfile();
      fetchHistory();
    }
    const interval = setInterval(fetchStatus, 30000);
    return () => {
      clearInterval(interval);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [fetchStatus, fetchHistory, fetchProfile, userId]);

  const processText = async (text, options = {}) => {
    setIsProcessing(true);
    const draftId = `pending-${Date.now()}`;
    const draft = {
      interaction_id: draftId,
      input_text: text,
      response: '',
      metadata: {},
      pending: true,
    };
    
    setHistory((prev) => [...prev, draft].slice(-50));

    try {
      const outboundHistory = history.flatMap((item) => {
        const rows = [];
        if (item.input_text || item.text) {
          rows.push({ role: 'user', content: item.input_text || item.text || '' });
        }
        if (item.response) {
          rows.push({ role: 'assistant', content: item.response });
        }
        return rows;
      });

      const response = await fetch(`${BACKEND}/api/v1/chat/stream`, {

        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          message: text,
          history: outboundHistory,
          personality,
          privacy_mode: options.privacy_mode || false,
          force_offline: options.force_offline || false
        }),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') break;
            
            try {
              const data = JSON.parse(dataStr);
              if (data.token) {
                fullResponse += data.token;
                // Live update history for streaming effect
                setHistory(prev => prev.map(item => 
                  item.interaction_id === draftId 
                    ? { ...item, response: fullResponse }
                    : item
                ));
              }
            } catch (e) { console.warn("JSON parse error in stream", e); }
          }
        }
      }

      // Mark as complete
      setHistory(prev => prev.map(item => 
        item.interaction_id === draftId 
          ? { ...item, pending: false }
          : item
      ));

      return { response: fullResponse };
    } catch (err) {
      console.error('Streaming connection failed', err);
      // Clean up failed draft
      setHistory((prev) => prev.filter((item) => item.interaction_id !== draftId));
      toast.error('Connection failed. Backend may be offline.');
      throw err;
    } finally {
      setIsProcessing(false);
    }
  };

  const submitFeedback = async (interactionId, vote, tags = []) => {
    try {
      const res = await feedbackAPI.submit({
        user_id: userId,
        interaction_id: interactionId,
        vote,
        tags,
      });
      setProfile(res.data.updated_profile);
      toast.success('Feedback received — adapting to your preferences');
    } catch (err) {
      toast.error('Failed to submit feedback');
    }
  };

  return (
    <AIContext.Provider value={{
      status,
      userId,
      personality,
      setPersonality,
      history,
      isProcessing,
      lastResponse,
      profile,
      systemLabel,
      isColdStart,
      processText,
      submitFeedback,
      refreshStatus: fetchStatus
    }}>
      {children}
    </AIContext.Provider>
  );
};

export const useAI = () => useContext(AIContext);
