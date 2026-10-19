import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Droplets, Sun, Moon, Globe, User } from 'lucide-react'
import { useAppStore } from '../lib/store'

export const Header: React.FC = () => {
  const { t, i18n } = useTranslation()
  const { theme, toggleTheme, userToken, userRole, setUserAuth } = useAppStore()
  const location = useLocation()

  const toggleLanguage = () => {
    const nextLang = i18n.language === 'en' ? 'hi' : 'en'
    i18n.changeLanguage(nextLang)
  }

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-white/80 dark:bg-darkBg/80 border-b border-gray-200 dark:border-gray-800 transition-colors">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center space-x-2.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-blue to-brand-cyan flex items-center justify-center shadow-lg shadow-brand-blue/20">
            <Droplets className="w-6 h-6 text-white" />
          </div>
          <div>
            <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-blue-600 via-brand-blue to-brand-cyan bg-clip-text text-transparent">
              {t('app.name')}
            </span>
            <div className="text-[10px] uppercase font-semibold tracking-wider text-gray-500 dark:text-gray-400">
              India Disaster AI
            </div>
          </div>
        </Link>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center space-x-1 lg:space-x-3 text-sm font-medium">
          <Link
            to="/"
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              location.pathname === '/'
                ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-darkCard'
            }`}
          >
            {t('nav.map')}
          </Link>
          <Link
            to="/help"
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              location.pathname === '/help'
                ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-darkCard'
            }`}
          >
            {t('nav.help')}
          </Link>
          <Link
            to="/coordinator"
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              location.pathname === '/coordinator'
                ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-darkCard'
            }`}
          >
            {t('nav.coordinator')}
          </Link>
          <Link
            to="/alerts"
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              location.pathname === '/alerts'
                ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-darkCard'
            }`}
          >
            {t('nav.alerts')}
          </Link>
          <Link
            to="/status"
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              location.pathname === '/status'
                ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-darkCard'
            }`}
          >
            {t('nav.status')}
          </Link>
        </nav>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 dark:bg-darkCard text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
            title="Toggle Hindi/English"
          >
            <Globe className="w-3.5 h-3.5 text-blue-500" />
            <span>{i18n.language === 'en' ? 'हिन्दी' : 'EN'}</span>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg bg-gray-100 dark:bg-darkCard text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
          </button>

          {/* Auth Button */}
          {userToken ? (
            <button
              onClick={() => setUserAuth(null, null)}
              className="hidden md:flex items-center space-x-1 text-xs px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500/20 font-semibold"
            >
              <span>{userRole || 'User'}</span>
              <span>•</span>
              <span>{t('nav.logout')}</span>
            </button>
          ) : (
            <Link
              to="/login"
              className="hidden md:flex items-center space-x-1.5 text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-semibold shadow-sm transition-colors"
            >
              <User className="w-3.5 h-3.5" />
              <span>{t('nav.login')}</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
