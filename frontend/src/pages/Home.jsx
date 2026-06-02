import { useState, useRef, useEffect } from 'react';
import { Copy, Edit3, Check } from 'lucide-react';
import Header from '../components/Header';
import SearchBar from '../components/SearchBar';
import AdminDashboard from '../components/AdminDashboard';
import CitationBlock from '../components/CitationBlock';
import ChartBlock from '../components/ChartBlock';

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
  
  // State for the main search bar input, lifted up so chat bubbles can edit it
  const [query, setQuery] = useState('');

  // Tracks which message was just copied to show a brief checkmark animation
  const [copiedIndex, setCopiedIndex] = useState(null);
  
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
   * Helper function to copy text to the clipboard and show a temporary checkmark.
   * 
   * @param {string} text - The text to copy.
   * @param {number} idx - The index of the message being copied.
   */
  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  /**
   * Callback fired when the SearchBar form is submitted.
   * 
   * Purpose: Establishes a native browser WebSocket connection to the backend,
   * sends the user query, and processes the incoming streaming JSON payload.
   * 
   * @param {string} submittedQuery - The search string entered by the user.
   */
  const handleSearch = (submittedQuery) => {
    if (!isSearchActive) setIsSearchActive(true);
    
    // Append the user query to the local chat stream immediately
    setMessages((prev) => [...prev, { role: 'user', content: submittedQuery }]);
    
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
        ws.send(JSON.stringify({ query: submittedQuery }));
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
            setAgentState(data.content);
            setMessages((prev) => [
              ...prev.map(msg => (msg.role === 'step') ? { ...msg, isAnimating: false } : msg),
              { role: 'step', content: data.content, isAnimating: true }
            ]);
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
            // Stop animations for all steps of this execution
            setMessages(prev => prev.map(msg => (msg.role === 'step') ? { ...msg, isAnimating: false } : msg));
          }
          else if (data.type === 'citations') {
            // Attach citations to the most recent AI message
            try {
              const citations = JSON.parse(data.content);
              setMessages((prev) => {
                const newMessages = [...prev];
                // Find the last AI message and attach citations to it
                for (let i = newMessages.length - 1; i >= 0; i--) {
                  if (newMessages[i].role === 'ai') {
                    newMessages[i] = { ...newMessages[i], citations };
                    break;
                  }
                }
                return newMessages;
              });
            } catch (err) {
              console.error("Failed to parse citations:", err);
            }
          }
          else if (data.type === 'chart') {
            try {
              const chartData = JSON.parse(data.content);
              setMessages((prev) => {
                const newMessages = [...prev];
                // Find the last AI message and attach chart to it
                for (let i = newMessages.length - 1; i >= 0; i--) {
                  if (newMessages[i].role === 'ai') {
                    newMessages[i] = { ...newMessages[i], chart: chartData };
                    return newMessages;
                  }
                }
                return [...newMessages, { role: 'ai', content: '', chart: chartData }];
              });
            } catch (err) {
              console.error("Failed to parse chart data:", err);
            }
          }
          else if (data.type === 'error') {
            // Display any backend errors directly in the agent status bar
            console.error("Backend Error:", data.content);
            setAgentState(`Error: ${data.content}`);
            setIsStreaming(false);
            // Stop animations on error as well
            setMessages(prev => prev.map(msg => (msg.role === 'step') ? { ...msg, isAnimating: false } : msg));
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
    <div className="h-screen overflow-hidden flex flex-col bg-gray-50 text-gray-900 dark:bg-slate-900 dark:text-gray-100 transition-colors duration-300 font-sans">
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
                  {messages.map((msg, idx) => {
                    if (msg.role === 'step') {
                      const isAnimating = msg.isAnimating !== false;
                      
                      return (
                        <div key={idx} className={`flex relative items-start my-4 ml-8 ${isAnimating ? "" : "opacity-80"}`}>
                          
                          {/* Continuous Energy Flow Line */}
                          <div className={`absolute left-[-22.5px] top-6 w-[2px] h-[calc(100%+15px)] rounded-full opacity-60 ${isAnimating ? "bg-gradient-to-b from-blue-500 via-purple-500 to-transparent" : "bg-slate-300 dark:bg-slate-700"}`}></div>

                          {/* Animated Processing Node */}
                          <div className="absolute left-[-25.5px] top-3 flex items-center justify-center">
                            {isAnimating && <div className="absolute w-5 h-5 rounded-full bg-blue-400/40 animate-ping"></div>}
                            <div className={`absolute w-3 h-3 rounded-full ${isAnimating ? "bg-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.8)] animate-pulse" : "bg-slate-400 dark:bg-slate-600"}`}></div>
                            <div className="w-1.5 h-1.5 rounded-full bg-white relative z-10"></div>
                          </div>

                          {/* Futuristic Rotating Gradient Bubble */}
                          <div className="relative overflow-hidden p-[2px] rounded-full shadow-md group">
                            {/* Animated rotating border */}
                            {isAnimating ? (
                              <div className="absolute inset-[-100%] animate-[spin_3s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#c084fc_0%,#3b82f6_50%,#2dd4bf_100%)] opacity-80"></div>
                            ) : (
                              <div className="absolute inset-x-0 inset-y-0 bg-slate-300 dark:bg-slate-700"></div>
                            )}
                            
                            {/* Bubble Content */}
                            <div className="relative bg-slate-50 dark:bg-slate-900 rounded-full px-5 py-2 flex items-center gap-3">
                              {/* Inner spinning gear / reactor */}
                              <div className="w-4 h-4">
                                {isAnimating ? (
                                  <svg className="animate-spin text-blue-500 drop-shadow-[0_0_5px_rgba(59,130,246,0.8)]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                  </svg>
                                ) : (
                                  <svg className="text-slate-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                                  </svg>
                                )}
                              </div>
                              <span className={`font-bold text-sm tracking-wide ${isAnimating ? "bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400" : "text-slate-500 dark:text-slate-400"}`}>
                                {msg.content}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    }
                    
                    return (
                    <div 
                      key={idx} 
                      className={`flex ${msg.role === 'user' ? 'justify-end mb-2 group' : 'justify-start'}`}
                    >
                      {msg.role === 'user' ? (
                        <div className="flex flex-col items-end max-w-[85%] sm:max-w-[75%]">
                          <div className="bg-blue-600 text-white rounded-3xl rounded-br-sm px-6 py-4 shadow-sm text-lg w-full">
                            <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                          </div>
                          
                          {/* Utility Buttons (Copy / Edit) - Visible on hover */}
                          <div className="flex gap-2 mt-2 mr-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                            <button 
                              onClick={() => handleCopy(msg.content, idx)}
                              className="text-slate-400 hover:text-blue-500 transition-colors p-1 flex items-center gap-1 text-xs font-medium"
                              title="Copy prompt"
                            >
                              {copiedIndex === idx ? (
                                <><Check className="w-3.5 h-3.5 text-emerald-500" /> <span className="text-emerald-500">Copied</span></>
                              ) : (
                                <><Copy className="w-3.5 h-3.5" /> Copy</>
                              )}
                            </button>
                            <button 
                              onClick={() => {
                                setQuery(msg.content);
                                // Optional UX touch: smooth scroll to bottom when they click edit so they see the search bar
                                scrollToBottom();
                              }}
                              className="text-slate-400 hover:text-blue-500 transition-colors p-1 flex items-center gap-1 text-xs font-medium ml-2"
                              title="Edit prompt"
                            >
                              <Edit3 className="w-3.5 h-3.5" /> Edit
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-col items-start w-full group">
                          {msg.content && (
                            <div className="max-w-[85%] sm:max-w-[75%] rounded-3xl px-6 py-4 shadow-sm text-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-bl-sm">
                              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                            </div>
                          )}
                          
                          {/* Utility Buttons (Copy) - Visible on hover */}
                          {msg.content && (
                            <div className="flex gap-2 mt-2 ml-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                              <button 
                                onClick={() => handleCopy(msg.content, idx)}
                                className="text-slate-400 hover:text-blue-500 transition-colors p-1 flex items-center gap-1 text-xs font-medium"
                                title="Copy response"
                              >
                                {copiedIndex === idx ? (
                                  <><Check className="w-3.5 h-3.5 text-emerald-500" /> <span className="text-emerald-500">Copied</span></>
                                ) : (
                                  <><Copy className="w-3.5 h-3.5" /> Copy</>
                                )}
                              </button>
                            </div>
                          )}

                          {msg.chart && (
                            <div className={`w-full max-w-[85%] sm:max-w-[75%] ${msg.content ? 'mt-4' : ''}`}>
                              <ChartBlock chartData={msg.chart} />
                            </div>
                          )}
                          
                          {msg.citations && msg.citations.length > 0 && (
                            <CitationBlock citations={msg.citations} />
                          )}
                        </div>
                      )}
                    </div>
                  )})}
                  
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
                query={query}
                setQuery={setQuery}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
