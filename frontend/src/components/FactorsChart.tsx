import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

interface FactorsChartProps {
  factors: {
    rain_contrib: number
    discharge_contrib: number
    elevation_contrib: number
    population_contrib: number
  }
}

export const FactorsChart: React.FC<FactorsChartProps> = ({ factors }) => {
  const data = [
    { name: '48h Rain', value: Math.round(factors.rain_contrib * 100), color: '#3b82f6' },
    { name: 'Discharge', value: Math.round(factors.discharge_contrib * 100), color: '#06b6d4' },
    { name: 'Low Elevation', value: Math.round(factors.elevation_contrib * 100), color: '#eab308' },
    { name: 'Population', value: Math.round(factors.population_contrib * 100), color: '#a855f7' },
  ]

  return (
    <div className="p-4 bg-white dark:bg-darkCard rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500">
          Factor Contributions to Composite Risk
        </h4>
        <span className="text-[10px] text-gray-400">Total 100% Weight</span>
      </div>

      <div className="h-44 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
            <XAxis type="number" domain={[0, 50]} unit="%" tick={{ fontSize: 10, fill: '#94a3b8' }} />
            <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#94a3b8' }} width={80} />
            <Tooltip
              formatter={(val: any) => [`${val}% Contribution`, 'Impact']}
              contentStyle={{ backgroundColor: '#1e293b', borderRadius: '8px', border: 'none', color: '#fff', fontSize: '12px' }}
            />
            <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={16}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
