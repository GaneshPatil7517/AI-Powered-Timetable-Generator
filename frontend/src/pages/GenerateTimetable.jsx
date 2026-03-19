import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { timetableAPI } from '../services/api'

export default function GenerateTimetable() {
  const [loading, setLoading] = useState(false)
  const [timetable, setTimetable] = useState(null)
  const [viewMode, setViewMode] = useState('preview')
  const [error, setError] = useState(null)
  const [hasConfig, setHasConfig] = useState(false)

  // divisions array from backend
  const divisions = timetable?.timetable?.timetable || timetable?.timetable || []

  useEffect(() => {
    checkConfig()
  }, [])

  const checkConfig = async () => {
    try {
      await timetableAPI.getConfig()
      setHasConfig(true)
    } catch (error) {
      setHasConfig(false)
    }
  }

  const handleGenerateSlots = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await timetableAPI.generateSlots()
      setTimetable(response.data)
      setViewMode('preview')
    } catch (error) {
      console.error(error)
      if (error.response?.status === 404) {
        setError('Please save timetable configuration in Input Data > Config tab first.')
      } else {
        setError('Failed to generate time slots. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateAI = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await timetableAPI.generateAITimetable()
      setTimetable(response.data)
      setViewMode('ai')
    } catch (error) {
      console.error(error)
      setError('Failed to generate AI timetable. Make sure you have added divisions, teachers, and subjects.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <h2 className="text-3xl font-bold text-gray-900 mb-6">
        Generate Timetable
      </h2>

      {/* Warning if no config */}
      {!hasConfig && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-yellow-800">
            ⚠️ Please save timetable configuration in <strong>Input Data → Config</strong> tab first to enable "Preview Time Slots".
          </p>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Buttons */}
      <div className="flex gap-4 mb-8">
        <button
          onClick={handleGenerateSlots}
          disabled={loading}
          className="px-6 py-3 rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Preview Time Slots'}
        </button>

        <button
          onClick={handleGenerateAI}
          disabled={loading}
          className="px-6 py-3 rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Generate AI Timetable'}
        </button>
      </div>

      {/* ================= PREVIEW TIME SLOTS VIEW ================= */}
      {viewMode === 'preview' && timetable && (
        <div className="bg-white rounded-xl shadow border">
          <div className="px-6 py-4 bg-blue-50 border-b">
            <h3 className="text-lg font-bold text-blue-700">
              Weekly Time Slots Preview
            </h3>
          </div>
          <div className="p-6 space-y-6">
            {Object.entries(timetable.timetable || {}).map(([day, slots]) => (
              <div key={day}>
                <h4 className="font-semibold text-gray-700 mb-3">{day}</h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                  {slots.map((slot, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg text-center border ${
                        slot.type === 'break'
                          ? 'bg-orange-100 border-orange-300'
                          : 'bg-blue-100 border-blue-300'
                      }`}
                    >
                      <div className="font-semibold text-sm">{slot.time}</div>
                      <div className="text-xs mt-1 capitalize">{slot.type}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ================= AI TIMETABLE VIEW ================= */}
      {viewMode === 'ai' && divisions.length > 0 && (
        <div className="space-y-10">
          {divisions.map((division) => (
            <motion.div
              key={division.division}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-xl shadow border"
            >
              {/* Division Header */}
              <div className="px-6 py-4 bg-green-50 border-b">
                <h3 className="text-lg font-bold text-green-700">
                  Division {division.division}
                </h3>
              </div>

              {/* Days */}
              <div className="p-6 space-y-6">
                {division.days.map((dayObj) => (
                  <div key={dayObj.day}>
                    <h4 className="font-semibold text-gray-700 mb-3">
                      {dayObj.day}
                    </h4>

                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                      {dayObj.slots.map((slot, idx) => (
                        <div
                          key={idx}
                          className={`p-3 rounded-lg text-center border ${
                            slot.type === 'Lab'
                              ? 'bg-purple-100 border-purple-300'
                              : slot.type === 'Theory'
                              ? 'bg-blue-100 border-blue-300'
                              : 'bg-gray-100 border-gray-300'
                          }`}
                        >
                          <div className="font-semibold text-sm">
                            {slot.time}
                          </div>
                          <div className="text-xs mt-1">
                            {slot.subject}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* ================= EMPTY STATE ================= */}
      {!timetable && (
        <div className="text-center text-gray-500 mt-20">
          No timetable generated yet
        </div>
      )}
    </div>
  )
}
