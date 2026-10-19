import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import {
  HeartHandshake,
  Sparkles,
  MapPin,
  Users,
  CheckCircle2,
  ShieldAlert,
  Loader2,
  PhoneCall,
  AlertTriangle,
} from 'lucide-react'
import { useAppStore } from '../lib/store'
import { LocationPicker, type SelectedLocationResult } from '../components/LocationPicker'

interface TriageResponse {
  id: number
  status: string
  triage_method: string
  urgency: string
  urgency_score: number
  need: string
  people_count: number
  vulnerable: string[]
  location_text: string
  location_confidence: string
  location_source?: string
  coordinates: { lat?: number; lon?: number }
  district?: string
  summary: string
  summary_hi?: string
  language: string
  created_at: string
}

export const GetHelpPage: React.FC = () => {
  const { t, i18n } = useTranslation()
  const isHi = i18n.language === 'hi'
  const { selectedDistrict } = useAppStore()
  const [message, setMessage] = useState('')
  const [result, setResult] = useState<TriageResponse | null>(null)
  const [isPickerOpen, setIsPickerOpen] = useState(false)
  const [isResultVerifying, setIsResultVerifying] = useState(false)
  const [isUpdatingLocation, setIsUpdatingLocation] = useState(false)
  const [pinnedLocation, setPinnedLocation] = useState<SelectedLocationResult | null>(null)

  const quickSamples = [
    {
      label: 'Terrace Trap (English)',
      text: 'Water entered ground floor, 5 people stuck on terrace including elderly grandmother. Please send boat urgently Patna Boring Road!',
    },
    {
      label: 'भोजन एवं पानी की कमी (Hindi)',
      text: 'भैया हमारे घर में पानी भर गया है, 4 लोग फंसे हैं, पीने का पानी और खाना 2 दिन से नहीं है।',
    },
    {
      label: 'Medical Emergency (Hinglish)',
      text: 'Bhaiya paani bohot tez aa raha hai, pregnant lady hai hospital pahunchana hai jaldi please.',
    },
  ]

  const triageMutation = useMutation({
    mutationFn: async ({ text, pinnedLoc }: { text: string; pinnedLoc?: SelectedLocationResult | null }) => {
      const res = await fetch('/api/v1/triage/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          district: selectedDistrict || 'Patna',
          lat: pinnedLoc?.lat,
          lon: pinnedLoc?.lon,
          location_text: pinnedLoc?.address,
          location_source: pinnedLoc?.source,
          location_confidence: pinnedLoc?.confidence,
        }),
      })
      if (!res.ok) throw new Error('Triage request failed')
      return res.json() as Promise<TriageResponse>
    },
    onSuccess: (data) => {
      setResult(data)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) return
    triageMutation.mutate({ text: message, pinnedLoc: pinnedLocation })
  }

  const handleUpdateResultLocation = async (loc: SelectedLocationResult) => {
    if (!result) return
    setIsUpdatingLocation(true)
    try {
      const res = await fetch(`/api/v1/matching/request/${result.id}/location`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: loc.lat,
          lon: loc.lon,
          location_raw: loc.address,
          location_source: loc.source,
          location_confidence: loc.confidence,
        }),
      })
      if (!res.ok) throw new Error('Failed to update location')
      setResult((prev) =>
        prev
          ? {
              ...prev,
              coordinates: { lat: loc.lat, lon: loc.lon },
              location_text: loc.address,
              location_confidence: loc.confidence,
              location_source: loc.source,
            }
          : null
      )
      setIsResultVerifying(false)
    } catch (err) {
      console.error('Error updating location:', err)
    } finally {
      setIsUpdatingLocation(false)
    }
  }

  const getUrgencyBadge = (urgency: string) => {
    switch (urgency.toLowerCase()) {
      case 'critical':
        return 'bg-red-600 text-white'
      case 'high':
        return 'bg-orange-500 text-white'
      case 'medium':
        return 'bg-yellow-500 text-white'
      default:
        return 'bg-green-600 text-white'
    }
  }

  const getConfidenceBadge = (confidence?: string) => {
    const c = (confidence || 'low').toLowerCase()
    if (c === 'high') {
      return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-500/30'
    }
    if (c === 'medium') {
      return 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border-amber-500/30'
    }
    return 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 border-rose-500/30'
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
      {/* Page Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-red-50 dark:bg-red-950/60 text-red-600 dark:text-red-400 text-xs font-semibold">
          <HeartHandshake className="w-4 h-4" />
          <span>Multilingual Emergency Rescue AI</span>
        </div>
        <h1 className="text-3xl font-black text-gray-900 dark:text-white tracking-tight">
          {t('nav.help')}
        </h1>
        <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 max-w-lg mx-auto">
          Describe your emergency in Hindi, English, or Hinglish. Our AI instantly extracts location, urgency, vulnerable individuals, and queues emergency rescue dispatch.
        </p>
      </div>

      {/* Input Form Card */}
      <div className="bg-white dark:bg-darkCard p-6 rounded-3xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-5">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
                What is your emergency? (आपकी समस्या क्या है?)
              </label>
              <span className="text-[11px] text-gray-400">Target District: <b>{selectedDistrict}</b></span>
            </div>
            <textarea
              rows={4}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="e.g. पानी घर में घुस गया है, 4 लोग छत पर हैं, एक बूढ़ी दादी हैं जिन्हें इंसुलिन चाहिए, जल्दी नाव भेजो बोरिंग रोड।"
              className="w-full p-4 rounded-2xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm leading-relaxed"
            />
          </div>

          {/* Pre-submission Location Attachment */}
          <div className="pt-1">
            {pinnedLocation ? (
              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-500/30 text-xs">
                <div className="flex items-center space-x-2.5 truncate mr-2">
                  <div className="p-1.5 rounded-lg bg-emerald-600 text-white shrink-0">
                    <MapPin className="w-4 h-4" />
                  </div>
                  <div className="truncate">
                    <span className="font-bold text-emerald-900 dark:text-emerald-100 block truncate">
                      {pinnedLocation.address}
                    </span>
                    <span className="text-[10px] text-emerald-700/80 dark:text-emerald-300/80 font-mono">
                      {pinnedLocation.lat.toFixed(5)}, {pinnedLocation.lon.toFixed(5)} • {pinnedLocation.source} • {pinnedLocation.confidence} confidence
                    </span>
                  </div>
                </div>
                <div className="flex items-center space-x-1.5 shrink-0">
                  <button
                    type="button"
                    onClick={() => setIsPickerOpen(true)}
                    className="px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition"
                  >
                    {isHi ? 'बदलें' : 'Change'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setPinnedLocation(null)}
                    className="px-2 py-1 text-[11px] font-semibold rounded-lg text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setIsPickerOpen(true)}
                className="inline-flex items-center space-x-2 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 p-2.5 rounded-xl border border-dashed border-blue-300 dark:border-blue-800 hover:bg-blue-50/50 dark:hover:bg-blue-950/40 transition w-full justify-center"
              >
                <MapPin className="w-4 h-4" />
                <span>{isHi ? '📍 नक्शे पर सटीक स्थान चुनें / GPS का उपयोग करें (वैकल्पिक)' : '📍 Pin exact location on map / use GPS (Optional)'}</span>
              </button>
            )}
          </div>

          {/* Quick Preset Buttons */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Try Sample Distress Messages:</span>
            <div className="flex flex-wrap gap-2">
              {quickSamples.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setMessage(sample.text)}
                  className="px-3 py-1.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted hover:bg-gray-100 dark:hover:bg-gray-800 text-[11px] text-gray-700 dark:text-gray-300 transition-colors font-medium"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={triageMutation.isPending || !message.trim()}
            className="w-full py-4 rounded-2xl bg-gradient-to-r from-red-600 via-rose-600 to-red-600 hover:from-red-700 hover:to-rose-700 text-white font-extrabold text-sm shadow-xl shadow-red-500/20 hover:shadow-red-500/40 active:scale-[0.99] flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
          >
            {triageMutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Analyzing Distress Message...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                <span>{t('actions.submit')}</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Pre-submission Location Picker Modal */}
      {isPickerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white dark:bg-darkCard w-full max-w-2xl rounded-3xl p-6 shadow-2xl border border-gray-200 dark:border-gray-800 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3 border-gray-100 dark:border-gray-800">
              <div>
                <h3 className="text-base font-bold text-gray-900 dark:text-white">
                  {isHi ? 'सटीक स्थान चुनें' : 'Pin Exact Location on Map'}
                </h3>
                <p className="text-xs text-gray-500">
                  {isHi ? 'स्थान खोजें, जीपीएस का उपयोग करें या मार्कर को ड्रैग करें' : 'Search, use GPS, or drag the pin to your exact rescue point'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsPickerOpen(false)}
                className="w-8 h-8 flex items-center justify-center rounded-full text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
              >
                ✕
              </button>
            </div>

            <LocationPicker
              districtName={selectedDistrict || 'Patna'}
              initialLat={pinnedLocation?.lat}
              initialLon={pinnedLocation?.lon}
              initialAddress={pinnedLocation?.address}
              onLocationConfirm={(loc: SelectedLocationResult) => {
                setPinnedLocation(loc)
                setIsPickerOpen(false)
              }}
              onCancel={() => setIsPickerOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Post-triage Result Location Correction Modal */}
      {isResultVerifying && result && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white dark:bg-darkCard w-full max-w-2xl rounded-3xl p-6 shadow-2xl border border-gray-200 dark:border-gray-800 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3 border-gray-100 dark:border-gray-800">
              <div>
                <h3 className="text-base font-bold text-gray-900 dark:text-white">
                  {isHi ? 'स्थान सत्यापित / ठीक करें' : 'Verify & Correct Location'}
                </h3>
                <p className="text-xs text-gray-500">
                  Request #{result.id} • {isHi ? 'सटीक स्थान चुनें ताकि बचाव दल आसानी से पहुँच सके' : 'Set precise location so rescue teams can reach without delay'}
                </p>
              </div>
              <button
                type="button"
                disabled={isUpdatingLocation}
                onClick={() => setIsResultVerifying(false)}
                className="w-8 h-8 flex items-center justify-center rounded-full text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
              >
                ✕
              </button>
            </div>

            <LocationPicker
              districtName={result.district || selectedDistrict || 'Patna'}
              initialLat={result.coordinates?.lat}
              initialLon={result.coordinates?.lon}
              initialAddress={result.location_text}
              onLocationConfirm={handleUpdateResultLocation}
              onCancel={() => setIsResultVerifying(false)}
            />
          </div>
        </div>
      )}

      {/* Triage Extraction Result Modal / Card */}
      {result && (
        <div className="bg-white dark:bg-darkCard p-6 rounded-3xl border border-gray-200 dark:border-gray-800 shadow-lg space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-4">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-500">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-extrabold text-base text-gray-900 dark:text-white">
                  Help Request #{result.id} Triaged & Queued
                </h3>
                <span className="text-[11px] text-gray-400">
                  Engine: <b className="capitalize">{result.triage_method}</b> • Detected Lang: <b className="uppercase">{result.language}</b>
                </span>
              </div>
            </div>

            <span className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider ${getUrgencyBadge(result.urgency)}`}>
              {result.urgency} Urgency
            </span>
          </div>

          {/* Extracted Parameters Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 bg-gray-50 dark:bg-darkMuted rounded-xl space-y-1">
              <span className="text-gray-400 font-semibold uppercase text-[10px]">Primary Need</span>
              <div className="font-bold text-gray-900 dark:text-white capitalize flex items-center space-x-1">
                <ShieldAlert className="w-3.5 h-3.5 text-blue-500" />
                <span>{result.need}</span>
              </div>
            </div>

            <div className="p-3 bg-gray-50 dark:bg-darkMuted rounded-xl space-y-1">
              <span className="text-gray-400 font-semibold uppercase text-[10px]">People Count</span>
              <div className="font-bold text-gray-900 dark:text-white flex items-center space-x-1">
                <Users className="w-3.5 h-3.5 text-purple-500" />
                <span>{result.people_count} Individual(s)</span>
              </div>
            </div>

            <div className="p-3 bg-gray-50 dark:bg-darkMuted rounded-xl space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-gray-400 font-semibold uppercase text-[10px]">Location</span>
                <span className={`px-1.5 py-0.2 rounded text-[9px] font-black uppercase border ${getConfidenceBadge(result.location_confidence)}`}>
                  {result.location_confidence || 'low'}
                </span>
              </div>
              <div className="font-bold text-gray-900 dark:text-white truncate flex items-center space-x-1">
                <MapPin className="w-3.5 h-3.5 text-red-500 shrink-0" />
                <span title={result.location_text}>{result.location_text || 'District Center'}</span>
              </div>
              {result.coordinates?.lat && result.coordinates?.lon && (
                <div className="text-[10px] text-gray-400 font-mono truncate">
                  {result.coordinates.lat.toFixed(4)}, {result.coordinates.lon.toFixed(4)}
                </div>
              )}
            </div>

            <div className="p-3 bg-gray-50 dark:bg-darkMuted rounded-xl space-y-1">
              <span className="text-gray-400 font-semibold uppercase text-[10px]">Vulnerable Groups</span>
              <div className="font-bold text-gray-900 dark:text-white">
                {result.vulnerable && result.vulnerable.length > 0
                  ? result.vulnerable.join(', ')
                  : 'None specified'}
              </div>
            </div>
          </div>

          {/* Low Confidence Warning / Verify Button */}
          {result.location_confidence === 'low' ? (
            <div className="p-3.5 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-500/30 flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2 text-amber-800 dark:text-amber-300">
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
                <span>
                  {isHi
                    ? 'स्थान की सटीकता कम है। कृपया सटीक जगह सत्यापित करें।'
                    : 'Location accuracy is approximate. Please verify on the map.'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsResultVerifying(true)}
                className="px-3 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs shrink-0 shadow-sm transition active:scale-95"
              >
                {isHi ? 'स्थान सत्यापित करें' : 'Verify location'}
              </button>
            </div>
          ) : (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setIsResultVerifying(true)}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center space-x-1 font-semibold"
              >
                <MapPin className="w-3.5 h-3.5" />
                <span>{isHi ? 'स्थान समायोजित करें' : 'Adjust / correct location'}</span>
              </button>
            </div>
          )}

          {/* Bilingual Summaries */}
          <div className="p-4 rounded-2xl bg-blue-50/50 dark:bg-blue-950/30 border border-blue-500/20 space-y-2">
            <div className="text-[11px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
              Coordinator Situation Summary
            </div>
            <p className="text-xs text-gray-800 dark:text-gray-200 font-medium">
              <b>English:</b> {result.summary}
            </p>
            {result.summary_hi && (
              <p className="text-xs text-gray-700 dark:text-gray-300">
                <b>हिन्दी:</b> {result.summary_hi}
              </p>
            )}
          </div>

          <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-100 dark:border-gray-800">
            <div className="flex items-center space-x-1.5 text-emerald-600 dark:text-emerald-400 font-semibold">
              <PhoneCall className="w-3.5 h-3.5" />
              <span>Direct dispatch link sent to local volunteer rescue team</span>
            </div>
            <span>Status: <b className="capitalize text-amber-500">{result.status}</b></span>
          </div>
        </div>
      )}
    </div>
  )
}

