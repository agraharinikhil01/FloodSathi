import React, { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useAppStore } from '../lib/store'
import { CloudRain, Waves, Mountain, ShieldCheck, Layers } from 'lucide-react'

interface GridPoint {
  id: number
  lat: number
  lon: number
  elevation_m: number
  rain_48h_mm: number
  river_discharge_m3s: number
  risk_score: number
  risk_level: string
  factors: {
    rain_contrib: number
    discharge_contrib: number
    elevation_contrib: number
    population_contrib: number
  }
}

interface InteractiveMapProps {
  center: [number, number]
  gridPoints: GridPoint[]
  districtName: string
}

const RISK_COLORS: Record<string, string> = {
  low: '#22c55e',       // Green / Aman
  medium: '#eab308',    // Yellow / Waspada
  high: '#f97316',      // Orange / Siaga
  severe: '#ef4444',    // Red / Awas
}

const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_API_KEY || 'Eeg9jpbOOY3skDQTExPf'

// MapTiler High-Resolution Style Presets
const MAP_STYLES: Record<string, { name: string; url: string; attribution: string }> = {
  streets: {
    name: 'MapTiler Streets',
    url: `https://api.maptiler.com/maps/streets-v2/256/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`,
    attribution: '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  dark: {
    name: 'MapTiler Dark Crisis',
    url: `https://api.maptiler.com/maps/dataviz-dark/256/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`,
    attribution: '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a>',
  },
  satellite: {
    name: 'MapTiler Satellite Hybrid',
    url: `https://api.maptiler.com/maps/hybrid/256/{z}/{x}/{y}.jpg?key=${MAPTILER_KEY}`,
    attribution: '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a>',
  },
  topo: {
    name: 'MapTiler Topo / Terrain',
    url: `https://api.maptiler.com/maps/topo-v2/256/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`,
    attribution: '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a>',
  },
}

// Controller to fly map smoothly when center changes
const MapRecenter: React.FC<{ center: [number, number] }> = ({ center }) => {
  const map = useMap()
  useEffect(() => {
    map.setView(center, 11, { animate: true })
  }, [center, map])
  return null
}

export const InteractiveRiskMap: React.FC<InteractiveMapProps> = ({ center, gridPoints, districtName }) => {
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

  // Default to MapTiler Dark in dark theme, or Streets in light theme
  const [selectedStyle, setSelectedStyle] = useState<string>(isDark ? 'dark' : 'streets')

  // Automatically update when theme toggles unless user manually picked satellite/topo
  useEffect(() => {
    if (selectedStyle === 'dark' || selectedStyle === 'streets') {
      setSelectedStyle(isDark ? 'dark' : 'streets')
    }
  }, [isDark])

  const activeStyle = MAP_STYLES[selectedStyle] || MAP_STYLES.streets

  return (
    <div className="relative w-full h-[480px] rounded-3xl overflow-hidden shadow-2xl border border-gray-200 dark:border-gray-800">
      <MapContainer
        center={center}
        zoom={11}
        scrollWheelZoom={false}
        className="w-full h-full"
      >
        <MapRecenter center={center} />
        <TileLayer
          key={selectedStyle}
          attribution={activeStyle.attribution}
          url={activeStyle.url}
          tileSize={256}
        />

        {gridPoints.map((pt) => {
          const color = RISK_COLORS[pt.risk_level.toLowerCase()] || '#3b82f6'
          return (
            <CircleMarker
              key={pt.id}
              center={[pt.lat, pt.lon]}
              radius={18}
              pathOptions={{
                color: '#ffffff',
                fillColor: color,
                fillOpacity: 0.75,
                weight: 2.5,
              }}
            >
              <Popup className="custom-leaflet-popup">
                <div className="p-1 space-y-2 text-xs">
                  <div className="flex items-center justify-between border-b pb-1">
                    <span className="font-extrabold text-gray-900 capitalize">{districtName} Grid #{pt.id}</span>
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-black uppercase text-white shadow-sm"
                      style={{ backgroundColor: color }}
                    >
                      {pt.risk_level}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-gray-700">
                    <div className="flex items-center space-x-1">
                      <CloudRain className="w-3.5 h-3.5 text-blue-500" />
                      <span>{pt.rain_48h_mm} mm rain</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Waves className="w-3.5 h-3.5 text-cyan-500" />
                      <span>{pt.river_discharge_m3s} m³/s</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Mountain className="w-3.5 h-3.5 text-amber-500" />
                      <span>{pt.elevation_m}m elev</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                      <span>Score: {Math.round(pt.risk_score * 100)}%</span>
                    </div>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>

      {/* MapTiler Layer Selector Control */}
      <div className="absolute top-4 right-4 z-[400] bg-white/90 dark:bg-darkCard/90 backdrop-blur-md p-1.5 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-xl flex items-center space-x-1 text-xs">
        <div className="px-2 py-1 flex items-center space-x-1 text-gray-500 font-bold uppercase text-[10px]">
          <Layers className="w-3.5 h-3.5 text-blue-500" />
          <span className="hidden sm:inline">MapTiler Style:</span>
        </div>
        {(['dark', 'streets', 'satellite', 'topo'] as const).map((styleKey) => (
          <button
            key={styleKey}
            onClick={() => setSelectedStyle(styleKey)}
            className={`px-2.5 py-1 rounded-xl font-extrabold capitalize text-[11px] transition-all ${
              selectedStyle === styleKey
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-darkMuted'
            }`}
          >
            {styleKey}
          </button>
        ))}
      </div>

      {/* Floating Legend */}
      <div className="absolute bottom-4 right-4 z-[400] bg-white/95 dark:bg-darkCard/95 backdrop-blur-md p-3.5 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-xl text-xs space-y-1.5">
        <div className="font-extrabold text-gray-900 dark:text-gray-100 uppercase tracking-wider text-[10px] flex items-center justify-between">
          <span>5km Flood Risk</span>
          <span className="text-[9px] text-blue-500 font-bold">MapTiler HD</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-3 rounded-full bg-emerald-500 shadow-sm"></span>
          <span className="text-gray-600 dark:text-gray-300 font-semibold text-[11px]">Low (Aman)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-3 rounded-full bg-yellow-500 shadow-sm"></span>
          <span className="text-gray-600 dark:text-gray-300 font-semibold text-[11px]">Medium (Waspada)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-3 rounded-full bg-orange-500 shadow-sm"></span>
          <span className="text-gray-600 dark:text-gray-300 font-semibold text-[11px]">High (Siaga)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-3 rounded-full bg-red-500 shadow-sm"></span>
          <span className="text-gray-600 dark:text-gray-300 font-semibold text-[11px]">Severe (Awas)</span>
        </div>
      </div>
    </div>
  )
}
