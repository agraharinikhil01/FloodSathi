import React, { useState, useEffect, useRef, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Circle, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {
  MapPin,
  Crosshair,
  Search,
  CheckCircle2,
  X,
  AlertCircle,
  Loader2,
  ShieldCheck,
  HelpCircle,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

export interface SelectedLocationResult {
  lat: number
  lon: number
  address: string
  name?: string
  source: string // 'geoapify' | 'photon' | 'nominatim' | 'gps' | 'manual_pin' | 'failed'
  confidence: string // 'high' | 'medium' | 'low'
  accuracyMeters?: number
}

interface LocationPickerProps {
  initialLat?: number
  initialLon?: number
  initialAddress?: string
  districtName?: string
  onLocationConfirm: (loc: SelectedLocationResult) => void
  onCancel?: () => void
}

const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_API_KEY || 'Eeg9jpbOOY3skDQTExPf'

// Custom Pin Icon using HTML/SVG so it never breaks in bundlers
const customPinIcon = L.divIcon({
  className: 'custom-location-pin',
  html: `
    <div style="position: relative; width: 36px; height: 36px; transform: translate(-50%, -100%); cursor: grab;">
      <div style="background: linear-gradient(135deg, #ef4444, #b91c1c); width: 34px; height: 34px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4); border: 2.5px solid #ffffff;">
        <div style="width: 10px; height: 10px; background-color: #ffffff; border-radius: 50%; transform: rotate(45deg);"></div>
      </div>
    </div>
  `,
  iconSize: [36, 36],
  iconAnchor: [18, 36],
})

// Controller to smoothly animate map to new location
const MapFlyController: React.FC<{ targetCoords: [number, number] | null }> = ({ targetCoords }) => {
  const map = useMap()
  useEffect(() => {
    if (targetCoords) {
      map.flyTo(targetCoords, 16, { animate: true, duration: 1.2 })
    }
  }, [targetCoords, map])
  return null
}

export const LocationPicker: React.FC<LocationPickerProps> = ({
  initialLat = 25.6093,
  initialLon = 85.1235,
  initialAddress = '',
  districtName = 'Patna',
  onLocationConfirm,
  onCancel,
}) => {
  const { i18n } = useTranslation()
  const isHi = i18n.language === 'hi'

  const [currentLat, setCurrentLat] = useState<number>(initialLat)
  const [currentLon, setCurrentLon] = useState<number>(initialLon)
  const [displayAddress, setDisplayAddress] = useState<string>(initialAddress)
  const [source, setSource] = useState<string>('manual_pin')
  const [confidence, setConfidence] = useState<string>('high')
  const [gpsAccuracy, setGpsAccuracy] = useState<number | null>(null)

  // Search & autocomplete states
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isLocatingGps, setIsLocatingGps] = useState(false)
  const [isReversing, setIsReversing] = useState(false)
  const [geoError, setGeoError] = useState<string | null>(null)

  const [flyTarget, setFlyTarget] = useState<[number, number] | null>([initialLat, initialLon])
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 400ms Debounced Autocomplete search
  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setSuggestions([])
      setIsDropdownOpen(false)
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const url = `/api/v1/geocode?q=${encodeURIComponent(
          query.trim()
        )}&lat=${currentLat}&lon=${currentLon}&district=${encodeURIComponent(
          districtName
        )}&type=autocomplete&limit=5`
        const res = await fetch(url)
        if (res.ok) {
          const data = await res.json()
          setSuggestions(data || [])
          setIsDropdownOpen(true)
        }
      } catch (err) {
        console.error('Autocomplete error:', err)
      } finally {
        setIsSearching(false)
      }
    }, 400)

    return () => clearTimeout(timer)
  }, [query, currentLat, currentLon, districtName])

  // Select suggestion item
  const handleSelectSuggestion = (item: any) => {
    setCurrentLat(item.lat)
    setCurrentLon(item.lon)
    setDisplayAddress(item.display_name)
    setSource(item.source || 'geoapify')
    setConfidence(item.confidence || 'medium')
    setGpsAccuracy(null)
    setFlyTarget([item.lat, item.lon])
    setIsDropdownOpen(false)
    setQuery(item.name || item.display_name)
    setGeoError(null)
  }

  // Reverse geocode when pin is dragged
  const handleMarkerDragEnd = async (event: any) => {
    const marker = event.target
    const pos = marker.getLatLng()
    const newLat = pos.lat
    const newLon = pos.lng

    setCurrentLat(newLat)
    setCurrentLon(newLon)
    setSource('manual_pin')
    setConfidence('high')
    setGpsAccuracy(null)
    setIsReversing(true)

    try {
      const res = await fetch(`/api/v1/reverse?lat=${newLat}&lon=${newLon}&district=${encodeURIComponent(districtName)}`)
      if (res.ok) {
        const data = await res.json()
        setDisplayAddress(data.display_name || `${newLat.toFixed(4)}, ${newLon.toFixed(4)}`)
      } else {
        setDisplayAddress(`${newLat.toFixed(4)}, ${newLon.toFixed(4)}`)
      }
    } catch (e) {
      setDisplayAddress(`${newLat.toFixed(4)}, ${newLon.toFixed(4)}`)
    } finally {
      setIsReversing(false)
    }
  }

  // GPS Fix (navigator.geolocation with high accuracy)
  const handleUseCurrentLocation = () => {
    setGeoError(null)
    if (!navigator.geolocation) {
      setGeoError(isHi ? 'आपके ब्राउज़र में GPS की सुविधा उपलब्ध नहीं है।' : 'Geolocation is not supported by your browser.')
      return
    }

    setIsLocatingGps(true)
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setIsLocatingGps(false)
        const lat = pos.coords.latitude
        const lon = pos.coords.longitude
        const acc = pos.coords.accuracy

        setCurrentLat(lat)
        setCurrentLon(lon)
        setGpsAccuracy(acc)
        setSource('gps')
        setConfidence('high')
        setFlyTarget([lat, lon])

        // Reverse geocode to find street/area name
        setIsReversing(true)
        try {
          const res = await fetch(`/api/v1/reverse?lat=${lat}&lon=${lon}&district=${encodeURIComponent(districtName)}`)
          if (res.ok) {
            const data = await res.json()
            setDisplayAddress(data.display_name || `${lat.toFixed(4)}, ${lon.toFixed(4)}`)
          } else {
            setDisplayAddress(`GPS Fix: ${lat.toFixed(4)}, ${lon.toFixed(4)} (±${Math.round(acc)}m)`)
          }
        } catch {
          setDisplayAddress(`GPS Fix: ${lat.toFixed(4)}, ${lon.toFixed(4)} (±${Math.round(acc)}m)`)
        } finally {
          setIsReversing(false)
        }
      },
      (err) => {
        setIsLocatingGps(false)
        if (err.code === err.PERMISSION_DENIED) {
          setGeoError(
            isHi
              ? 'लोकेशन परमिशन अस्वीकार कर दी गई। कृपया ब्राउज़र सेटिंग्स में लोकेशन अनुमति दें।'
              : 'Location permission denied. Please allow location access in your browser settings.'
          )
        } else {
          setGeoError(
            isHi
              ? 'GPS सिग्नल नहीं मिल पाया। कृपया पिन को मैप पर खींचकर सेट करें।'
              : 'Unable to retrieve GPS position. Please drag the pin on the map.'
          )
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    )
  }

  // Confirm selection
  const handleConfirm = () => {
    onLocationConfirm({
      lat: currentLat,
      lon: currentLon,
      address: displayAddress || `${currentLat.toFixed(5)}, ${currentLon.toFixed(5)}`,
      source,
      confidence: 'high', // User confirmation elevates confidence to high
      accuracyMeters: gpsAccuracy || undefined,
    })
  }

  const markerPosition: [number, number] = useMemo(() => [currentLat, currentLon], [currentLat, currentLon])

  const getConfidenceBadge = (conf: string) => {
    switch (conf.toLowerCase()) {
      case 'high':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>{isHi ? 'उच्च सटीकता' : 'High Confidence'}</span>
          </span>
        )
      case 'medium':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
            <ShieldCheck className="w-3 h-3 text-amber-600" />
            <span>{isHi ? 'मध्यम सटीकता' : 'Medium Confidence'}</span>
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 dark:bg-rose-950/70 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
            <AlertCircle className="w-3 h-3 text-rose-600" />
            <span>{isHi ? 'पुष्टि आवश्यक' : 'Low Confidence'}</span>
          </span>
        )
    }
  }

  const getSourceBadge = (src: string) => {
    const srcMap: Record<string, { label: string; bg: string }> = {
      geoapify: { label: 'Geoapify (Primary)', bg: 'bg-blue-100 dark:bg-blue-950/70 text-blue-700 dark:text-blue-300' },
      photon: { label: 'Photon (Komoot)', bg: 'bg-purple-100 dark:bg-purple-950/70 text-purple-700 dark:text-purple-300' },
      nominatim: { label: 'Nominatim (OSM)', bg: 'bg-orange-100 dark:bg-orange-950/70 text-orange-700 dark:text-orange-300' },
      gps: { label: 'GPS Device Fix', bg: 'bg-cyan-100 dark:bg-cyan-950/70 text-cyan-700 dark:text-cyan-300' },
      manual_pin: { label: 'Manual Pin (यूजर पिन)', bg: 'bg-teal-100 dark:bg-teal-950/70 text-teal-700 dark:text-teal-300' },
    }
    const item = srcMap[src] || { label: src, bg: 'bg-gray-100 text-gray-700' }
    return (
      <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold tracking-wide uppercase ${item.bg}`}>
        {item.label}
      </span>
    )
  }

  return (
    <div className="bg-white dark:bg-darkCard rounded-3xl border border-gray-200 dark:border-gray-800 shadow-2xl overflow-hidden flex flex-col space-y-4 p-5 max-w-2xl w-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-800">
        <div className="space-y-0.5">
          <h2 className="text-base font-black text-gray-900 dark:text-white flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-red-500" />
            <span>{isHi ? 'स्थान चुनें या पुष्टि करें' : 'Pin & Verify Location'}</span>
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {isHi
              ? 'सटीक राहत एवं बचाव के लिए पिन को खींचकर सही स्थान पर रखें।'
              : 'Search or drag the pin on the map to pinpoint exact emergency location.'}
          </p>
        </div>
        {onCancel && (
          <button
            onClick={onCancel}
            className="p-1 rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Search Input with Autocomplete + GPS Button */}
      <div className="flex flex-col sm:flex-row items-stretch gap-2 relative" ref={dropdownRef}>
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => {
              if (suggestions.length > 0) setIsDropdownOpen(true)
            }}
            placeholder={
              isHi
                ? 'जगह खोजें (उदा: दानापुर, बोरिंग रोड, कतई)...'
                : 'Search place (e.g. Danapur, Boring Road, Morigaon)...'
            }
            className="w-full bg-gray-50 dark:bg-darkMuted border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white text-xs font-semibold rounded-2xl py-2.5 pl-9 pr-8 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
          />
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3 pointer-events-none" />
          {query && (
            <button
              onClick={() => {
                setQuery('')
                setSuggestions([])
                setIsDropdownOpen(false)
              }}
              className="absolute right-2.5 top-2.5 p-0.5 text-gray-400 hover:text-gray-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Autocomplete Suggestions Menu */}
          {isDropdownOpen && suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1.5 bg-white dark:bg-darkCard rounded-2xl border border-gray-200 dark:border-gray-700 shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-1 duration-150">
              <div className="px-3 py-1.5 border-b border-gray-100 dark:border-gray-800 bg-gray-50/70 dark:bg-darkMuted/60 flex items-center justify-between text-[10px] font-bold text-gray-500">
                <span>{isHi ? 'स्थान सुझाव (Geoapify / Photon / OSM)' : 'Location Suggestions'}</span>
                {isSearching && <Loader2 className="w-3 h-3 animate-spin text-blue-500" />}
              </div>
              <div className="max-h-60 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800/60">
                {suggestions.map((s, idx) => (
                  <button
                    key={`${s.lat}-${s.lon}-${idx}`}
                    type="button"
                    onClick={() => handleSelectSuggestion(s)}
                    className="w-full text-left p-2.5 hover:bg-blue-50 dark:hover:bg-blue-950/40 transition-colors flex items-start space-x-2 group"
                  >
                    <MapPin className="w-3.5 h-3.5 text-red-500 mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-bold text-gray-900 dark:text-white truncate group-hover:text-blue-600">
                        {s.name}
                      </div>
                      <div className="text-[10px] text-gray-400 truncate">{s.display_name}</div>
                    </div>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 font-mono">
                      {s.source}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Use My Current Location Button */}
        <button
          type="button"
          onClick={handleUseCurrentLocation}
          disabled={isLocatingGps}
          className="flex items-center justify-center space-x-1.5 px-3.5 py-2.5 bg-gray-100 dark:bg-darkMuted hover:bg-blue-50 dark:hover:bg-blue-950/40 text-blue-600 dark:text-brand-cyan rounded-2xl text-xs font-bold border border-gray-200 dark:border-gray-700 transition-all shrink-0 active:scale-95 disabled:opacity-50"
        >
          {isLocatingGps ? (
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
          ) : (
            <Crosshair className="w-4 h-4" />
          )}
          <span>{isHi ? 'मेरा वर्तमान स्थान (GPS)' : 'Current Location'}</span>
        </button>
      </div>

      {/* Geolocation Alert or Error */}
      {geoError && (
        <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-300 dark:border-red-800 rounded-2xl text-xs text-red-700 dark:text-red-300 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
          <span>{geoError}</span>
        </div>
      )}

      {/* Interactive Map with Draggable Marker */}
      <div className="w-full h-64 rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800 relative shadow-inner">
        <MapContainer
          center={markerPosition}
          zoom={14}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            url={`https://api.maptiler.com/maps/streets-v2/256/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`}
            attribution='&copy; <a href="https://www.maptiler.com/">MapTiler</a> &copy; OpenStreetMap'
          />
          <MapFlyController targetCoords={flyTarget} />

          {/* Draggable Emergency Pin Marker */}
          <Marker
            position={markerPosition}
            draggable={true}
            eventHandlers={{ dragend: handleMarkerDragEnd }}
            icon={customPinIcon}
          />

          {/* GPS Accuracy Circle */}
          {gpsAccuracy && (
            <Circle
              center={markerPosition}
              radius={gpsAccuracy}
              pathOptions={{
                color: '#06b6d4',
                fillColor: '#06b6d4',
                fillOpacity: 0.15,
                weight: 1.5,
              }}
            />
          )}
        </MapContainer>

        {/* Floating Hint Overlay on Map */}
        <div className="absolute bottom-2 left-2 right-2 pointer-events-none z-[1000] flex justify-center">
          <div className="px-3 py-1 bg-black/75 backdrop-blur-md rounded-full text-[10px] text-white font-medium shadow-lg flex items-center space-x-1.5">
            <HelpCircle className="w-3 h-3 text-cyan-400" />
            <span>
              {isHi
                ? 'पिन को खींचकर (Drag) अपने सटीक घर/स्थान पर रखें।'
                : 'Drag the pin to adjust your exact location.'}
            </span>
          </div>
        </div>
      </div>

      {/* Address & Status Display */}
      <div className="p-3.5 bg-gray-50 dark:bg-darkMuted/60 rounded-2xl border border-gray-100 dark:border-gray-800 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getConfidenceBadge(confidence)}
            {getSourceBadge(source)}
          </div>
          <span className="text-[10px] text-gray-400 font-mono">
            {currentLat.toFixed(5)}°, {currentLon.toFixed(5)}°
          </span>
        </div>

        <div className="flex items-start space-x-2 text-xs">
          <MapPin className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
          <div className="flex-1 font-medium text-gray-800 dark:text-gray-200">
            {isReversing ? (
              <span className="text-gray-400 flex items-center space-x-1">
                <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
                <span>{isHi ? 'पता खोजा जा रहा है...' : 'Resolving street address...'}</span>
              </span>
            ) : (
              displayAddress || `${currentLat.toFixed(5)}, ${currentLon.toFixed(5)}`
            )}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-end space-x-2 pt-1">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-xl text-xs font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            {isHi ? 'रद्द करें' : 'Cancel'}
          </button>
        )}
        <button
          type="button"
          onClick={handleConfirm}
          className="flex items-center space-x-1.5 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl text-xs font-extrabold shadow-lg shadow-emerald-600/20 active:scale-95 transition-all"
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>{isHi ? 'इस स्थान की पुष्टि करें' : 'Confirm this location'}</span>
        </button>
      </div>
    </div>
  )
}
