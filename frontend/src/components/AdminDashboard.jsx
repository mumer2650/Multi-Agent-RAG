import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-xl rounded-lg p-3">
        <p className="text-slate-500 dark:text-slate-400 text-sm font-medium mb-1">{label}</p>
        <p className="text-purple-600 dark:text-purple-400 font-bold text-lg">
          Score: {payload[0].value.toFixed(2)}
        </p>
      </div>
    );
  }
  return null;
};

/**
 * AdminDashboard Component
 * 
 * Purpose: Fetches and visualizes the latest RAGAS evaluation metrics from the backend.
 * Provides a high-level overview of the system's performance using Recharts.
 */
export default function AdminDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Document Ingestion State
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [uploadError, setUploadError] = useState(false);

  /**
   * Handles the file upload to the /ingest endpoint.
   */
  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadMessage('');
    setUploadError(false);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Send the POST request. The browser automatically sets the Content-Type with boundary.
      const response = await fetch('http://127.0.0.1:8000/ingest', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setUploadMessage(data.message || 'Document ingested successfully.');
        setSelectedFile(null);
        e.target.reset(); // Reset the file input visually
      } else {
        setUploadMessage(data.detail || 'Upload failed.');
        setUploadError(true);
      }
    } catch (err) {
      console.error("Upload error:", err);
      setUploadMessage('A network error occurred during upload.');
      setUploadError(true);
    } finally {
      setIsUploading(false);
    }
  };

  useEffect(() => {
    // Hardcoded metrics as requested to avoid backend link issues for now
    setMetrics({
      context_precision: 0.85,
      faithfulness: 0.92,
      answer_relevance: 0.88,
      timestamp: new Date().toLocaleString()
    });
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-xl text-slate-500 animate-pulse">Loading metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-xl text-red-500">Error: {error}</p>
      </div>
    );
  }

  // Map the raw JSON payload into an array format required by Recharts
  const chartData = [
    { name: 'Context Precision', score: metrics.context_precision },
    { name: 'Faithfulness', score: metrics.faithfulness },
    { name: 'Answer Relevance', score: metrics.answer_relevance },
  ];

  return (
    <div className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full animate-fade-in overflow-y-auto">
      <h2 className="text-3xl font-bold mb-8 text-slate-900 dark:text-white">MLOps Analytics</h2>
      
      {/* Top Grid: Split layout for Cards and Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6 w-full max-w-6xl mx-auto">
        
        {/* The Left Column (Vertical Cards) */}
        <div className="col-span-1 flex flex-col gap-6">
          {chartData.map((item) => (
            <div key={item.name} className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 transition-colors w-full">
              <h3 className="text-lg font-medium text-slate-500 dark:text-slate-400 mb-2">{item.name}</h3>
              <p className="text-4xl font-bold text-purple-600 dark:text-purple-400">
                {(item.score * 100).toFixed(1)}%
              </p>
            </div>
          ))}
        </div>

        {/* The Right Column (The Chart) */}
        <div className="col-span-1 lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 flex flex-col min-h-[350px]">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-semibold text-slate-900 dark:text-white">Evaluation Scores (RAGAS)</h3>
            <span className="text-sm font-medium text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-900/50 px-3 py-1 rounded-full">
              Last updated: {metrics.timestamp}
            </span>
          </div>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8' }} dy={10} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8' }} dx={-10} domain={[0, 1]} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} isAnimationActive={false} />
              <Bar dataKey="score" fill="#8b5cf6" radius={[6, 6, 0, 0]} maxBarSize={110} animationDuration={1500} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* The Bottom Row (Document Ingestion) */}
      <div className="w-full max-w-6xl mx-auto">
        <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 transition-colors w-full">
          <h3 className="text-xl font-semibold mb-4 text-slate-900 dark:text-white">Knowledge Base Ingestion</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
            Upload new appliance manuals (PDF) to chunk and add them to the vector indexes.
          </p>
          
          <form onSubmit={handleFileUpload} className="flex flex-col sm:flex-row items-center gap-4">
            <input 
              type="file" 
              onChange={(e) => setSelectedFile(e.target.files[0])}
              className="block w-full text-sm text-slate-500 dark:text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-100 file:text-purple-700 hover:file:bg-purple-200 dark:file:bg-slate-700 dark:file:text-purple-400 dark:hover:file:bg-slate-600 transition-colors cursor-pointer"
            />
            <button 
              type="submit" 
              disabled={!selectedFile || isUploading}
              className="px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-400 dark:disabled:bg-slate-600 text-white rounded-full font-medium transition-colors shadow-sm whitespace-nowrap"
            >
              {isUploading ? 'Ingesting...' : 'Upload Document'}
            </button>
          </form>

          {uploadMessage && (
            <div className={`mt-4 text-sm font-medium px-4 py-2 rounded-lg ${uploadError ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400' : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400'}`}>
              {uploadMessage}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
