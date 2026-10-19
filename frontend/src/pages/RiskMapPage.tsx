import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  ShieldCheck,
  CloudRain,
  Waves,
  AlertTriangle,
  Compass,
  Building,
  RefreshCw,
  Info,
  MapPin,
  Search,
  X,
  Loader2,
  Droplets,
  Wind,
} from 'lucide-react'
import { useAppStore } from '../lib/store'
import { InteractiveRiskMap } from '../components/InteractiveRiskMap'
import { RiskGauge } from '../components/RiskGauge'
import { FactorsChart } from '../components/FactorsChart'

export const RiskMapPage: React.FC = () => {
  const { t, i18n } = useTranslation()
  const { selectedDistrict, setSelectedDistrict } = useAppStore()

  const [searchInput, setSearchInput] = useState('')
  const [isOpenSuggestions, setIsOpenSuggestions] = useState(false)
  const [activeLocationParams, setActiveLocationParams] = useState<{
    lat?: number
    lon?: number
    state?: string
    district?: string
  } | null>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Fetch districts list
  const { data: districts = [] } = useQuery({
    queryKey: ['districts', i18n.language],
    queryFn: async () => {
      const res = await fetch(`/api/v1/risk/districts?lang=${i18n.language}`)
      if (!res.ok) throw new Error('Failed to fetch districts')
      return res.json()
    },
  })

  // Live Location Suggestions Query across India
  const { data: suggestions = [], isFetching: isSearchingSuggestions } = useQuery({
    queryKey: ['locationSuggestions', searchInput],
    queryFn: async () => {
      if (!searchInput || searchInput.trim().length < 2) return []
      const res = await fetch(`/api/v1/risk/suggestions?q=${encodeURIComponent(searchInput.trim())}`)
      if (!res.ok) return []
      return res.json()
    },
    enabled: searchInput.trim().length >= 2,
    staleTime: 30000,
  })

  // Click-outside listener to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node)) {
        setIsOpenSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Fetch active district risk details (with exact coords if selected from suggestions)
  const { data: districtRisk, refetch, isFetching } = useQuery({
    queryKey: ['districtRisk', selectedDistrict, activeLocationParams, i18n.language],
    queryFn: async () => {
      let url = `/api/v1/risk/district/${encodeURIComponent(selectedDistrict)}?lang=${i18n.language}`
      if (activeLocationParams?.lat != null && activeLocationParams?.lon != null) {
        url += `&lat=${activeLocationParams.lat}&lon=${activeLocationParams.lon}`
        if (activeLocationParams.state) url += `&state=${encodeURIComponent(activeLocationParams.state)}`
        if (activeLocationParams.district) url += `&district=${encodeURIComponent(activeLocationParams.district)}`
      }
      const res = await fetch(url)
      if (!res.ok) throw new Error('Failed to fetch district risk')
      return res.json()
    },
  })

  const handleSelectSuggestion = (suggestion: {
    name: string
    district: string
    state: string
    lat: number
    lon: number
    display_name: string
  }) => {
    setSelectedDistrict(suggestion.name)
    setActiveLocationParams({
      lat: suggestion.lat,
      lon: suggestion.lon,
      state: suggestion.state,
      district: suggestion.district,
    })
    setSearchInput(`${suggestion.name}${suggestion.district ? ` (${suggestion.district})` : ''}`)
    setIsOpenSuggestions(false)
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchInput.trim()) return
    setSelectedDistrict(searchInput.trim())
    setActiveLocationParams(null)
    setIsOpenSuggestions(false)
  }

  const risk = districtRisk?.risk
  const metrics = risk?.metrics
  const factors = risk?.factors
  const facilities = districtRisk?.facilities_summary

  const centerCoords: [number, number] = districtRisk?.district?.centroid
    ? [districtRisk.district.centroid.lat, districtRisk.district.centroid.lon]
    : [25.5941, 85.1376]

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Top Banner & District Dropdown */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-darkCard p-6 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm">
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-brand-cyan text-xs font-semibold">
            <Compass className="w-3.5 h-3.5" />
            <span>Interactive Multi-Factor Decision Support</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
            <span>{t('risk.title')}</span>
            {districtRisk?.district && (
              <span className="text-sm font-bold text-blue-600 dark:text-brand-cyan px-2.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-900">
                {districtRisk.district.name} • {districtRisk.district.state}
              </span>
            )}
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Open-Meteo 48h rain + discharge, SRTM 90m terrain, MapTiler HD tiles & NDMA SACHET alert override.
          </p>
        </div>

        {/* Search with Live Suggestions Dropdown & District Selector */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 relative">
          {/* Custom Search Any Indian City/Village with Suggestions */}
          <div className="relative" ref={suggestionsRef}>
            <form onSubmit={handleSearchSubmit} className="flex items-center space-x-1.5">
              <div className="relative w-64 md:w-80">
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => {
                    setSearchInput(e.target.value)
                    setIsOpenSuggestions(true)
                  }}
                  onFocus={() => {
                    if (searchInput.trim().length >= 2) setIsOpenSuggestions(true)
                  }}
                  placeholder="Type any place (e.g. Katai, Sant Kabir Nagar)..."
                  className="w-full bg-gray-50 dark:bg-darkMuted border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white text-xs font-semibold rounded-xl py-2 pl-8 pr-7 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                />
                <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5 pointer-events-none" />
                {searchInput && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchInput('')
                      setIsOpenSuggestions(false)
                    }}
                    className="absolute right-2 top-2 p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              <button
                type="submit"
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm shrink-0"
              >
                Search
              </button>
            </form>

            {/* Suggestions Dropdown Popup */}
            {isOpenSuggestions && searchInput.trim().length >= 2 && (
              <div className="absolute top-full left-0 w-80 md:w-96 mt-1.5 bg-white dark:bg-darkCard rounded-2xl border border-gray-200 dark:border-gray-700 shadow-2xl overflow-hidden z-50">
                <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-800 bg-gray-50/70 dark:bg-darkMuted/60 flex items-center justify-between text-[11px] font-bold text-gray-500 dark:text-gray-400">
                  <span>Locations matching "{searchInput}"</span>
                  {isSearchingSuggestions && <Loader2 className="w-3 h-3 animate-spin text-blue-500" />}
                </div>

                <div className="max-h-72 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800/60">
                  {isSearchingSuggestions && suggestions.length === 0 ? (
                    <div className="p-4 text-center text-xs text-gray-400">
                      Searching locations across India...
                    </div>
                  ) : suggestions.length > 0 ? (
                    suggestions.map((s: any, idx: number) => (
                      <button
                        key={`${s.lat}-${s.lon}-${idx}`}
                        type="button"
                        onClick={() => handleSelectSuggestion(s)}
                        className="w-full text-left p-3 hover:bg-blue-50 dark:hover:bg-blue-950/40 transition-colors flex items-start space-x-2.5 group"
                      >
                        <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-brand-cyan group-hover:scale-105 transition-transform mt-0.5 shrink-0">
                          <MapPin className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-black text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-brand-cyan transition-colors truncate">
                              {s.name}
                            </span>
                            <span className="text-[10px] text-gray-400 font-mono ml-1 shrink-0">
                              {s.lat.toFixed(2)}°, {s.lon.toFixed(2)}°
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 mt-1 text-[11px] flex-wrap">
                            <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-medium">
                              District: <strong className="font-bold text-gray-900 dark:text-white">{s.district || 'N/A'}</strong>
                            </span>
                            <span className="text-gray-400">•</span>
                            <span className="px-1.5 py-0.5 rounded bg-blue-100/70 dark:bg-blue-950/70 text-blue-700 dark:text-blue-300 font-medium">
                              State: <strong className="font-bold text-blue-800 dark:text-blue-200">{s.state || 'India'}</strong>
                            </span>
                          </div>
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="p-4 text-center">
                      <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                        No direct match found for "{searchInput}"
                      </p>
                      <p className="text-[11px] text-gray-400 mt-1">
                        Click 'Search' to locate directly via geocoder.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Preset Select Dropdown */}
          <div className="relative">
            <select
              value={selectedDistrict}
              onChange={(e) => {
                setSelectedDistrict(e.target.value)
                setActiveLocationParams(null)
                setSearchInput('')
              }}
              aria-label="Select target district"
              className="appearance-none bg-gray-50 dark:bg-darkMuted border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white text-xs font-bold rounded-xl py-2 pl-3 pr-8 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-sm"
            >
              <option value={selectedDistrict}>{selectedDistrict} (Active)</option>
              {districts.map((d: any) => (
                <option key={d.id} value={d.name}>
                  {d.name} ({d.state}) {d.has_official_alert ? '🚨' : ''}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-400">
              ▼
            </div>
          </div>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200 transition-colors shadow-sm disabled:opacity-50"
            title="Refresh district data"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin text-blue-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* Official Alert Banner if Active */}
      {risk?.is_overridden && risk.official_alert && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-red-600/15 via-rose-600/10 to-red-600/15 border border-red-500/30 flex items-start space-x-3 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5 animate-pulse" />
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-red-600 text-white tracking-wider">
                Official {risk.official_alert.source} Alert • {risk.official_alert.level}
              </span>
              <span className="text-[11px] text-red-600/80 dark:text-red-400 font-semibold">
                ID: {risk.official_alert.identifier}
              </span>
            </div>
            <p className="text-xs font-bold text-gray-900 dark:text-white">
              {i18n.language === 'hi' ? risk.official_alert.message_hi : risk.official_alert.message_en}
            </p>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              Note: This official advisory overrides the local numerical score on the map.
            </p>
          </div>
        </div>
      )}

      {/* Primary Grid Layout: Map & Risk Gauge */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Interactive Map */}
        <div className="lg:col-span-2 space-y-4">
          <InteractiveRiskMap
            center={centerCoords}
            gridPoints={districtRisk?.grid_points || []}
            districtName={selectedDistrict}
          />

          {/* Live OpenWeatherMap Observation Widget */}
          {districtRisk?.live_weather && (
            <div className="p-4 bg-gradient-to-r from-blue-500/10 via-cyan-500/5 to-transparent dark:from-blue-950/40 dark:via-cyan-950/20 dark:to-transparent rounded-2xl border border-blue-500/20 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in fade-in duration-300">
              <div className="flex items-center space-x-3.5">
                <div className="relative">
                  {districtRisk.live_weather.icon ? (
                    <img
                      src={`https://openweathermap.org/img/wn/${districtRisk.live_weather.icon}@2x.png`}
                      alt={districtRisk.live_weather.description}
                      className="w-12 h-12 object-contain filter drop-shadow"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center text-blue-500">
                      <CloudRain className="w-6 h-6" />
                    </div>
                  )}
                  <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-500 rounded-full ring-2 ring-white dark:ring-darkCard animate-pulse" />
                </div>

                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xl font-black text-gray-900 dark:text-white">
                      {districtRisk.live_weather.temp_c}°C
                    </span>
                    <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 capitalize">
                      {districtRisk.live_weather.description}
                    </span>
                  </div>
                  <div className="text-[11px] text-gray-400 flex items-center space-x-2">
                    <span>Feels like <b>{districtRisk.live_weather.feels_like_c}°C</b></span>
                    <span>•</span>
                    <span>Station: <b>{districtRisk.live_weather.city_name || selectedDistrict}</b></span>
                  </div>
                </div>
              </div>

              {/* Weather Attributes Pills */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <div className="px-2.5 py-1.5 rounded-xl bg-white dark:bg-darkCard border border-gray-200 dark:border-gray-800 flex items-center space-x-1.5 shadow-xs">
                  <Droplets className="w-3.5 h-3.5 text-blue-500" />
                  <span className="text-gray-500">Humidity:</span>
                  <span className="font-bold text-gray-900 dark:text-white">{districtRisk.live_weather.humidity_pct}%</span>
                </div>

                <div className="px-2.5 py-1.5 rounded-xl bg-white dark:bg-darkCard border border-gray-200 dark:border-gray-800 flex items-center space-x-1.5 shadow-xs">
                  <Wind className="w-3.5 h-3.5 text-cyan-500" />
                  <span className="text-gray-500">Wind:</span>
                  <span className="font-bold text-gray-900 dark:text-white">{districtRisk.live_weather.wind_speed_kmh} km/h</span>
                </div>

                <div className="px-2.5 py-1.5 rounded-xl bg-white dark:bg-darkCard border border-gray-200 dark:border-gray-800 flex items-center space-x-1.5 shadow-xs">
                  <CloudRain className="w-3.5 h-3.5 text-indigo-500" />
                  <span className="text-gray-500">Rain 48h:</span>
                  <span className="font-bold text-indigo-600 dark:text-indigo-400">{districtRisk.live_weather.rain_48h_mm} mm</span>
                </div>

                <div className="hidden sm:inline-flex items-center space-x-1 px-2 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 text-[10px] font-bold border border-emerald-500/20">
                  <span>OpenWeather</span>
                </div>
              </div>
            </div>
          )}

          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-white dark:bg-darkCard rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
              <div className="flex items-center justify-between text-gray-500 text-xs font-semibold">
                <span>Rain 48h</span>
                <CloudRain className="w-4 h-4 text-blue-500" />
              </div>
              <div className="mt-2 text-lg font-black text-gray-900 dark:text-white">
                {metrics?.avg_rain_48h_mm ?? 0} <span className="text-xs font-normal text-gray-400">mm</span>
              </div>
            </div>

            <div className="p-3 bg-white dark:bg-darkCard rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
              <div className="flex items-center justify-between text-gray-500 text-xs font-semibold">
                <span>Discharge</span>
                <Waves className="w-4 h-4 text-cyan-500" />
              </div>
              <div className="mt-2 text-lg font-black text-gray-900 dark:text-white">
                {metrics?.avg_river_discharge_m3s ?? 0} <span className="text-xs font-normal text-gray-400">m³/s</span>
              </div>
            </div>

            <div className="p-3 bg-white dark:bg-darkCard rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
              <div className="flex items-center justify-between text-gray-500 text-xs font-semibold">
                <span>Shelters</span>
                <ShieldCheck className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="mt-2 text-lg font-black text-gray-900 dark:text-white">
                {facilities?.shelters ?? 0} <span className="text-xs font-normal text-gray-400">Ready</span>
              </div>
            </div>

            <div className="p-3 bg-white dark:bg-darkCard rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
              <div className="flex items-center justify-between text-gray-500 text-xs font-semibold">
                <span>Hospitals</span>
                <Building className="w-4 h-4 text-purple-500" />
              </div>
              <div className="mt-2 text-lg font-black text-gray-900 dark:text-white">
                {facilities?.hospitals ?? 0} <span className="text-xs font-normal text-gray-400">Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Risk Gauge & Factor Breakdown */}
        <div className="space-y-4">
          <RiskGauge
            score={risk?.raw_score || 0}
            level={risk?.level || 'Low'}
            isOverridden={risk?.is_overridden}
            officialBadge={risk?.official_badge}
          />

          {factors && <FactorsChart factors={factors} />}

          {/* Explanation Box */}
          <div className="p-4 bg-white dark:bg-darkCard rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-2">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-gray-700 dark:text-gray-300">
              <Info className="w-3.5 h-3.5 text-blue-500" />
              <span>Assessment Reason</span>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              {risk?.explanation || 'Loading assessment explanation...'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
