import React, { useState } from 'react';
import { Search, ArrowUp } from 'lucide-react';

/**
 * SearchBar Component
 * 
 * Purpose: Renders the primary user input interface. It adapts its layout and styling
 * depending on whether the application is in an active search state.
 * 
 * Expected Output / State Mutation:
 * - Local State: Updates the `query` text as the user types. Toggles `isLoading` during API calls.
 * - Side Effects: Calls `onSearch` prop to notify parent component to change layout state
 *   and initiate the chat stream UI.
 * 
 * @param {Object} props - The component props.
 * @param {boolean} props.isActive - Indicates if a search has been executed. If false, 
 *        the bar is centered with a glowing effect. If true, it moves to the bottom.
 * @param {Function} props.onSearch - Callback function to handle the submitted query.
 */
export default function SearchBar({ isActive, onSearch }) {
  // Local state for the input field value
  const [query, setQuery] = useState('');
  // Local state to track if a network request is currently pending
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Handles the form submission event.
   * Prevents default page reload, invokes the parent callback to update the UI layout,
   * and acts as a stub for the future WebSocket or REST API integration.
   * 
   * @param {React.FormEvent} e - The default HTML form submit event.
   */
  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    
    // Prevent submitting empty or whitespace-only queries
    if (!query.trim()) return;

    // Trigger parent UI transition (e.g., move search bar to bottom, reveal chat stream)
    onSearch(query);
    
    // Begin loading state (e.g., disable input and button)
    setIsLoading(true);
    console.log(`[SAGE API Stub] Sending query to backend: "${query}"`);

    try {
      /*
       * =========================================================================
       * FUTURE BACKEND API INTEGRATION POINT (WebSocket / REST)
       * =========================================================================
       * 
       * The Multi-Agent RAG orchestrator running on FastAPI will handle this query.
       * We will likely use WebSockets for real-time text streaming and state updates.
       * 
       * Example WebSocket Implementation:
       * 
       * const ws = new WebSocket('ws://localhost:8000/ws/chat');
       * 
       * ws.onopen = () => {
       *   // Send the initial query once connection is established
       *   ws.send(JSON.stringify({ query: query }));
       * };
       * 
       * ws.onmessage = (event) => {
       *   const data = JSON.parse(event.data);
       *   // Update parent context or state management (e.g., Zustand/Redux) 
       *   // with streaming tokens or agent state updates.
       * };
       * 
       * ws.onerror = (error) => {
       *   console.error("WebSocket Error:", error);
       * };
       * =========================================================================
       */
      
      // Simulating a network delay (e.g., orchestrator agent is thinking)
      await new Promise(resolve => setTimeout(resolve, 1500));
      console.log("[SAGE API Stub] Backend response successfully simulated.");
      
    } catch (error) {
      console.error("[SAGE API Stub] Error during backend communication:", error);
      // In production, we would dispatch an error state to the UI here
    } finally {
      // Clean up after the request finishes
      setIsLoading(false);
      setQuery(''); // Clear the input field for the next query
    }
  };

  return (
    <div 
      className={`w-full max-w-4xl mx-auto px-4 transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)]
      ${isActive ? 'pb-6' : 'flex-1 flex flex-col justify-center mb-[15vh]'}`}
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
          disabled={isLoading}
        />
        
        <button
          type="submit"
          disabled={!query.trim() || isLoading}
          className={`absolute right-3 p-3 rounded-full transition-all duration-200 flex items-center justify-center ${
            query.trim() 
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
