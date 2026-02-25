import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { coreAPI, memoryAPI, textAPI, voiceAPI } from '../api/client';
import toast from 'react-hot-toast';

const AIContext = createContext();

export const AIProvider = ({ children }) => {
  const [status, setStatus] = useState('offline');
  const [personality, setPersonality] = useState('Echo');
  const [history, setHistory] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(10);
  const [lastResponse, setLastResponse] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await coreAPI.getStatus();
      setStatus(res.data.status || 'online');
    } catch (err) {
      setStatus('offline');
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await memoryAPI.getHistory();
      setHistory(res.data.history || []);
    } catch (err) {
      console.error('Failed to fetch history', err);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchHistory();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchHistory]);

  const processText = async (text) => {
    setIsProcessing(true);
    try {
      const res = await textAPI.process(text, personality);
      const data = res.data;
      setLastResponse(data);
      setHistory(prev => [data, ...prev].slice(0, 50));
      toast.success('Synapse active');
      return data;
    } catch (err) {
      console.error('API connection failed', err);
      toast.error('Connection failed. Is the backend running?');
      throw err;
    } finally {
      setIsProcessing(false);
    }
  };

  const processVoice = async (audioBlob) => {
    setIsProcessing(true);
    try {
      const res = await voiceAPI.process(audioBlob, personality);
      setLastResponse(res.data);
      setHistory(prev => [res.data, ...prev].slice(0, 50));
      toast.success('Voice processed');
      return res.data;
    } catch (err) {
      toast.error('Failed to process voice');
      throw err;
    } finally {
      setIsProcessing(false);
    }
  };

  const clearMemory = async () => {
    try {
      await memoryAPI.clear();
      setHistory([]);
      setLastResponse(null);
      toast.success('Memory cleared');
    } catch (err) {
      toast.error('Failed to clear memory');
    }
  };

  return (
    <AIContext.Provider value={{
      status,
      personality,
      setPersonality,
      history,
      isProcessing,
      recordingDuration,
      setRecordingDuration,
      lastResponse,
      processText,
      processVoice,
      clearMemory,
      refreshStatus: fetchStatus
    }}>
      {children}
    </AIContext.Provider>
  );
};

export const useAI = () => useContext(AIContext);
