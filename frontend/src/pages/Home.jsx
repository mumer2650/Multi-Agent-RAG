import React, { useState } from 'react';
import Header from '../components/Header';
import SearchBar from '../components/SearchBar';

/**
 * Home Component (ChatLayout)
 * 
 * Purpose: Serves as the primary layout for the SAGE application. It orchestrates the 
 * high-level state, determining the position of the SearchBar and managing the visibility 
 * and data of the chat stream.
 * 
 * Expected Output:
 * - Renders a full-height container with dynamic flex layouts.
 * - Transitions smoothly between a "landing" state (centered search bar) and an 
 *   "active" state (chat stream above, search bar below).
 */
export default function Home() {
  // Boolean state tracking whether the user has initiated a conversation.
  // Determines if the layout shifts from center to bottom-aligned.
  const [isSearchActive, setIsSearchActive] = useState(false);
  
  // Array state holding the history of chat messages.
  // In a full implementation, this will hold both user inputs and streaming AI responses.
  const [messages, setMessages] = useState([]);

  /**
   * Callback fired when the SearchBar form is submitted.
   * 
   * Purpose: Updates the layout to the "active" mode if it isn't already, 
   * and immediately appends the user's query to the chat history array.
   * 
   * @param {string} query - The search string entered by the user.
   */
  const handleSearch = (query) => {
    // If this is the first query, trigger the layout shift
    if (!isSearchActive) {
      setIsSearchActive(true);
    }
    
    // Append the new user message to the local chat stream state
    setMessages((prevMessages) => [
      ...prevMessages,
      { role: 'user', content: query }
    ]);
    
    // Note: AI responses will be appended here asynchronously via WebSockets 
    // in the full implementation (refer to the SearchBar API stub).
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-900 transition-colors duration-300 text-slate-900 dark:text-slate-100 font-sans">
      <Header />
      
      {/* 
        Main Content Area 
        Relative positioning ensures smooth transitions for child elements.
        Overflow hidden prevents main scrollbar; scrolling is handled in the chat area.
      */}
      <main className="flex-1 flex flex-col relative w-full h-[calc(100vh-88px)]">
        
        {/* 
          Chat Stream Space: 
          Only rendered when a search is active. Takes up remaining height above the search bar.
        */}
        {isSearchActive && (
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 flex flex-col">
            <div className="max-w-4xl w-full mx-auto space-y-6">
              {messages.map((msg, idx) => (
                <div 
                  key={idx} 
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`max-w-[85%] sm:max-w-[75%] rounded-3xl px-6 py-4 shadow-sm text-lg ${
                      msg.role === 'user' 
                        ? 'bg-blue-600 text-white rounded-br-sm' 
                        : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-bl-sm'
                    }`}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  </div>
                </div>
              ))}
              {/* 
                Future enhancement: Add a loading indicator or streaming text block here 
                while waiting for the AI backend.
              */}
            </div>
          </div>
        )}

        {/* 
          Search Bar Container:
          If not active, it acts as a flex-1 container to center the SearchBar via flex properties.
          If active, it sticks to the bottom.
        */}
        <div className={`w-full ${!isSearchActive ? 'flex-1 flex flex-col' : 'pb-6 pt-2 shrink-0'}`}>
          <SearchBar isActive={isSearchActive} onSearch={handleSearch} />
        </div>
      </main>
    </div>
  );
}
