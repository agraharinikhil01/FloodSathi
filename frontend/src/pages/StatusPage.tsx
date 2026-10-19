import React from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  Database,
  Server,
  RefreshCw,
  ShieldAlert,
  MapPin,
} from 'lucide-react'

interface AdapterStatusItem {
  name: string
  status: string
  cache_policy: string
  latency_ms?: number
  last_fetched?: string
  note?: string
}

interface SystemTelemetry {
  status: string
  app: string
  version: string
  database: string
  active_districts: number
  active_requests: number
  adapters: AdapterStatusItem[]
  timestamp: string
}

export const StatusPage: React.FC = () => {
  const { t } = useTranslation()

  const { data: telemetry, isFetching, refetch } = useQuery({
    queryKey: ['systemTelemetry'],
    queryFn: async () => {
      const res = await fetch('/api/v1/status/system')
      if (!res.ok) throw new Error('Failed to fetch system status')
      return res.json() as Promise<SystemTelemetry>
    },
    refetchInterval: 15000, // Poll every 15s
  })

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'live':
      case 'operational':
      case 'healthy':
        return 'bg-emerald-500/10 text-emerald-500'
      case 'cached':
        return 'bg-blue-500/10 text-blue-500'
      case 'fixture':
        return 'bg-amber-500/10 text-amber-500'
      default:
        return 'bg-gray-500/10 text-gray-400'
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-darkCard p-6 rounded-3xl border border-gray-200 dark:border-gray-800 shadow-sm">
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 text-xs font-semibold">
            <Activity className="w-3.5 h-3.5" />
            <span>Telemetry & Infrastructure Diagnostics</span>
          </div>
          <h1 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">
            {t('nav.status')}
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Real-time status of zero-key data adapters, SQLite WAL database, and caching fallbacks.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-2.5 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200 transition-colors shadow-sm self-start sm:self-auto"
          title="Refresh diagnostics"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin text-blue-500' : ''}`} />
        </button>
      </div>

      {/* System Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white dark:bg-darkCard rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-gray-400 text-xs font-bold uppercase">
            <span>Core System</span>
            <Server className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-lg font-black text-gray-900 dark:text-white capitalize">
            {telemetry?.status || 'Operational'}
          </div>
          <div className="text-[10px] text-gray-400">Version {telemetry?.version || '2.0.0'}</div>
        </div>

        <div className="p-4 bg-white dark:bg-darkCard rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-gray-400 text-xs font-bold uppercase">
            <span>Database</span>
            <Database className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-lg font-black text-gray-900 dark:text-white capitalize">
            {telemetry?.database || 'Connected'}
          </div>
          <div className="text-[10px] text-gray-400">SQLite (WAL Mode)</div>
        </div>

        <div className="p-4 bg-white dark:bg-darkCard rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-gray-400 text-xs font-bold uppercase">
            <span>Monitored Districts</span>
            <MapPin className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-lg font-black text-gray-900 dark:text-white">
            {telemetry?.active_districts || 10}
          </div>
          <div className="text-[10px] text-gray-400">5km resolution grids</div>
        </div>

        <div className="p-4 bg-white dark:bg-darkCard rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-gray-400 text-xs font-bold uppercase">
            <span>Open Requests</span>
            <ShieldAlert className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-lg font-black text-gray-900 dark:text-white">
            {telemetry?.active_requests ?? 0}
          </div>
          <div className="text-[10px] text-gray-400">Triage rescue queue</div>
        </div>
      </div>

      {/* External Adapters Connectivity Table */}
      <div className="bg-white dark:bg-darkCard rounded-3xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
          <div>
            <h3 className="font-extrabold text-sm text-gray-900 dark:text-white">
              Data Adapters & Upstream Health
            </h3>
            <p className="text-[11px] text-gray-400">
              Zero-key integrations with automatic disk caching and fixture fallback.
            </p>
          </div>
          <span className="text-[10px] font-bold uppercase px-2.5 py-1 bg-gray-100 dark:bg-darkMuted rounded-full text-gray-500">
            7 Active Sources
          </span>
        </div>

        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {(telemetry?.adapters || []).map((adapter) => (
            <div key={adapter.name} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-start sm:items-center space-x-3">
                <span className="flex h-2.5 w-2.5 relative mt-1 sm:mt-0">
                  <span
                    className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                      adapter.status === 'Live' ? 'bg-emerald-400' : 'bg-blue-400'
                    }`}
                  ></span>
                  <span
                    className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                      adapter.status === 'Live' ? 'bg-emerald-500' : 'bg-blue-500'
                    }`}
                  ></span>
                </span>
                <div>
                  <div className="font-bold text-xs text-gray-900 dark:text-white flex items-center space-x-2">
                    <span>{adapter.name}</span>
                    <span className="text-[10px] font-medium text-gray-400">({adapter.note})</span>
                  </div>
                  <div className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                    Policy: {adapter.cache_policy}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-4 self-end sm:self-auto text-xs">
                {adapter.latency_ms && (
                  <span className="text-[11px] text-gray-400 font-mono">
                    {adapter.latency_ms}ms
                  </span>
                )}
                <span
                  className={`px-2.5 py-0.5 rounded-full font-extrabold text-[10px] uppercase tracking-wider ${getStatusBadge(
                    adapter.status
                  )}`}
                >
                  {adapter.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
