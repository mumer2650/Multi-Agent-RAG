import { useState, useRef, useEffect } from 'react';
import Header from '../components/Header';
import SearchBar from '../components/SearchBar';
import AdminDashboard from '../components/AdminDashboard';

/**
 * Home Component (ChatLayout)
 * 
 * Purpose: Orchestrates the main chat interface layout and manages the state 
 * for the WebSocket connection and message stream.
 */
export default function Home() {
  // State for toggling between the Chat UI and the Admin Dashboard
  const [currentView, setCurrentView] = useState('chat');

  // Boolean state tracking whether the user has initiated a conversation.
  const [isSearchActive, setIsSearchActive] = useState(false);
  
  // Array state holding the actual chat tokens/words.
  const [messages, setMessages] = useState([]);
  
  // A string to display the current 'thinking' status of the AI.
  const [agentState, setAgentState] = useState('');
  
  // A boolean to disable the input field while the AI is answering.
  const [isStreaming, setIsStreaming] = useState(false);

  // Reference to the bottom of the chat stream container
  const messagesEndRef = useRef(null);

  /**
   * Helper function to smoothly scroll the chat container to the bottom.
   * This ensures the newest tokens or status messages are always in view.
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  /**
   * Auto-Scroll Effect
   * 
   * Listens for changes to the `messages` array or `agentState` string.
   * Whenever the AI streams a new token or updates its thinking status, 
   * this effect automatically scrolls the view down.
   */
  useEffect(() => {
    scrollToBottom();
  }, [messages, agentState]);

  /**
   * Callback fired when the SearchBar form is submitted.
   * 
   * Purpose: Establishes a native browser WebSocket connection to the backend,
   * sends the user query, and processes the incoming streaming JSON payload.
   * 
   * @param {string} query - The search string entered by the user.
   */
  const handleSearch = (query) => {
    if (!isSearchActive) setIsSearchActive(true);
    
    // Append the user query to the local chat stream immediately
    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    
    // Lock the input field and set an initial connecting status
    setIsStreaming(true);
    setAgentState('Connecting to SAGE...');

    try {
      // Establish the native WebSocket connection targeting our FastAPI backend
      const ws = new WebSocket('ws://localhost:8000/ws/chat');

      /**
       * onopen Event Listener
       * Triggered when the WebSocket connection is successfully established.
       * We send the user's input as a JSON string matching the ChatRequest schema.
       */
      ws.onopen = () => {
        setAgentState(''); // Clear connecting text
        ws.send(JSON.stringify({ query: query }));
      };

      /**
       * onmessage Event Listener
       * Triggered whenever the server sends data. We parse the incoming JSON payload
       * and update our React state based on the 'type' field.
       */
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'status') {
            // Update the agentState variable so the user sees what the AI is doing
            setAgentState(data.content);
          } 
          else if (data.type === 'token') {
            // Once tokens start arriving, clear the agent thinking status
            setAgentState('');
            
            // Append the content chunk to the messages state so the text types out in real-time
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              
              if (lastMessage && lastMessage.role === 'ai') {
                // If the last message is from the AI, append the new token
                newMessages[newMessages.length - 1] = {
                  ...lastMessage,
                  content: lastMessage.content + data.content
                };
              } else {
                // Otherwise, create a new AI message object for the first token
                newMessages.push({ role: 'ai', content: data.content });
              }
              return newMessages;
            });
          } 
          else if (data.type === 'done') {
            // Un-lock the input field for the next query
            setIsStreaming(false);
          }
          else if (data.type === 'error') {
            // Display any backend errors directly in the agent status bar
            console.error("Backend Error:", data.content);
            setAgentState(`Error: ${data.content}`);
            setIsStreaming(false);
            ws.close();
          }
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      /**
       * onerror Event Listener
       * Handles network-level errors (e.g., server down, connection refused).
       */
      ws.onerror = (error) => {
        console.error("WebSocket encountered an error:", error);
        setAgentState('Connection error. Is the backend running?');
        setIsStreaming(false);
      };

      /**
       * onclose Event Listener
       * Cleans up the UI state when the backend closes the connection.
       */
      ws.onclose = () => {
        console.log("WebSocket connection closed.");
        // Only clear the agent state if we haven't already displayed an error
        setAgentState((prev) => prev.startsWith('Error') || prev.startsWith('Connection') ? prev : '');
        setIsStreaming(false);
      };

    } catch (error) {
      // Catch synchronous errors during WebSocket instantiation
      console.error("Failed to initialize WebSocket:", error);
      setAgentState('Failed to connect.');
      setIsStreaming(false);
    }
  };

  return (
    // Layout Lock: We use 'h-screen overflow-hidden' instead of 'min-h-screen'.
    // This strictly confines the app to the exact viewport height, preventing the 
    // global page from scrolling and ensuring the search bar remains locked to the bottom.
    <div className="h-screen overflow-hidden flex flex-col bg-slate-50 dark:bg-slate-900 transition-colors duration-300 text-slate-900 dark:text-slate-100 font-sans">
      <Header currentView={currentView} onViewChange={setCurrentView} />
      
      <main className="flex-1 flex flex-col relative w-full h-[calc(100vh-88px)]">
        
        {currentView === 'admin' ? (
          <AdminDashboard />
        ) : (
          <>
            {/* Chat Stream Area */}
            {isSearchActive && (
              <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 flex flex-col">
                <div className="max-w-4xl w-full mx-auto space-y-6">
                  {/* Render aggregated messages in a clean, readable text block */}
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
                  
                  {/* Anchor element for the auto-scroll hook to target */}
                  <div ref={messagesEndRef} />
                </div>
              </div>
            )}

            {/* Search Bar Container */}
            <div className={`w-full ${!isSearchActive ? 'flex-1 flex flex-col' : 'pb-6 pt-2 shrink-0'}`}>
              
              {/* Render the agentState in a small, italicized text block above the search bar */}
              {agentState && (
                <div className="max-w-4xl mx-auto w-full px-4 mb-3 text-center">
                  <span className="text-sm italic text-slate-500 dark:text-slate-400 animate-pulse">
                    {agentState}
                  </span>
                </div>
              )}
              
              <SearchBar 
                isActive={isSearchActive} 
                onSearch={handleSearch} 
                isStreaming={isStreaming} 
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
