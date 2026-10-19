import React from 'react'
import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { BottomNav } from './BottomNav'
import { SosButton } from './SosButton'
import { SosModal } from './SosModal'
import { useTranslation } from 'react-i18next'
import { Info } from 'lucide-react'

export const Layout: React.FC = () => {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen flex flex-col bg-lightBg dark:bg-darkBg text-slate-900 dark:text-slate-100 transition-colors duration-200">
      <Header />

      {/* Official Disclaimer Banner */}
      <div className="bg-amber-500/10 dark:bg-amber-500/15 border-b border-amber-500/20 px-4 py-1.5 text-center text-xs font-medium text-amber-800 dark:text-amber-300 flex items-center justify-center space-x-1.5">
        <Info className="w-3.5 h-3.5 shrink-0" />
        <span>{t('app.disclaimer')}</span>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 pb-24 md:pb-8">
        <Outlet />
      </main>

      {/* SOS Floating Action & Modal */}
      <SosButton />
      <SosModal />

      {/* Mobile Bottom Navigation */}
      <BottomNav />
    </div>
  )
}
