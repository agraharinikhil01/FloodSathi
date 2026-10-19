import React from 'react'
import { AlertTriangle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAppStore } from '../lib/store'

export const SosButton: React.FC = () => {
  const { t } = useTranslation()
  const { setSosOpen } = useAppStore()

  return (
    <div className="fixed bottom-20 md:bottom-8 right-4 md:right-8 z-40">
      <button
        onClick={() => setSosOpen(true)}
        className="group relative flex items-center space-x-2.5 px-5 py-3.5 rounded-full bg-gradient-to-r from-red-600 to-rose-600 text-white font-extrabold text-sm shadow-xl shadow-red-500/30 hover:shadow-red-500/50 hover:scale-105 active:scale-95 transition-all duration-200"
      >
        <div className="relative">
          <AlertTriangle className="w-5 h-5 animate-bounce" />
          <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-yellow-300"></span>
          </span>
        </div>
        <span className="tracking-wide uppercase">{t('actions.sos')}</span>
      </button>
    </div>
  )
}
