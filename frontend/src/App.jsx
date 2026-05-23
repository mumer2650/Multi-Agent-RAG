import React from 'react';
import Home from './pages/Home';
import './index.css';

/**
 * App Component
 * 
 * Purpose: The root component of the React application. It currently renders the 
 * main Home page which encapsulates the SAGE chat interface layout.
 */
function App() {
  return (
    <React.Fragment>
      <Home />
    </React.Fragment>
  );
}

export default App;
