import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { coreAPI, feedbackAPI, modelAPI, textAPI, userAPI } from '../api/client';
import toast from 'react-hot-toast';

const AIContext = createContext();

export const AIProvider = ({ children }) => {
  const [status, setStatus] = useState('offline');
  const [userId, setUserId] = useState(() => localStorage.getItem('helix_user_id') || 'guest-user');
  const [personality, setPersonality] = useState('helix');
  const [history, setHistory] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastResponse, setLastResponse] = useState(null);
  const [profile, setProfile] = useState(null);
  const [systemLabel, setSystemLabel] = useState('');

  const fetchStatus = useCallback(async () => {
    try {
      const res = await coreAPI.getStatus();
      setStatus(res.data.status || 'online');
    } catch (err) {
      setStatus('offline');
    }
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

  useEffect(() => {
    const clear = async () => {
      try {
        await userAPI.clearHistory(userId);
      } catch (err) {
        console.warn('Failed to clear backend history', err);
      }
      setHistory([]);
    };
    clear();
  }, [personality, userId]);

  const processText = async (text) => {
    setIsProcessing(true);
    const draft = {
      interaction_id: `pending-${Date.now()}`,
      input_text: text,
      response: '',
      metadata: {},
      pending: true,
    };
    setHistory((prev) => [...prev, draft].slice(-50));
    try {
      let finalPayload = null;
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

      await textAPI.stream(
        {
          user_id: userId,
          message: text,
          history: outboundHistory,
          personality,
        },
        (event) => {
          const eventType = event.type || (event.response ? 'done' : 'delta');
          
          if (eventType === 'delta') {
            setHistory((prev) =>
              prev.map((item) =>
                item.interaction_id === draft.interaction_id
                  ? { ...item, response: `${item.response}${event.content}`, pending: true }
                  : item
              )
            );
          }
          if (eventType === 'done') {
            finalPayload = {
              interaction_id: event.interaction_id || draft.interaction_id, 
              input_text: text,
              response: event.response,
              metadata: {
                ...(event.metadata || {}),
                backend_interaction_id: event.interaction_id
              },
              model_version: event.metadata?.model_version || '2.0.0',
              pending: false,
            };
            if (event.profile) setProfile(event.profile);
            
            setHistory((prev) => 
               prev.map((item) => item.interaction_id === draft.interaction_id ? finalPayload : item)
            );
            setLastResponse(finalPayload);
          }
        }
      );
      return finalPayload;
    } catch (err) {
      console.error('API connection failed', err);
      setHistory((prev) => prev.filter((item) => item.interaction_id !== draft.interaction_id));
      toast.error('Connection failed. Is the backend running on port 8000?');
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
      processText,
      submitFeedback,
      refreshStatus: fetchStatus
    }}>
      {children}
    </AIContext.Provider>
  );
};

export const useAI = () => useContext(AIContext);
