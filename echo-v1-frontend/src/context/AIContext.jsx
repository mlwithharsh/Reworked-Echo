import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { coreAPI, feedbackAPI, modelAPI, textAPI, userAPI } from '../api/client';
import toast from 'react-hot-toast';

const AIContext = createContext();

export const AIProvider = ({ children }) => {
  const [status, setStatus] = useState('offline');
  const [userId] = useState('demo-user');
  const [history, setHistory] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastResponse, setLastResponse] = useState(null);
  const [profile, setProfile] = useState(null);
  const [modelVersions, setModelVersions] = useState([]);

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

  const fetchModelVersions = useCallback(async () => {
    try {
      const res = await modelAPI.listVersions();
      setModelVersions(res.data.items || []);
    } catch (err) {
      console.warn('Failed to fetch model versions', err);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchProfile();
    fetchHistory();
    fetchModelVersions();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchHistory, fetchModelVersions, fetchProfile]);

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
      await textAPI.stream(
        {
          user_id: userId,
          message: text,
          history: history.map((item) => ({
            role: 'user',
            content: item.input_text || item.text || '',
          })),
          personality_override: profile,
        },
        (event) => {
          if (event.type === 'delta') {
            setHistory((prev) =>
              prev.map((item) =>
                item.interaction_id === draft.interaction_id
                  ? { ...item, response: `${item.response}${event.content}` }
                  : item
              )
            );
          }
          if (event.type === 'done') {
            finalPayload = {
              interaction_id: event.interaction_id,
              input_text: text,
              response: event.response,
              metadata: event.metadata || {},
              model_version: event.metadata?.model_version,
              profile: event.profile,
            };
            setProfile(event.profile);
            setHistory((prev) =>
              prev.map((item) =>
                item.interaction_id === draft.interaction_id ? finalPayload : item
              )
            );
            setLastResponse(finalPayload);
          }
        }
      );
      return finalPayload;
    } catch (err) {
      console.error('API connection failed', err);
      setHistory((prev) => prev.filter((item) => item.interaction_id !== draft.interaction_id));
      toast.error('Connection failed. Is the FastAPI backend running?');
      throw err;
    } finally {
      setIsProcessing(false);
    }
  };

  const updateProfile = async (key, value) => {
    try {
      const nextProfile = { ...(profile || { user_id: userId }), [key]: value };
      const res = await userAPI.updateProfile(userId, nextProfile);
      setProfile(res.data);
    } catch (err) {
      toast.error('Failed to update preferences');
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
      toast.success(`Feedback logged (${res.data.reward.toFixed(2)})`);
    } catch (err) {
      toast.error('Failed to submit feedback');
    }
  };

  return (
    <AIContext.Provider value={{
      status,
      userId,
      history,
      isProcessing,
      lastResponse,
      profile,
      modelVersions,
      processText,
      updateProfile,
      submitFeedback,
      refreshStatus: fetchStatus
    }}>
      {children}
    </AIContext.Provider>
  );
};

export const useAI = () => useContext(AIContext);
