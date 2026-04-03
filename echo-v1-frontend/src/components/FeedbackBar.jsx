import React, { useState } from 'react';

const TAG_OPTIONS = ['helpful', 'confusing', 'too_long', 'supportive', 'clear'];

const FeedbackBar = ({ interactionId, onSubmit, disabled }) => {
  const [selectedTags, setSelectedTags] = useState([]);

  const toggleTag = (tag) => {
    setSelectedTags((current) =>
      current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag]
    );
  };

  return (
    <div className="space-y-3 max-w-[80%]">
      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onSubmit(interactionId, 'up', selectedTags)}
          className="px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-400/20 text-emerald-300 text-xs font-bold uppercase tracking-widest"
        >
          👍 Helpful
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onSubmit(interactionId, 'down', selectedTags)}
          className="px-3 py-2 rounded-xl bg-rose-500/10 border border-rose-400/20 text-rose-300 text-xs font-bold uppercase tracking-widest"
        >
          👎 Needs Work
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {TAG_OPTIONS.map((tag) => (
          <button
            key={tag}
            type="button"
            onClick={() => toggleTag(tag)}
            className={`px-2 py-1 rounded-full text-[10px] uppercase tracking-widest border ${
              selectedTags.includes(tag)
                ? 'bg-solace-blue/20 border-solace-blue/40 text-solace-blue'
                : 'bg-white/5 border-white/10 text-text-muted'
            }`}
          >
            {tag.replace('_', ' ')}
          </button>
        ))}
      </div>
    </div>
  );
};

export default FeedbackBar;
