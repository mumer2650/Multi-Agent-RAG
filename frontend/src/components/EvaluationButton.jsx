import { useState } from 'react';
import { Activity, Loader2, X } from 'lucide-react';

export default function EvaluationButton({ userQuery }) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);

  const fetchEvaluation = async () => {
    setIsOpen(true);
    if (metrics) return; // Already fetched
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`http://127.0.0.1:8000/metrics/message?query=${encodeURIComponent(userQuery)}`);
      const data = await response.json();
      
      if (data.status === 'completed') {
        setMetrics(data);
      } else if (data.status === 'pending') {
        setError('Grading in progress... try again in a few seconds.');
      } else {
        setError('Failed to fetch evaluation.');
      }
    } catch (err) {
      setError('Network error.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative inline-block mt-2">
      <button 
        onClick={fetchEvaluation}
        className="text-slate-400 hover:text-purple-500 transition-colors p-1 flex items-center gap-1 text-xs font-medium ml-2 bg-transparent border-none"
        title="View Live Evaluation"
      >
        <Activity className="w-3.5 h-3.5" /> Eval
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-2 w-64 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 p-4 z-50">
          <div className="flex justify-between items-center mb-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Live Evaluation</h4>
            <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
              <X className="w-4 h-4" />
            </button>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-4 gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-purple-500" />
              <span className="text-xs text-slate-500">Grading response...</span>
            </div>
          ) : error ? (
            <div className="text-xs text-amber-600 dark:text-amber-400 py-2 text-center">
              {error}
            </div>
          ) : metrics ? (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-700 dark:text-slate-300">Context Precision</span>
                <span className="text-sm font-bold text-purple-600 dark:text-purple-400">{(metrics.context_precision * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5">
                <div className="bg-purple-500 h-1.5 rounded-full" style={{ width: `${metrics.context_precision * 100}%` }}></div>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-700 dark:text-slate-300">Faithfulness</span>
                <span className="text-sm font-bold text-blue-600 dark:text-blue-400">{(metrics.faithfulness * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5">
                <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${metrics.faithfulness * 100}%` }}></div>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-700 dark:text-slate-300">Answer Relevance</span>
                <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{(metrics.answer_relevance * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5">
                <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${metrics.answer_relevance * 100}%` }}></div>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
