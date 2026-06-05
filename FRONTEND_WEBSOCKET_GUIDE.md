# WebSocket Integration Quick Reference

## Basic Connection

```javascript
// Connect to backend
const ws = new WebSocket('ws://localhost:8000/ws/chat');

ws.onopen = () => {
    console.log("Connected!");
    // Ready to send messages
};

ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    handleResponse(response);
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};

ws.onclose = () => {
    console.log("Disconnected");
};
```

## Sending a Query

```javascript
// Send query
ws.send(JSON.stringify({
    query: "Show me products under 50000"
}));

// Optional: With timeout
setTimeout(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            query: "Your question here"
        }));
    }
}, 500);
```

## Response Types

```javascript
function handleResponse(response) {
    switch(response.type) {
        case "status":
            // Show loading/progress
            updateStatus(response.content);
            // e.g., "🧠 Routing your query..."
            break;
            
        case "token":
            // Stream answer text
            appendToAnswer(response.content);
            break;
            
        case "citations":
            // Display citations
            const citations = JSON.parse(response.content);
            showCitations(citations);
            break;
            
        case "chart":
            // Render chart
            const chartData = JSON.parse(response.content);
            renderChart(chartData);
            break;
            
        case "done":
            // Response complete
            console.log("Response finished");
            break;
            
        case "error":
            // Show error
            showError(response.content);
            break;
    }
}
```

## Complete Example

```javascript
class ChatWidget {
    constructor(wsUrl = 'ws://localhost:8000/ws/chat') {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.currentAnswer = "";
        this.conversationHistory = [];
        
        this.connect();
    }
    
    connect() {
        this.ws = new WebSocket(this.wsUrl);
        this.ws.onopen = () => this.onOpen();
        this.ws.onmessage = (event) => this.onMessage(event);
        this.ws.onerror = (error) => this.onError(error);
        this.ws.onclose = () => this.onClose();
    }
    
    onOpen() {
        console.log("Connected to backend");
        document.getElementById('status').textContent = "Ready";
        document.getElementById('sendBtn').disabled = false;
    }
    
    onMessage(event) {
        const response = JSON.parse(event.data);
        
        switch(response.type) {
            case "status":
                this.updateStatus(response.content);
                break;
                
            case "token":
                this.currentAnswer += response.content;
                document.getElementById('answer').textContent = this.currentAnswer;
                break;
                
            case "citations":
                const citations = JSON.parse(response.content);
                this.displayCitations(citations);
                break;
                
            case "chart":
                const chart = JSON.parse(response.content);
                this.displayChart(chart);
                break;
                
            case "done":
                this.onResponseComplete();
                break;
                
            case "error":
                this.showError(response.content);
                break;
        }
    }
    
    onError(error) {
        console.error("WebSocket error:", error);
        this.showError("Connection error");
    }
    
    onClose() {
        console.log("Disconnected from backend");
        this.updateStatus("Disconnected");
        // Attempt to reconnect after 3 seconds
        setTimeout(() => this.connect(), 3000);
    }
    
    sendQuery(query) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.showError("Not connected to backend");
            return;
        }
        
        // Reset for new response
        this.currentAnswer = "";
        document.getElementById('answer').textContent = "";
        document.getElementById('citations').innerHTML = "";
        
        // Send query
        this.ws.send(JSON.stringify({ query: query }));
        
        this.updateStatus("🤔 Processing...");
        document.getElementById('sendBtn').disabled = true;
    }
    
    updateStatus(status) {
        document.getElementById('status').textContent = status;
    }
    
    displayCitations(citations) {
        let html = "<h3>Sources:</h3>";
        
        citations.forEach((cite, idx) => {
            if (cite.type === "retrieval") {
                html += `
                    <div class="citation">
                        <strong>[${cite.index}]</strong> ${cite.source} (Page ${cite.page})
                        <p>${cite.snippet}</p>
                        <small>Relevance: ${cite.relevance_score?.toFixed(2)}</small>
                    </div>
                `;
            } else if (cite.type === "database") {
                html += `
                    <div class="citation">
                        <strong>🗃️</strong> ${cite.source} (${cite.record_count} records)
                    </div>
                `;
            } else if (cite.type === "analysis") {
                html += `
                    <div class="citation">
                        <strong>📊</strong> ${cite.source}
                    </div>
                `;
            }
        });
        
        document.getElementById('citations').innerHTML = html;
    }
    
    displayChart(chartData) {
        // Use Chart.js, D3.js, or any visualization library
        // Example with Chart.js:
        
        const ctx = document.getElementById('chartCanvas').getContext('2d');
        
        if (chartData.chartType === "bar") {
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: chartData.data.map(d => d.model),
                    datasets: [{
                        label: chartData.meta?.title || 'Data',
                        data: chartData.data.map(d => d.price || d.energy_rating || 0),
                        backgroundColor: 'rgba(75, 192, 192, 0.5)'
                    }]
                }
            });
        }
    }
    
    onResponseComplete() {
        this.updateStatus("Ready");
        document.getElementById('sendBtn').disabled = false;
        
        // Save to history
        this.conversationHistory.push({
            role: "user",
            content: document.getElementById('query').value
        });
        this.conversationHistory.push({
            role: "assistant",
            content: this.currentAnswer
        });
    }
    
    showError(error) {
        console.error("Error:", error);
        document.getElementById('error').textContent = error;
        document.getElementById('error').style.display = "block";
        document.getElementById('sendBtn').disabled = false;
    }
}

// Usage
const chat = new ChatWidget();

document.getElementById('sendBtn').addEventListener('click', () => {
    const query = document.getElementById('query').value;
    if (query.trim()) {
        chat.sendQuery(query);
        document.getElementById('query').value = '';
    }
});

// Send on Enter key
document.getElementById('query').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('sendBtn').click();
    }
});
```

