import { useState } from 'react';

export default function CitationBlock({ citations }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!citations || citations.length === 0) {
    return null;
  }

  const getCitationIcon = (type) => {
    switch (type) {
      case 'retrieval':
        return '📄';
      case 'database':
        return '🗄️';
      case 'analysis':
        return '🔬';
      default:
        return '📌';
    }
  };

  const formatCitation = (citation) => {
    switch (citation.type) {
      case 'retrieval':
        return {
          icon: getCitationIcon('retrieval'),
          title: `${citation.source}${citation.page ? ` (Page ${citation.page})` : ''}`,
          relevance: citation.relevance_score ? `${(citation.relevance_score * 100).toFixed(0)}%` : null,
          snippet: citation.snippet || 'No preview available',
          link: `http://localhost:8000/static/${citation.source}${citation.page ? `#page=${citation.page}` : ''}`
        };
      case 'database':
        return {
          icon: getCitationIcon('database'),
          title: 'Database Query',
          records: citation.record_count,
          snippet: citation.source || 'SQL Query executed',
        };
      case 'analysis':
        return {
          icon: getCitationIcon('analysis'),
          title: 'Analysis Result',
          snippet: citation.source || 'Python analysis performed',
        };
      default:
        return {
          icon: getCitationIcon('default'),
          title: citation.source || 'Citation',
          snippet: 'No details available',
        };
    }
  };

  return (
    <div className="mt-4 max-w-[85%] sm:max-w-[75%]">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors text-left"
      >
        <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          📚 Sources ({citations.length})
        </span>
        <span className={`ml-auto transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-2">
          {citations.map((citation, idx) => {
            const formatted = formatCitation(citation);
            return (
              <div
                key={idx}
                className="p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:border-slate-300 dark:hover:border-slate-600 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <span className="text-lg flex-shrink-0">{formatted.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      {formatted.link ? (
                        <a 
                          href={formatted.link} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="font-semibold text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline flex items-center gap-1"
                        >
                          {formatted.title}
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                        </a>
                      ) : (
                        <p className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                          {formatted.title}
                        </p>
                      )}
                      {formatted.relevance && (
                        <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
                          {formatted.relevance} match
                        </span>
                      )}
                      {formatted.records && (
                        <span className="text-xs bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 px-2 py-1 rounded">
                          {formatted.records} records
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-400 mt-2 line-clamp-2">
                      {formatted.snippet}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
