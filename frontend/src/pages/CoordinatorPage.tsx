import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  RefreshCw,
  Building2,
  Home,
  UserCheck,
  Compass,
  Zap,
  Loader2,
  MapPin,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react'
import { useAppStore } from '../lib/store'
import { LocationPicker, type SelectedLocationResult } from '../components/LocationPicker'

interface AssignmentDetail {
  name: string
  distance_km: number
  eta_min: number
}

interface CoordinatorRequest {
  id: number
  district: string
  raw_text: string
  language?: string
  urgency?: number
  need?: string
  people_count?: number
  location_raw?: string
  lat?: number
  lon?: number
  location_source?: string
  location_confidence?: string
  summary_en?: string
  summary_hi?: string
  status: string
  created_at: string
  assignments: {
    volunteer?: AssignmentDetail
    shelter?: AssignmentDetail
    hospital?: AssignmentDetail
  }
}

export const CoordinatorPage: React.FC = () => {
  const { t } = useTranslation()
  const { selectedDistrict } = useAppStore()
  const queryClient = useQueryClient()
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [verifyingRequest, setVerifyingRequest] = useState<CoordinatorRequest | null>(null)

  // Fetch coordinator queue
  const {
    data: requests = [],
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ['coordinatorRequests', filterStatus, selectedDistrict],
    queryFn: async () => {
      let url = '/api/v1/matching/requests?limit=100'
      if (filterStatus !== 'all') {
        url += `&status=${filterStatus}`
      }
      const res = await fetch(url)
      if (!res.ok) throw new Error('Failed to fetch requests')
      return res.json() as Promise<CoordinatorRequest[]>
    },
  })

  // Batch Auto-Match Mutation
  const batchMatchMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/matching/match-all?limit=50', {
        method: 'POST',
      })
      if (!res.ok) throw new Error('Batch matching failed')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coordinatorRequests'] })
    },
  })

  // Single Match Mutation
  const singleMatchMutation = useMutation({
    mutationFn: async (reqId: number) => {
      const res = await fetch(`/api/v1/matching/match/${reqId}`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error('Match failed')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coordinatorRequests'] })
    },
  })

  // Location Verification Mutation
  const updateLocationMutation = useMutation({
    mutationFn: async (payload: {
      requestId: number
      lat: number
      lon: number
      address: string
      source: string
      confidence: string
    }) => {
      const res = await fetch(`/api/v1/matching/request/${payload.requestId}/location`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: payload.lat,
          lon: payload.lon,
          location_raw: payload.address,
          location_source: payload.source,
          location_confidence: payload.confidence,
        }),
      })
      if (!res.ok) throw new Error('Failed to update location')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coordinatorRequests'] })
      setVerifyingRequest(null)
    },
  })

  const getUrgencyColor = (urgency?: number) => {
    switch (urgency) {
      case 5:
        return 'bg-red-600 text-white'
      case 4:
        return 'bg-orange-500 text-white'
      case 3:
        return 'bg-yellow-500 text-white'
      default:
        return 'bg-green-600 text-white'
    }
  }

  const unassignedCount = requests.filter((r) => r.status === 'new').length

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Header & Batch Matching Action */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-darkCard p-6 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm">
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-brand-cyan text-xs font-semibold">
            <Compass className="w-3.5 h-3.5" />
            <span>Emergency Operations Center</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-white">
            {t('nav.coordinator')}
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Real-time triage queue, nearest shelter capacity tracking, and automated volunteer dispatch.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2.5 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200 transition-colors shadow-sm"
            title="Refresh requests"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin text-blue-500' : ''}`} />
          </button>

          <button
            onClick={() => batchMatchMutation.mutate()}
            disabled={batchMatchMutation.isPending || unassignedCount === 0}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-brand-blue hover:from-blue-700 hover:to-blue-600 text-white text-xs font-extrabold shadow-lg shadow-blue-500/20 active:scale-95 transition-all disabled:opacity-50"
          >
            {batchMatchMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Assigning Resources...</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 fill-white" />
                <span>Auto-Match All Open ({unassignedCount})</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Filter Tabs & Counter */}
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 pb-3">
        <div className="flex items-center space-x-2">
          {['all', 'new', 'assigned', 'resolved'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors ${
                filterStatus === st
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-gray-100 dark:bg-darkCard text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800'
              }`}
            >
              {st} {st === 'new' ? `(${unassignedCount})` : ''}
            </button>
          ))}
        </div>

        <span className="text-xs text-gray-400 font-medium">
          Showing <b>{requests.length}</b> request(s)
        </span>
      </div>

      {/* Requests List */}
      <div className="space-y-4">
        {requests.map((req) => (
          <div
            key={req.id}
            className={`p-5 rounded-2xl bg-white dark:bg-darkCard border shadow-sm transition-all space-y-4 ${
              req.status === 'new'
                ? 'border-red-500/30 dark:border-red-500/20 shadow-red-500/5'
                : 'border-gray-200 dark:border-gray-800'
            }`}
          >
            {/* Top Row: Meta & Urgency Badge */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 dark:border-gray-800 pb-3">
              <div className="flex items-center space-x-2.5">
                <span
                  className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${getUrgencyColor(
                    req.urgency
                  )}`}
                >
                  Urgency {req.urgency || 3}
                </span>
                <span className="font-extrabold text-xs text-gray-900 dark:text-white">
                  Request #{req.id} • {req.district}
                </span>
                <span className="text-[11px] text-gray-400 font-medium">
                  {req.people_count ? `${req.people_count} person(s)` : 'General'} • Need:{' '}
                  <b className="capitalize text-blue-500">{req.need || 'rescue'}</b>
                </span>
              </div>

              <div className="flex items-center space-x-2 text-xs">
                <span
                  className={`px-2 py-0.5 rounded-full font-bold text-[10px] uppercase tracking-wider ${
                    req.status === 'assigned'
                      ? 'bg-emerald-500/10 text-emerald-500'
                      : req.status === 'new'
                      ? 'bg-amber-500/10 text-amber-500'
                      : 'bg-gray-500/10 text-gray-400'
                  }`}
                >
                  {req.status}
                </span>

                {req.status === 'new' && (
                  <button
                    onClick={() => singleMatchMutation.mutate(req.id)}
                    disabled={singleMatchMutation.isPending}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-all shadow-sm active:scale-95 disabled:opacity-50"
                  >
                    Match Resources
                  </button>
                )}
              </div>
            </div>

            {/* Middle Row: Citizen Distress Text & Summaries */}
            <div className="space-y-2">
              <p className="text-xs text-gray-800 dark:text-gray-200 font-medium bg-gray-50 dark:bg-darkMuted/60 p-3 rounded-xl border border-gray-100 dark:border-gray-800">
                "{req.raw_text}"
              </p>

              {(req.summary_en || req.summary_hi) && (
                <div className="text-[11px] text-gray-500 dark:text-gray-400 flex flex-col sm:flex-row gap-1 sm:gap-4">
                  {req.summary_en && (
                    <span>
                      <b>Summary:</b> {req.summary_en}
                    </span>
                  )}
                  {req.summary_hi && (
                    <span>
                      <b>विवरण:</b> {req.summary_hi}
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Bottom Row: Matched Resources Cards */}
            {req.status === 'assigned' && req.assignments && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                {/* Hospital */}
                <div className="p-3 bg-red-50/50 dark:bg-red-950/20 border border-red-500/20 rounded-xl space-y-1">
                  <div className="flex items-center space-x-1.5 text-red-600 dark:text-red-400 text-xs font-bold">
                    <Building2 className="w-3.5 h-3.5" />
                    <span>Hospital</span>
                  </div>
                  <div className="text-xs font-semibold text-gray-900 dark:text-white truncate">
                    {req.assignments.hospital?.name || 'Assigned Post'}
                  </div>
                  <div className="text-[10px] text-gray-500">
                    {req.assignments.hospital
                      ? `${req.assignments.hospital.distance_km} km • ETA ${req.assignments.hospital.eta_min} min`
                      : 'Standby'}
                  </div>
                </div>

                {/* Shelter */}
                <div className="p-3 bg-blue-50/50 dark:bg-blue-950/20 border border-blue-500/20 rounded-xl space-y-1">
                  <div className="flex items-center space-x-1.5 text-blue-600 dark:text-blue-400 text-xs font-bold">
                    <Home className="w-3.5 h-3.5" />
                    <span>Relief Shelter</span>
                  </div>
                  <div className="text-xs font-semibold text-gray-900 dark:text-white truncate">
                    {req.assignments.shelter?.name || 'Local Relief Camp'}
                  </div>
                  <div className="text-[10px] text-gray-500">
                    {req.assignments.shelter
                      ? `${req.assignments.shelter.distance_km} km • ETA ${req.assignments.shelter.eta_min} min`
                      : 'Capacity allocated'}
                  </div>
                </div>

                {/* Volunteer */}
                <div className="p-3 bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-500/20 rounded-xl space-y-1">
                  <div className="flex items-center space-x-1.5 text-emerald-600 dark:text-emerald-400 text-xs font-bold">
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>Volunteer Responder</span>
                  </div>
                  <div className="text-xs font-semibold text-gray-900 dark:text-white truncate">
                    {req.assignments.volunteer?.name || 'Dispatched Field Agent'}
                  </div>
                  <div className="text-[10px] text-gray-500">
                    {req.assignments.volunteer
                      ? `${req.assignments.volunteer.distance_km} km • ETA ${req.assignments.volunteer.eta_min} min`
                      : 'En route'}
                  </div>
                </div>
              </div>
            )}

            {/* Location & Verification Row */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-gray-100 dark:border-gray-800 text-xs">
              <div className="flex items-center space-x-1.5 text-gray-700 dark:text-gray-300 min-w-0">
                <MapPin className="w-3.5 h-3.5 text-red-500 shrink-0" />
                <span className="font-semibold truncate max-w-xs">{req.location_raw || 'Unknown Location'}</span>
                {req.lat != null && req.lon != null && (
                  <span className="text-[10px] text-gray-400 font-mono shrink-0">
                    ({req.lat.toFixed(3)}, {req.lon.toFixed(3)})
                  </span>
                )}
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                {req.location_confidence === 'low' ? (
                  <button
                    onClick={() => setVerifyingRequest(req)}
                    className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-xl text-xs font-black bg-amber-500 hover:bg-amber-600 text-white shadow-sm transition-all active:scale-95 animate-pulse"
                    title="Geocoding confidence is low. Click to pinpoint exact location on map."
                  >
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Verify location</span>
                  </button>
                ) : (
                  <button
                    onClick={() => setVerifyingRequest(req)}
                    className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-lg text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/30 transition-colors"
                    title="Click to view or adjust location pin"
                  >
                    <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                    <span>Verified ({req.location_source || 'geoapify'})</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Location Verification Drawer / Modal */}
      {verifyingRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <LocationPicker
            initialLat={verifyingRequest.lat || 25.6093}
            initialLon={verifyingRequest.lon || 85.1235}
            initialAddress={verifyingRequest.location_raw || ''}
            districtName={verifyingRequest.district}
            onCancel={() => setVerifyingRequest(null)}
            onLocationConfirm={(loc: SelectedLocationResult) => {
              updateLocationMutation.mutate({
                requestId: verifyingRequest.id,
                lat: loc.lat,
                lon: loc.lon,
                address: loc.address,
                source: loc.source,
                confidence: loc.confidence,
              })
            }}
          />
        </div>
      )}
    </div>
  )
}
