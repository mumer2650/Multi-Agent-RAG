import { useState } from 'react';
import { Search, ArrowUp } from 'lucide-react';

/**
 * SearchBar Component
 * 
 * Purpose: Renders the primary user input interface. It adapts its layout and styling
 * depending on whether the application is in an active search state.
 * 
 * @param {Object} props - The component props.
 * @param {boolean} props.isActive - Indicates if a search has been executed.
 * @param {Function} props.onSearch - Callback function to handle the submitted query.
 * @param {boolean} props.isStreaming - Disables the input field while the AI is answering.
 */
export default function SearchBar({ isActive, onSearch, isStreaming }) {
  // Local state for the input field value
  const [query, setQuery] = useState('');

  /**
   * Handles the form submission event.
   * Prevents default page reload and passes the query up to the parent component 
   * where the WebSocket connection is managed.
   * 
   * @param {React.FormEvent} e - The default HTML form submit event.
   */
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    
    // Capture the current query state
    const submittedQuery = query.trim();
    
    // Prevent submitting empty queries or submitting while AI is already streaming
    if (!submittedQuery || isStreaming) return;

    // Immediately clear the input field state
    setQuery('');
    
    // Push the heavy WebSocket initialization to the back of the event loop.
    // This gives the browser's rendering engine enough time to instantly paint 
    // the empty input field to the screen before the main thread is blocked.
    setTimeout(() => {
      onSearch(submittedQuery);
    }, 0);
  };

  return (
    <div 
      className={`w-full max-w-4xl mx-auto px-4 transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)]
      ${isActive ? '' : 'flex-1 flex flex-col justify-center mb-[15vh]'}`}
    >
      {/* Landing State Greeting: Only shown before the first query is sent */}
      {!isActive && (
        <div className="text-center mb-10 animate-fade-in flex flex-col items-center">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-semibold bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600 bg-clip-text text-transparent mb-4 tracking-tight">
            How can I help you today?
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-lg max-w-2xl">
            SAGE is your expert assistant for appliance specifications, spatial clearances, and energy calculations.
          </p>
        </div>
      )}

      {/* The Search Form Container */}
      <form 
        onSubmit={handleSearchSubmit}
        className={`relative flex items-center w-full rounded-[2rem] bg-white dark:bg-slate-800 transition-all duration-500
          ${isActive 
            ? 'border border-slate-300 dark:border-slate-600 shadow-sm' 
            : 'border border-transparent animate-glow'
          }`}
      >
        <Search className="absolute left-6 w-6 h-6 text-slate-400 dark:text-slate-500 pointer-events-none" />
        
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask SAGE about refrigerators, washing machines, or LED TVs..."
          className="w-full py-5 pl-16 pr-16 rounded-[2rem] bg-transparent text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none text-lg"
          disabled={isStreaming} // Disable input while AI is answering
        />
        
        <button
          type="submit"
          disabled={!query.trim() || isStreaming} // Disable button while AI is answering
          className={`absolute right-3 p-3 rounded-full transition-all duration-200 flex items-center justify-center ${
            query.trim() && !isStreaming
              ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md transform hover:scale-105 active:scale-95' 
              : 'bg-slate-100 dark:bg-slate-700 text-slate-300 dark:text-slate-500 cursor-not-allowed'
          }`}
          aria-label="Send Query"
        >
          <ArrowUp className="w-5 h-5" strokeWidth={3} />
        </button>
      </form>
    </div>
  );
}
