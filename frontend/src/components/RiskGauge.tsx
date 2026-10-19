import React from 'react'
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts'

interface RiskGaugeProps {
  score: number // 0.0 to 1.0
  level: string
  isOverridden?: boolean
  officialBadge?: string | null
}

const LEVEL_COLORS: Record<string, string> = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#f97316',
  severe: '#ef4444',
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({ score, level, isOverridden, officialBadge }) => {
  const percentage = Math.round(score * 100)
  const activeColor = LEVEL_COLORS[level.toLowerCase()] || '#3b82f6'

  const data = [
    {
      name: 'Risk',
      value: percentage,
      fill: activeColor,
    },
  ]

  return (
    <div className="flex flex-col items-center justify-center p-4 bg-white dark:bg-darkCard rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm relative">
      <div className="w-48 h-40 relative flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="70%"
            outerRadius="100%"
            barSize={12}
            data={data}
            startAngle={180}
            endAngle={0}
          >
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              angleAxisId={0}
              tick={false}
            />
            <RadialBar
              background={{ fill: '#334155', opacity: 0.15 }}
              dataKey="value"
              cornerRadius={8}
            />
          </RadialBarChart>
        </ResponsiveContainer>

        {/* Center Text */}
        <div className="absolute top-[42%] flex flex-col items-center">
          <span className="text-3xl font-black text-gray-900 dark:text-white tracking-tight">
            {percentage}%
          </span>
          <span
            className="text-[11px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full text-white mt-1"
            style={{ backgroundColor: activeColor }}
          >
            {level}
          </span>
        </div>
      </div>

      {isOverridden && (
        <div className="mt-1 flex items-center space-x-1.5 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-[11px] font-bold">
          <span>⚠️ Official {officialBadge || 'NDMA'} Alert Override</span>
        </div>
      )}
    </div>
  )
}
