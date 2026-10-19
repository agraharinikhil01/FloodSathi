import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Map, AlertCircle, Users, Bell, Activity } from 'lucide-react'

export const BottomNav: React.FC = () => {
  const { t } = useTranslation()
  const location = useLocation()

  const tabs = [
    { to: '/', label: t('nav.map'), icon: Map },
    { to: '/help', label: t('nav.help'), icon: AlertCircle },
    { to: '/coordinator', label: t('nav.coordinator'), icon: Users },
    { to: '/alerts', label: t('nav.alerts'), icon: Bell },
    { to: '/status', label: t('nav.status'), icon: Activity },
  ]

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 dark:bg-darkCard/95 backdrop-blur-lg border-t border-gray-200 dark:border-gray-800 pb-safe shadow-[0_-4px_20px_rgba(0,0,0,0.06)]">
      <div className="grid grid-cols-5 h-16">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = location.pathname === tab.to
          return (
            <Link
              key={tab.to}
              to={tab.to}
              className={`flex flex-col items-center justify-center space-y-1 transition-colors ${
                isActive
                  ? 'text-blue-600 dark:text-brand-cyan font-bold'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
              }`}
            >
              <div className={`p-1 rounded-lg ${isActive ? 'bg-blue-50 dark:bg-blue-950/60' : ''}`}>
                <Icon className="w-5 h-5" />
              </div>
              <span className="text-[10px] tracking-tight">{tab.label}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