## HTML Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Agent RAG Chat</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.3.0/dist/chart.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; }
        .container { padding: 20px; }
        .input-area { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        #status { color: #666; font-size: 0.9em; }
        #answer { background: #f5f5f5; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        #citations { background: #f9f9f9; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .citation { margin: 10px 0; padding: 10px; border-left: 3px solid #007bff; }
        #error { color: red; padding: 10px; background: #ffe5e5; border-radius: 4px; margin-bottom: 20px; display: none; }
        canvas { max-width: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Multi-Agent RAG Chat</h1>
        
        <div id="status">Connecting...</div>
        
        <div id="error"></div>
        
        <div class="input-area">
            <input type="text" id="query" placeholder="Ask anything..." />
            <button id="sendBtn" disabled>Send</button>
        </div>
        
        <div id="answer"></div>
        <div id="citations"></div>
        
        <canvas id="chartCanvas"></canvas>
    </div>
    
    <script src="chat.js"></script>
</body>
</html>
```

## Response Flow Diagram

```
User Types Query
    ↓
[Send Button Click]
    ↓
ws.send({ query: "..." })
    ↓
Backend Processes
    ↓
Response Stream Starts:
    1. status: "🧠 Routing your query..."
    2. status: "🗃️ Querying product database..."
    3. status: "🐍 Running analysis..."
    4. status: "💡 Generating answer..."
    5. token: "The" (1st word)
    6. token: " best" (2nd word)
    7. token: " products..." (rest)
    8. citations: [{ type: "database", ... }]
    9. chart: { chartType: "bar", data: [...] }
    10. done: ""
    ↓
Frontend Renders Result
```

## Environment Variables

```javascript
// Production
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws/chat';

// Or in .env
REACT_APP_WS_URL=ws://localhost:8000/ws/chat
```

## Error Handling

```javascript
try {
    if (!window.WebSocket) {
        throw new Error("WebSocket not supported");
    }
    
    const ws = new WebSocket(wsUrl);
    
    ws.onerror = (event) => {
        console.error("WebSocket error:", event);
        // Handle: connection refused, timeout, etc.
    };
    
} catch (error) {
    console.error("Failed to connect:", error);
    // Show user-friendly message
}
```

## Testing with curl (for debugging)

```bash
# Use websocat (install: npm install -g websocat)
websocat ws://localhost:8000/ws/chat
# Then type: {"query": "Show TVs"}
```

Or use Python:
```python
import websocket
import json

ws = websocket.WebSocket()
ws.connect("ws://localhost:8000/ws/chat")

ws.send(json.dumps({"query": "Show TVs"}))

while True:
    response = json.loads(ws.recv())
    print(f"[{response['type']}] {response['content'][:50]}...")
```

## Production Checklist

- [ ] Change localhost to actual backend URL
- [ ] Add connection timeout handling
- [ ] Implement auto-reconnect with exponential backoff
- [ ] Add message queuing if connection drops
- [ ] Handle very long answers (streaming)
- [ ] Add loading indicators for each status type
- [ ] Implement error recovery UI
- [ ] Test with slow connections
- [ ] Add CORS headers in backend if needed
- [ ] Use WSS (WebSocket Secure) in production
