import React from 'react';

const SLIDERS = [
  { key: 'brevity_preference', label: 'Verbosity' },
  { key: 'support_preference', label: 'Emotional Tone' },
  { key: 'task_focus', label: 'Task Focus' },
  { key: 'engagement_preference', label: 'Engagement' },
];

const PreferenceSliders = ({ profile, onChange }) => {
  if (!profile) return null;

  return (
    <div className="grid gap-4 rounded-[1.75rem] bg-white/5 border border-white/10 p-5">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Adaptive Controls</p>
        <p className="text-sm text-text-secondary mt-1">These sliders condition prompts at inference time.</p>
      </div>
      {SLIDERS.map((item) => (
        <label key={item.key} className="space-y-2">
          <div className="flex items-center justify-between text-xs uppercase tracking-widest text-text-muted">
            <span>{item.label}</span>
            <span>{Math.round((profile[item.key] || 0) * 100)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={profile[item.key] || 0}
            onChange={(event) => onChange(item.key, Number(event.target.value))}
            className="w-full accent-cyan-400"
          />
        </label>
      ))}
      <div className="rounded-2xl bg-solace-purple/10 border border-solace-purple/20 px-4 py-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-solace-purple-glow">Learning Signal</p>
        <p className="text-xs text-text-secondary mt-1">Adapting to your preferences. Feedback points: {profile.points || 0}</p>
      </div>
    </div>
  );
};

export default PreferenceSliders;
