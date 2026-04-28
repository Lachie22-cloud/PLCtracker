import { useState, useEffect, useRef } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { Layout } from '@/components/Shell'
import FieldHelpProvider from '@/components/FieldHelp'
import { useTheme } from '@/hooks/useTheme'
import { VIOLATIONS, RULES, SAP_STATE, RUNS } from '@/data/governance'
import { PRESETS } from '@/data/presets'
import { NPD } from '@/data/npd'
import { type LiveRun } from '@/screens/Runs'

import OverviewScreen    from '@/screens/Overview'
import ViolationsScreen  from '@/screens/Violations'
import MaterialScreen    from '@/screens/Material'
import RunsScreen        from '@/screens/Runs'
import RulesScreen       from '@/screens/Rules'
import PresetsListScreen, { PresetEditScreen } from '@/screens/Presets'
import NpdListScreen     from '@/screens/NpdList'
import NpdDetailScreen   from '@/screens/NpdDetail'
import NpdBoardScreen    from '@/screens/NpdBoard'
import LifecycleBoard    from '@/screens/LifecycleBoard'
import LifecycleTable    from '@/screens/LifecycleTable'
import LifecycleDashboard from '@/screens/LifecycleDashboard'
import LifecycleUpload   from '@/screens/LifecycleUpload'

interface Toast {
  kind: 'ok' | 'error'
  msg: string
}

function AppInner() {
  const { prefs } = useTheme()
  const navigate = useNavigate()
  const [liveRun, setLiveRun] = useState<LiveRun | null>(null)
  const [toast, setToast] = useState<Toast | null>(null)
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const counts = {
    openViolations: VIOLATIONS.length,
    activeRules: RULES.length,
    presets: PRESETS.length,
    npd: NPD.filter((r: { status: string }) => r.status === 'in_progress' || r.status === 'on_hold').length,
  }

  const startRun = () => {
    if (liveRun && liveRun.status === 'running') return
    navigate('/runs')
    const newId = (RUNS[0]?.id || 100) + 1
    setLiveRun({
      id: newId,
      source: 'SAP OData',
      status: 'running',
      records: 0, mara: 0, marc: 0, changes: 0, violations_rebuilt: 0,
      started: new Date().toISOString(), finished: null, duration_s: 0,
      records_so_far: 0, progress: 5, elapsed_s: 0,
      step: 'Connecting to /sap/opu/odata/sap/MM_MATERIAL_SRV …',
      error: null, user: 'lena.decker@plct.io',
    })
  }

  useEffect(() => {
    if (!liveRun || liveRun.status !== 'running') return
    if (tickRef.current) clearInterval(tickRef.current)

    let elapsed = liveRun.elapsed_s || 0
    let progress = liveRun.progress || 5
    let records = liveRun.records_so_far || 0

    const steps = [
      'Connecting to /sap/opu/odata/sap/MM_MATERIAL_SRV …',
      'Pulling MARA (general material data) …',
      'Pulling MARC (plant data) …',
      'Diffing against last snapshot …',
      'Re-evaluating governance rules …',
      'Persisting violations …',
    ]
    let stepIdx = 0

    tickRef.current = setInterval(() => {
      elapsed += 1
      progress = Math.min(progress + 7 + Math.random() * 4, 100)
      records = Math.min(records + 850 + Math.floor(Math.random() * 600), 18460)
      stepIdx = Math.min(Math.floor(progress / 17), steps.length - 1)

      if (progress >= 100) {
        if (tickRef.current) clearInterval(tickRef.current)
        setLiveRun(prev => prev ? ({
          ...prev,
          status: 'success',
          progress: 100,
          records: 18460, mara: 11252, marc: 18460, changes: 12,
          violations_rebuilt: VIOLATIONS.length,
          finished: new Date().toISOString(),
          duration_s: elapsed,
          step: 'Done.',
        }) : null)
        setToast({ kind: 'ok', msg: 'Extraction completed · 12 new field changes detected.' })
        setTimeout(() => setToast(null), 4500)
      } else {
        setLiveRun(prev => prev ? ({ ...prev, elapsed_s: elapsed, progress, records_so_far: records, step: steps[stepIdx] }) : null)
      }
    }, 700)

    return () => { if (tickRef.current) clearInterval(tickRef.current) }
  }, [liveRun?.status])

  return (
    <FieldHelpProvider>
      <Layout counts={counts} sap={SAP_STATE} onRunNow={startRun}>
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview"   element={<OverviewScreen />} />
          <Route path="/violations" element={<ViolationsScreen />} />
          <Route path="/material"   element={<MaterialScreen />} />
          <Route path="/runs"       element={<RunsScreen liveRun={liveRun} onRunNow={startRun} />} />
          <Route path="/rules"      element={<RulesScreen />} />
          <Route path="/presets"    element={<PresetsListScreen />} />
          <Route path="/presets/:presetId" element={<PresetEditScreen />} />
          <Route path="/npd"        element={<NpdListScreen />} />
          <Route path="/npd/board"  element={<NpdBoardScreen />} />
          <Route path="/npd/:no"    element={<NpdDetailScreen />} />
          <Route path="/lifecycle/board"     element={<LifecycleBoard />} />
          <Route path="/lifecycle/table"     element={<LifecycleTable />} />
          <Route path="/lifecycle/dashboard" element={<LifecycleDashboard />} />
          <Route path="/lifecycle/upload"    element={<LifecycleUpload />} />
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </Layout>

      {toast && (
        <div className="toast-wrap">
          <div className={'toast' + (toast.kind === 'error' ? ' is-error' : '')}>
            <span style={{ color: toast.kind === 'error' ? 'var(--critical)' : 'var(--ok)' }}>
              {toast.kind === 'error' ? '✕' : '✓'}
            </span>
            <span>{toast.msg}</span>
          </div>
        </div>
      )}
    </FieldHelpProvider>
  )
}

export default function App() {
  useTheme()
  return <AppInner />
}
