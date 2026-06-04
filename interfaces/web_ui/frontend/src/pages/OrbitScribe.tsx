import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2, RefreshCw, BrainCircuit, Network, Heart, AlertTriangle, TrendingUp, FileText } from 'lucide-react'

interface ReasoningStep {
  step: number
  observation: string
  inference: string
  confidence: number
}

interface Attachment {
  subject: string
  partner: string
  attachment_style: string
  evidence: string[]
  confidence: number
  reasoning: ReasoningStep[]
}

interface Triangulation {
  speaker: string
  target: string
  listener: string
  context: string
  manipulative_score: number
  reasoning: ReasoningStep[]
}

interface Trajectory {
  thread_id: string
  start_sentiment: string
  end_sentiment: string
  trajectory: string
  inflection_points: { date: string; event: string; sentiment_shift: string }[]
  reasoning: ReasoningStep[]
}

interface GraphNode {
  name: string
  role: string
  centrality_score: number
  risk_profile: string
  connections: Record<string, { strength: number; type: string; risk: number }>
}

interface Report {
  success: boolean
  device_owner: string
  timestamp: string
  risk_level: string
  llm_used: boolean
  mode: string
  overall_narrative: string
  llm_reasoning_summary: string
  attachment_analyses: Attachment[]
  triangulation_events: Triangulation[]
  emotional_trajectories: Trajectory[]
  relationship_graph: GraphNode[]
}

const styleColors: Record<string, string> = {
  secure: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  anxious: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  avoidant: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  disorganized: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
}

const trajColors: Record<string, string> = {
  improving: 'text-green-400',
  stable: 'text-blue-400',
  declining: 'text-red-400',
  volatile: 'text-yellow-400',
}

const riskColors: Record<string, string> = {
  low: 'bg-green-500/20 text-green-400 border-green-500/40',
  moderate: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
  critical: 'bg-red-500/20 text-red-400 border-red-500/40',
}

