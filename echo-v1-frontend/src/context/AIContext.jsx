import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { coreAPI, memoryAPI, textAPI, voiceAPI } from '../api/client';
import toast from 'react-hot-toast';

const AIContext = createContext();

export const AIProvider = ({ children }) => {
  const [status, setStatus] = useState('offline');
  const [personality, setPersonality] = useState('Echo');

  // Automatically clear memory when personality changes
  useEffect(() => {
    const wipeMemoryOnSwitch = async () => {
      try {
        await memoryAPI.clear();
        setHistory([]);
        setLastResponse(null);
      } catch (err) {
        console.warn('Failed to auto-wipe memory', err);
      }
    };
    wipeMemoryOnSwitch();
  }, [personality]);
  const [history, setHistory] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
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
      const historyData = res.data.history || [];
      // Store in oldest-to-newest order (FIFO)
      setHistory(Array.isArray(historyData) ? [...historyData].reverse() : []);
    } catch (err) {
      console.warn('Failed to fetch history', err);
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
      // Append to history (newest at bottom)
      setHistory(prev => [...prev, data].slice(-50));
      return data;
    } catch (err) {
      console.error('API connection failed', err);
      toast.error('Connection failed. Is the backend running?');
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
      toast.success('Synapse cleared');
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
      lastResponse,
      processText,
      clearMemory,
      refreshStatus: fetchStatus
    }}>
      {children}
    </AIContext.Provider>
  );
};

export const useAI = () => useContext(AIContext);
