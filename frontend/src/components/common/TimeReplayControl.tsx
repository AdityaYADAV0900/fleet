import React, { useState, useEffect, useRef } from 'react';
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Play,
  Pause,
  RotateCcw,
  Clock,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export const DEMO_BOOKMARKS = [
  { label: 'Nov 05', date: '2025-11-05', desc: 'Baseline operational window' },
  { label: 'Nov 15', date: '2025-11-15', desc: 'Mid-period evaluation' },
  { label: 'Nov 25', date: '2025-11-25', desc: 'Active inspection view' },
  { label: 'Dec 31', date: '2025-12-31', desc: 'Period closing snapshot' },
];

export const TimeReplayControl: React.FC = () => {
  const { asOfDate, setAsOfDate } = useAuth();
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const playTimerRef = useRef<number | null>(null);

  const currentDate = asOfDate || '2025-11-25';

  const adjustDate = (days: number) => {
    const d = new Date(currentDate);
    if (isNaN(d.getTime())) return;
    d.setDate(d.getDate() + days);
    const newStr = d.toISOString().split('T')[0];
    setAsOfDate(newStr);
  };

  // Play / Pause loop cycling through bookmarks or day-by-day
  useEffect(() => {
    if (!isPlaying) {
      if (playTimerRef.current) {
        window.clearInterval(playTimerRef.current);
        playTimerRef.current = null;
      }
      return;
    }

    playTimerRef.current = window.setInterval(() => {
      const currentIndex = DEMO_BOOKMARKS.findIndex((b) => b.date === asOfDate);
      const nextIndex = (currentIndex + 1) % DEMO_BOOKMARKS.length;
      setAsOfDate(DEMO_BOOKMARKS[nextIndex].date);
    }, 2500);

    return () => {
      if (playTimerRef.current) {
        window.clearInterval(playTimerRef.current);
        playTimerRef.current = null;
      }
    };
  }, [isPlaying, asOfDate, setAsOfDate]);

  return (
    <div className="flex items-center space-x-1 sm:space-x-2 bg-white border border-[#E6E2F0] rounded-[10px] px-2.5 py-1 shadow-ap-sm font-mono text-xs">
      {/* Date View Label / Icon */}
      <div className="hidden lg:flex items-center space-x-1 text-[#6B5B84] pr-2 border-r border-[#EDE9F5]">
        <Clock className="w-3.5 h-3.5 text-[#7C3AED]" />
        <span className="text-[10px] uppercase font-semibold tracking-wider text-[#3B1D5E]">As-Of</span>
      </div>

      {/* Quick Jump Bookmarks */}
      <div className="hidden md:flex items-center space-x-1">
        {DEMO_BOOKMARKS.map((bm) => {
          const isActive = asOfDate === bm.date;
          return (
            <button
              key={bm.date}
              onClick={() => {
                setIsPlaying(false);
                setAsOfDate(bm.date);
              }}
              title={`${bm.label} (${bm.date}): ${bm.desc}`}
              className={`px-2 py-0.5 rounded-[6px] text-[10px] font-semibold transition ${
                isActive
                  ? 'bg-[#1DE9C0] text-[#3B1D5E] shadow-sm'
                  : 'bg-[#F4F2FB] text-[#6B5B84] hover:text-[#3B1D5E] hover:bg-[#EDE9F5] border border-transparent'
              }`}
            >
              {bm.label}
            </button>
          );
        })}
      </div>

      {/* Date Stepper Controls: -1d, Input, +1d */}
      <div className="flex items-center space-x-0.5">
        <button
          onClick={() => {
            setIsPlaying(false);
            adjustDate(-1);
          }}
          className="p-1 rounded-[6px] hover:bg-[#F4F2FB] text-[#6B5B84] hover:text-[#3B1D5E] transition"
          title="Previous Day (-1d)"
          aria-label="Previous Day"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>

        <div className="flex items-center space-x-1 px-1.5 py-0.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[6px]">
          <Calendar className="w-3 h-3 text-[#7C3AED] shrink-0" />
          <input
            type="date"
            value={currentDate}
            onChange={(e) => {
              setIsPlaying(false);
              setAsOfDate(e.target.value || '2025-11-25');
            }}
            className="bg-transparent text-[#3B1D5E] text-xs font-mono focus:outline-none w-[105px] cursor-pointer"
            title="Operational as-of cutoff date"
          />
        </div>

        <button
          onClick={() => {
            setIsPlaying(false);
            adjustDate(1);
          }}
          className="p-1 rounded-[6px] hover:bg-[#F4F2FB] text-[#6B5B84] hover:text-[#3B1D5E] transition"
          title="Next Day (+1d)"
          aria-label="Next Day"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Play / Pause Toggle */}
      <button
        onClick={() => setIsPlaying(!isPlaying)}
        className={`p-1 rounded-[6px] transition flex items-center gap-1 text-[11px] ${
          isPlaying
            ? 'bg-[#1DE9C0] text-[#3B1D5E] font-bold shadow-sm'
            : 'bg-[#F4F2FB] hover:bg-[#EDE9F5] text-[#6B5B84] hover:text-[#3B1D5E] border border-[#E6E2F0]'
        }`}
        title={isPlaying ? 'Pause auto-playback' : 'Auto-advance operational date view'}
      >
        {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
      </button>

      {/* Reset to Default */}
      {asOfDate !== '2025-11-25' && (
        <button
          onClick={() => {
            setIsPlaying(false);
            setAsOfDate('2025-11-25');
          }}
          className="p-1 rounded-[6px] hover:bg-[#F4F2FB] text-[#6B5B84] hover:text-[#7C3AED] transition"
          title="Reset to Baseline Date (2025-11-25)"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
