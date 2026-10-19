import React, { useState } from 'react'
import { AlertTriangle, X, Sparkles, CheckCircle2, PhoneCall, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../lib/store'

export const SosModal: React.FC = () => {
  const { t } = useTranslation()
  const { isSosOpen, setSosOpen, selectedDistrict } = useAppStore()
  const queryClient = useQueryClient()
  const [distressMessage, setDistressMessage] = useState('')
  const [successResponse, setSuccessResponse] = useState<any>(null)

  const quickAlertTemplates = [
    'Emergency! Water level rising rapidly on ground floor, 4 trapped on roof.',
    'Urgent medical required: pregnant woman in active labor, need boat.',
    'Senior citizen stranded without heart medication and drinking water.',
  ]

  const sosMutation = useMutation({
    mutationFn: async (text: string) => {
      const res = await fetch('/api/v1/triage/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          district: selectedDistrict || 'Patna',
        }),
      })
      if (!res.ok) throw new Error('SOS triage submission failed')
      return res.json()
    },
    onSuccess: (data) => {
      setSuccessResponse(data)
      queryClient.invalidateQueries({ queryKey: ['coordinatorRequests'] })
    },
  })

  if (!isSosOpen) return null

  const handleClose = () => {
    setSosOpen(false)
    setDistressMessage('')
    setSuccessResponse(null)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!distressMessage.trim()) return
    sosMutation.mutate(distressMessage)
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-white dark:bg-darkCard w-full max-w-lg rounded-3xl border border-red-500/40 shadow-2xl p-6 space-y-5 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-red-600 text-white animate-pulse">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-black text-lg text-red-600 dark:text-red-400 uppercase tracking-tight">
                {t('actions.sos')} Rescue Trigger
              </h3>
              <p className="text-[11px] text-gray-500 dark:text-gray-400">
                Direct high-priority dispatch to NDRF / SDRF volunteer rescue teams.
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Success View */}
        {successResponse ? (
          <div className="space-y-4 py-2">
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 space-y-2">
              <div className="flex items-center space-x-2 text-emerald-600 dark:text-emerald-400 font-extrabold text-sm">
                <CheckCircle2 className="w-5 h-5" />
                <span>SOS Signal #{successResponse.id} Transmitted!</span>
              </div>
              <p className="text-xs text-gray-700 dark:text-gray-300">
                Your coordinates have been locked and broadcast to nearby rescue units with <b>{successResponse.urgency.toUpperCase()}</b> priority.
              </p>
            </div>

            <div className="p-4 bg-gray-50 dark:bg-darkMuted rounded-2xl space-y-2 text-xs">
              <div className="flex justify-between text-gray-500">
                <span>Extracted Need:</span>
                <b className="text-gray-900 dark:text-white capitalize">{successResponse.need}</b>
              </div>
              <div className="flex justify-between text-gray-500">
                <span>People Count:</span>
                <b className="text-gray-900 dark:text-white">{successResponse.people_count} Individual(s)</b>
              </div>
              <div className="flex justify-between text-gray-500">
                <span>Location:</span>
                <b className="text-gray-900 dark:text-white">{successResponse.location_text || selectedDistrict}</b>
              </div>
            </div>

            <div className="flex items-center space-x-2 p-3 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 text-xs font-semibold">
              <PhoneCall className="w-4 h-4 shrink-0" />
              <span>Emergency Helpline: <b>1077</b> (State Disaster Management)</span>
            </div>

            <button
              onClick={handleClose}
              className="w-full py-3 rounded-xl bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-bold text-xs"
            >
              Done / Close
            </button>
          </div>
        ) : (
          /* Form View */
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 mb-1.5">
                Location & Urgent Situation (स्थान और तत्काल स्थिति):
              </label>
              <textarea
                rows={3}
                value={distressMessage}
                onChange={(e) => setDistressMessage(e.target.value)}
                placeholder="e.g. हम 5 लोग छत पर फंसे हैं, पानी गले तक है, तुरंत नाव भेजो बोरिंग रोड पटना।"
                className="w-full p-3.5 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted text-gray-900 dark:text-white text-xs leading-relaxed focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>

            {/* Quick Templates */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Quick Emergency Presets:
              </span>
              <div className="space-y-1.5">
                {quickAlertTemplates.map((template, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setDistressMessage(template)}
                    className="w-full text-left p-2 rounded-xl bg-gray-50 dark:bg-darkMuted hover:bg-red-50 dark:hover:bg-red-950/30 border border-gray-200 dark:border-gray-700 text-[11px] text-gray-700 dark:text-gray-300 transition-colors truncate"
                  >
                    • {template}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={sosMutation.isPending || !distressMessage.trim()}
              className="w-full py-3.5 rounded-xl bg-gradient-to-r from-red-600 via-rose-600 to-red-600 hover:from-red-700 hover:to-rose-700 text-white font-black text-xs uppercase tracking-wider shadow-xl shadow-red-500/30 flex items-center justify-center space-x-2 disabled:opacity-50 transition-all active:scale-98"
            >
              {sosMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Transmitting SOS Coordinates...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>TRANSMIT SOS SIGNAL NOW</span>
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