export function OrbitScribe() {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('synthetic')
  const [error, setError] = useState('')

  const runAnalysis = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/unified/demo/orbitscribe/analyze?mode=${mode}`)
      const data = await res.json()
      if (data.success) {
        setReport(data)
      } else {
        setError(data.error || 'Analysis failed')
      }
    } catch (e) {
      setError(String(e))
    }
    setLoading(false)
  }

  useEffect(() => {
    runAnalysis()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <BrainCircuit className="h-6 w-6 text-purple-400" />
            OrbitScribe Relationship Engine
          </h1>
          <p className="text-sm text-muted-foreground">
            LLM-powered relationship reasoning with chain-of-thought evidence
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={mode} onValueChange={setMode}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="synthetic">⚡ Instant Demo</SelectItem>
              <SelectItem value="auto">🤖 Auto (LLM fallback)</SelectItem>
              <SelectItem value="llm">🧠 Full LLM (slow)</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={runAnalysis} disabled={loading} size="sm">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            <span className="ml-2">{loading ? 'Analyzing...' : 'Run Analysis'}</span>
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-red-400">
          {error}
        </div>
      )}

      {report && (
        <>
          {/* Risk Banner */}
          <div className={`rounded-xl border p-6 ${riskColors[report.risk_level] || riskColors.low}`}>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold uppercase">Overall Risk: {report.risk_level}</h2>
                <p className="mt-1 text-sm opacity-80 whitespace-pre-line">{report.llm_reasoning_summary}</p>
              </div>
              <Badge variant="outline" className={report.llm_used ? 'border-green-500/40 text-green-400' : 'border-yellow-500/40 text-yellow-400'}>
                {report.llm_used ? '🤖 LLM Reasoning' : '📊 Synthetic Demo'}
              </Badge>
            </div>
          </div>

          {/* Narrative */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" />
                Narrative Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
                {report.overall_narrative}
              </p>
            </CardContent>
          </Card>

          {/* Attachment Analyses */}
          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-lg font-semibold">
              <Heart className="h-5 w-5 text-green-400" />
              Attachment Analyses ({report.attachment_analyses.length})
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              {report.attachment_analyses.map((a, i) => (
                <Card key={i} className="border-l-4 border-l-purple-500">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">{a.subject} ↔ {a.partner}</CardTitle>
                      <Badge className={styleColors[a.attachment_style] || ''}>{a.attachment_style}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="text-xs text-muted-foreground">
                      Confidence: {(a.confidence * 100).toFixed(0)}%
                    </div>
                    <div className="space-y-1">
                      {a.evidence.slice(0, 3).map((ev, j) => (
                        <p key={j} className="text-xs italic text-muted-foreground">"{ev}"</p>
                      ))}
                    </div>
                    <div className="space-y-1">
                      {a.reasoning.map((r) => (
                        <div key={r.step} className="rounded bg-muted p-2 text-xs">
                          <span className="font-semibold text-primary">Step {r.step}:</span>{' '}
                          <span className="text-muted-foreground">{r.observation}</span> →{' '}
                          <span className="text-foreground">{r.inference}</span>
                          <span className="ml-2 text-[10px] opacity-60">({(r.confidence * 100).toFixed(0)}%)</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Triangulation Events */}
          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-lg font-semibold">
              <AlertTriangle className="h-5 w-5 text-red-400" />
              Triangulation Events ({report.triangulation_events.length})
            </h3>
            <div className="space-y-3">
              {report.triangulation_events.map((t, i) => (
                <Card key={i} className="border-l-4 border-l-red-500">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        {t.speaker} → {t.listener} <span className="text-muted-foreground">(about {t.target})</span>
                      </CardTitle>
                      <Badge variant="outline" className={t.manipulative_score > 0.7 ? 'border-red-500/40 text-red-400' : 'border-yellow-500/40 text-yellow-400'}>
                        Score: {(t.manipulative_score * 100).toFixed(0)}%
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-xs italic text-muted-foreground">"{t.context}"</p>
                    <div className="space-y-1">
                      {t.reasoning.map((r) => (
                        <div key={r.step} className="rounded bg-muted p-2 text-xs">
                          <span className="font-semibold text-primary">Step {r.step}:</span>{' '}
                          <span className="text-muted-foreground">{r.observation}</span> →{' '}
                          <span className="text-foreground">{r.inference}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Emotional Trajectories */}
          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-lg font-semibold">
              <TrendingUp className="h-5 w-5 text-blue-400" />
              Emotional Trajectories ({report.emotional_trajectories.length})
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              {report.emotional_trajectories.map((et, i) => (
                <Card key={i}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">{et.thread_id}</CardTitle>
                      <Badge variant="outline" className={trajColors[et.trajectory] || ''}>
                        {et.trajectory}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="text-xs text-muted-foreground">
                      {et.start_sentiment} → {et.end_sentiment}
                    </div>
                    <div className="space-y-1">
                      {et.inflection_points.map((p, j) => (
                        <div key={j} className="rounded bg-muted p-2 text-xs">
                          <span className="font-semibold">{p.date}:</span> {p.event}
                          <span className="ml-2 opacity-60">({p.sentiment_shift})</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Relationship Graph */}
          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-lg font-semibold">
              <Network className="h-5 w-5 text-yellow-400" />
              Relationship Graph ({report.relationship_graph.length} nodes)
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              {report.relationship_graph.map((n, i) => (
                <Card key={i}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">{n.name}</CardTitle>
                      <Badge variant="outline" className={riskColors[n.risk_profile] || ''}>
                        {n.risk_profile}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="text-xs text-muted-foreground">
                      Role: {n.role} | Centrality: {(n.centrality_score * 100).toFixed(0)}%
                    </div>
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b text-muted-foreground">
                          <th className="pb-1 text-left">To</th>
                          <th className="pb-1 text-left">Type</th>
                          <th className="pb-1 text-left">Strength</th>
                          <th className="pb-1 text-left">Risk</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(n.connections).map(([name, conn]) => (
                          <tr key={name} className="border-b border-border/50">
                            <td className="py-1">{name}</td>
                            <td className="py-1 capitalize">{conn.type}</td>
                            <td className="py-1">
                              <div className="h-1.5 w-16 rounded-full bg-muted">
                                <div
                                  className="h-1.5 rounded-full bg-primary"
                                  style={{ width: `${conn.strength * 100}%` }}
                                />
                              </div>
                            </td>
                            <td className="py-1">{(conn.risk * 100).toFixed(0)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
