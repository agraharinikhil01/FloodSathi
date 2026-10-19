import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Send,
  RefreshCw,
  PlusCircle,
  Radio,
  CheckCircle2,
  Loader2,
  Volume2,
} from 'lucide-react'
import { useAppStore } from '../lib/store'

interface AlertItem {
  id: number
  district: string
  level: string
  message_en: string
  message_hi: string
  channel: string
  source: string
  identifier: string
  sent_at: string
}

interface BroadcastResult {
  status: string
  mock: boolean
  alert_id: number
  channel: string
  dispatched_count: number
  delivery_rate: string
  timestamp: string
  message: string
}

export const AlertsPage: React.FC = () => {
  const { t } = useTranslation()
  const { selectedDistrict } = useAppStore()
  const queryClient = useQueryClient()

  const [broadcastLog, setBroadcastLog] = useState<BroadcastResult | null>(null)
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const [targetDistrict, setTargetDistrict] = useState(selectedDistrict || 'Patna')
  const [alertLevel, setAlertLevel] = useState<'severe' | 'high' | 'medium'>('severe')

  // Fetch alerts list
  const { data: alerts = [], isFetching, refetch } = useQuery({
    queryKey: ['alerts'],
    queryFn: async () => {
      const res = await fetch('/api/v1/alerts')
      if (!res.ok) throw new Error('Failed to fetch alerts')
      return res.json() as Promise<AlertItem[]>
    },
  })

  // Generate Alert Mutation
  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/alerts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          district: targetDistrict,
          level: alertLevel,
          channel: 'all',
        }),
      })
      if (!res.ok) throw new Error('Failed to generate alert')
      return res.json()
    },
    onSuccess: () => {
      setShowGenerateModal(false)
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  // Broadcast Mutation
  const broadcastMutation = useMutation({
    mutationFn: async (alertId: number) => {
      const res = await fetch(`/api/v1/alerts/${alertId}/broadcast?channel=all`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error('Broadcast failed')
      return res.json() as Promise<BroadcastResult>
    },
    onSuccess: (data) => {
      setBroadcastLog(data)
    },
  })

  const getLevelBorder = (level: string) => {
    switch (level.toLowerCase()) {
      case 'severe':
        return 'border-l-red-500 bg-red-500/5'
      case 'high':
        return 'border-l-orange-500 bg-orange-500/5'
      default:
        return 'border-l-yellow-500 bg-yellow-500/5'
    }
  }

  const getLevelBadge = (level: string) => {
    switch (level.toLowerCase()) {
      case 'severe':
        return 'bg-red-600 text-white'
      case 'high':
        return 'bg-orange-500 text-white'
      default:
        return 'bg-yellow-500 text-white'
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-darkCard p-6 rounded-3xl border border-gray-200 dark:border-gray-800 shadow-sm">
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-red-50 dark:bg-red-950/60 text-red-600 dark:text-red-400 text-xs font-semibold">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            <span>NDMA SACHET Feeds & Bilingual Broadcaster</span>
          </div>
          <h1 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">
            {t('nav.alerts')}
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Real-time CAP XML warnings from official authorities and AI advisory synthesizer.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2.5 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200 transition-colors shadow-sm"
            title="Refresh alerts"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin text-blue-500' : ''}`} />
          </button>

          <button
            onClick={() => setShowGenerateModal(true)}
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md transition-all active:scale-95"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Generate New Advisory</span>
          </button>
        </div>
      </div>

      {/* Broadcast Simulation Feedback Banner */}
      {broadcastLog && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between animate-in fade-in duration-300">
          <div className="flex items-center space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
            <div className="text-xs">
              <span className="font-extrabold text-emerald-700 dark:text-emerald-400">
                Mock Broadcast Sent: {broadcastLog.dispatched_count} recipients (Delivery: {broadcastLog.delivery_rate})
              </span>
              <p className="text-gray-500 dark:text-gray-400 text-[11px]">{broadcastLog.message}</p>
            </div>
          </div>
          <button
            onClick={() => setBroadcastLog(null)}
            className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Alerts Feed */}
      <div className="space-y-4">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`p-6 rounded-2xl border-l-4 bg-white dark:bg-darkCard border border-gray-200 dark:border-gray-800 shadow-sm space-y-4 ${getLevelBorder(
              alert.level
            )}`}
          >
            {/* Header info */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 dark:border-gray-800 pb-3">
              <div className="flex items-center space-x-2.5">
                <span
                  className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${getLevelBadge(
                    alert.level
                  )}`}
                >
                  {alert.level} Risk
                </span>
                <span className="font-extrabold text-xs text-gray-900 dark:text-white">
                  {alert.district} • {alert.source}
                </span>
                <span className="text-[11px] text-gray-400 font-medium">
                  ID: {alert.identifier}
                </span>
              </div>

              <span className="text-[11px] text-gray-400">
                {new Date(alert.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            {/* Bilingual messages (max 160 chars) */}
            <div className="space-y-2">
              <div className="p-3 bg-gray-50 dark:bg-darkMuted/60 rounded-xl space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-blue-600 dark:text-brand-cyan">
                  English Broadcast ({alert.message_en.length}/160 chars):
                </div>
                <p className="text-xs font-semibold text-gray-900 dark:text-white">
                  {alert.message_en}
                </p>
              </div>

              <div className="p-3 bg-gray-50 dark:bg-darkMuted/60 rounded-xl space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                  हिन्दी प्रसारण ({alert.message_hi.length}/160 chars):
                </div>
                <p className="text-xs font-semibold text-gray-800 dark:text-gray-200">
                  {alert.message_hi}
                </p>
              </div>
            </div>

            {/* Mock Broadcast Dispatch Button */}
            <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-800 text-xs">
              <div className="flex items-center space-x-1.5 text-gray-400">
                <Volume2 className="w-3.5 h-3.5" />
                <span>Target Channel: <b className="capitalize text-gray-600 dark:text-gray-300">{alert.channel}</b></span>
              </div>

              <button
                onClick={() => broadcastMutation.mutate(alert.id)}
                disabled={broadcastMutation.isPending}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-darkMuted hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 font-bold transition-all shadow-sm active:scale-95 disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5 text-blue-500" />
                <span>Simulate Broadcast (MOCK)</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Generate Alert Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-darkCard p-6 rounded-3xl max-w-md w-full border border-gray-200 dark:border-gray-800 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
              <h3 className="font-extrabold text-base text-gray-900 dark:text-white">
                Generate Emergency Advisory
              </h3>
              <button
                onClick={() => setShowGenerateModal(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-600 dark:text-gray-400 mb-1">
                  Target District
                </label>
                <input
                  type="text"
                  value={targetDistrict}
                  onChange={(e) => setTargetDistrict(e.target.value)}
                  className="w-full p-3 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted text-gray-900 dark:text-white text-xs font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-600 dark:text-gray-400 mb-1">
                  Severity Level
                </label>
                <select
                  value={alertLevel}
                  onChange={(e) => setAlertLevel(e.target.value as any)}
                  className="w-full p-3 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted text-gray-900 dark:text-white text-xs font-semibold"
                >
                  <option value="severe">Severe Risk (Immediate Evacuation)</option>
                  <option value="high">High Risk (Pre-Evacuation Warning)</option>
                  <option value="medium">Medium Risk (General Advisory)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-3 border-t border-gray-100 dark:border-gray-800">
              <button
                onClick={() => setShowGenerateModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-extrabold shadow-md flex items-center space-x-1.5 disabled:opacity-50"
              >
                {generateMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Generate & Save</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
