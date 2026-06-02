import React from 'react';
import { 
  ScatterChart, Scatter, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';

/**
 * ChartBlock Component
 * 
 * Renders dynamic Recharts inside the chat window.
 * Supports: scatter, bar, and line charts based on the `chartType` field.
 */
const ChartBlock = ({ chartData }) => {
  if (!chartData || !chartData.data || chartData.data.length === 0) return null;

  const { chartType, title, xKey, yKey, data } = chartData;

  // Custom Tooltip for dark mode support and better UX
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-3 rounded-lg shadow-lg">
          <p className="font-semibold text-slate-800 dark:text-slate-100 mb-1">
            {payload[0].payload.model || label || 'Product'}
          </p>
          {payload.map((entry, index) => (
            <p key={`item-${index}`} className="text-sm" style={{ color: entry.color }}>
              <span className="capitalize">{entry.name.replace(/_/g, ' ')}: </span>
              <span className="font-mono">{entry.value}</span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const renderChart = () => {
    switch (chartType) {
      case 'scatter':
        return (
          <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
            <XAxis 
              type="number" 
              dataKey={xKey} 
              name={xKey.replace(/_/g, ' ')} 
              tick={{ fill: '#64748b' }} 
              domain={['auto', 'auto']}
            />
            <YAxis 
              type="number" 
              dataKey={yKey} 
              name={yKey.replace(/_/g, ' ')} 
              tick={{ fill: '#64748b' }} 
              domain={['auto', 'auto']}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            <Legend wrapperStyle={{ paddingTop: '20px' }}/>
            <Scatter 
              name={`${yKey.replace(/_/g, ' ')} vs ${xKey.replace(/_/g, ' ')}`} 
              data={data} 
              fill="#8b5cf6" 
            />
          </ScatterChart>
        );

      case 'line':
        return (
          <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
            <XAxis 
              dataKey={xKey} 
              tick={{ fill: '#64748b' }} 
            />
            <YAxis 
              tick={{ fill: '#64748b' }} 
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ paddingTop: '20px' }}/>
            <Line 
              type="monotone" 
              dataKey={yKey} 
              name={yKey.replace(/_/g, ' ')} 
              stroke="#3b82f6" 
              strokeWidth={3}
              activeDot={{ r: 8 }} 
            />
          </LineChart>
        );

      case 'bar':
      default:
        return (
          <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
            <XAxis 
              dataKey={xKey} 
              tick={{ fill: '#64748b' }} 
              // Hide labels if there are too many models
              tickFormatter={(value) => value.length > 15 ? value.substring(0, 15) + '...' : value}
            />
            <YAxis 
              tick={{ fill: '#64748b' }} 
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(148, 163, 184, 0.1)' }} />
            <Legend wrapperStyle={{ paddingTop: '20px' }}/>
            <Bar 
              dataKey={yKey} 
              name={yKey.replace(/_/g, ' ')} 
              fill="#3b82f6" 
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        );
    }
  };

  return (
    <div className="w-full mt-6 bg-white dark:bg-slate-800/80 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
      {title && (
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700/50 bg-slate-50/50 dark:bg-slate-800/50">
          <h3 className="font-semibold text-slate-800 dark:text-slate-100">
            {title}
          </h3>
        </div>
      )}
      <div className="p-4" style={{ width: '100%', height: 400 }}>
        <ResponsiveContainer>
          {renderChart()}
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ChartBlock;
