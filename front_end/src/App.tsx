import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = 'ws://localhost:8766'

const PRESET_TASKS = [
  '打开美团，查看我最近的订单状态',
  '打开微信，查看最新消息并告诉我内容',
  '打开支付宝，查询账户余额',
  '打开设置，查看当前WiFi名称',
  '打开相机，帮我拍一张照片',
]

// ── Types ────────────────────────────────────────────────────────────────────

type LogLevel = 'info' | 'warn' | 'error' | 'success'
interface LogEntry { id: number; time: string; level: LogLevel; message: string }
type Status = 'disconnected' | 'idle' | 'running'
interface TapRipple { id: number; xPct: number; yPct: number }

// ── Helpers ───────────────────────────────────────────────────────────────────

const timeNow = () =>
  new Date().toLocaleTimeString('zh-CN', { hour12: false })

const levelColor = (l: LogLevel) =>
  l === 'error' ? '#ef4444' : l === 'warn' ? '#f59e0b' : l === 'success' ? '#10b981' : '#94a3b8'

const levelBg = (l: LogLevel) =>
  l === 'error' ? 'rgba(239,68,68,0.06)' : l === 'warn' ? 'rgba(245,158,11,0.06)' : l === 'success' ? 'rgba(16,185,129,0.06)' : 'transparent'

const levelIcon = (l: LogLevel) =>
  l === 'error' ? '✕' : l === 'warn' ? '⚠' : l === 'success' ? '✓' : '›'

// ── Sub-components ────────────────────────────────────────────────────────────

function ModelBadge({ label }: { label: string }) {
  return (
    <span style={{
      background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.3)',
      color: '#93c5fd', borderRadius: 4, padding: '2px 8px',
      fontSize: 11, fontWeight: 600, letterSpacing: '0.02em',
    }}>{label}</span>
  )
}

function StatusDot({ status }: { status: Status }) {
  const color = status === 'disconnected' ? '#ef4444' : status === 'idle' ? '#10b981' : '#f59e0b'
  const label = status === 'disconnected' ? '未连接' : status === 'idle' ? '就绪' : '执行中'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block',
        boxShadow: status === 'running' ? `0 0 8px ${color}` : 'none',
      }} />
      <span style={{ fontSize: 12, color, fontWeight: 600 }}>{label}</span>
    </div>
  )
}

function AdbStatus({ connected, devices, onRefresh }: {
  connected: boolean; devices: string[]; onRefresh: () => void
}) {
  const borderColor = connected ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'
  const bgColor = connected ? 'rgba(16,185,129,0.07)' : 'rgba(239,68,68,0.07)'
  const textColor = connected ? '#10b981' : '#ef4444'
  return (
    <div style={{
      background: bgColor, border: `1px solid ${borderColor}`,
      borderRadius: 8, padding: '10px 14px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    }}>
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: textColor }}>
          {connected ? '📱 手机已连接' : '📵 手机未连接'}
        </div>
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
          {connected ? devices[0] : 'adb connect IP:端口'}
        </div>
      </div>
      <button onClick={onRefresh} style={{
        background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
        color: '#94a3b8', borderRadius: 6, padding: '4px 10px', fontSize: 11, cursor: 'pointer',
      }}>刷新</button>
    </div>
  )
}

function PhoneFrame({ screenshot, ripples, isRunning }: {
  screenshot: string | null; ripples: TapRipple[]; isRunning: boolean
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
      <div style={{
        width: 280, height: 580,
        background: 'linear-gradient(145deg,#1a1f2e,#0d1117)',
        borderRadius: 40,
        border: `2px solid ${isRunning ? 'rgba(59,130,246,0.5)' : '#1e2f50'}`,
        boxShadow: isRunning
          ? '0 0 24px rgba(59,130,246,0.25), 0 20px 60px rgba(0,0,0,0.6)'
          : '0 20px 60px rgba(0,0,0,0.6)',
        position: 'relative',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        transition: 'border-color 0.4s, box-shadow 0.4s',
      }}>
        {/* notch */}
        <div style={{
          position: 'absolute', top: 14, width: 80, height: 6,
          background: '#0d1117', borderRadius: 3,
        }} />

        {/* screen */}
        <div style={{
          width: 248, height: 520,
          background: '#000', borderRadius: 28,
          overflow: 'hidden', position: 'relative', marginTop: 8,
        }}>
          {screenshot ? (
            <img
              src={`data:image/png;base64,${screenshot}`}
              alt="phone screen"
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
          ) : (
            <div style={{
              width: '100%', height: '100%',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
              gap: 12, color: '#1e2f50',
            }}>
              <div style={{ fontSize: 36 }}>📱</div>
              <div style={{ fontSize: 12, textAlign: 'center', lineHeight: 1.6, color: '#374151' }}>
                连接手机并开始任务<br />截图将实时显示在此
              </div>
            </div>
          )}

          {/* tap ripples */}
          {ripples.map(r => (
            <div key={r.id} style={{
              position: 'absolute',
              left: `${r.xPct}%`, top: `${r.yPct}%`,
              width: 36, height: 36, borderRadius: '50%',
              border: '2px solid #3b82f6',
              animation: 'ripple 0.7s ease-out forwards',
              pointerEvents: 'none',
            }} />
          ))}

          {/* running badge */}
          {isRunning && (
            <div style={{
              position: 'absolute', bottom: 8, right: 8,
              background: 'rgba(59,130,246,0.9)', borderRadius: 12,
              padding: '2px 8px', fontSize: 10, fontWeight: 700, color: '#fff',
              display: 'flex', alignItems: 'center', gap: 4,
            }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#fff' }} />
              AI 执行中
            </div>
          )}
        </div>

        {/* home bar */}
        <div style={{
          position: 'absolute', bottom: 14, width: 80, height: 4,
          background: '#1e2f50', borderRadius: 2,
        }} />
      </div>
      <div style={{ fontSize: 11, color: '#374151', letterSpacing: '0.05em' }}>
        vivo S19 · Android 15 · ADB Mirror
      </div>
    </div>
  )
}

function LogPanel({ logs, onClear }: { logs: LogEntry[]; onClear: () => void }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div style={{
      background: '#0f1729', border: '1px solid #1e2f50',
      borderRadius: 12, display: 'flex', flexDirection: 'column',
      height: '100%', overflow: 'hidden',
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #1e2f50',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0,
      }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>执行日志</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: '#374151' }}>{logs.length} 条</span>
          <button onClick={onClear} style={{
            background: 'none', border: '1px solid #1e2f50',
            color: '#374151', borderRadius: 4, padding: '2px 8px',
            fontSize: 11, cursor: 'pointer',
          }}>清空</button>
        </div>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
        {logs.length === 0 && (
          <div style={{ padding: '32px 16px', color: '#374151', fontSize: 12, textAlign: 'center' }}>
            任务执行日志将在此显示...
          </div>
        )}
        {logs.map(entry => (
          <div key={entry.id} style={{
            padding: '3px 16px', background: levelBg(entry.level),
            display: 'flex', gap: 8, alignItems: 'flex-start',
            animation: 'fadeIn 0.2s ease',
          }}>
            <span style={{ color: levelColor(entry.level), fontSize: 10, minWidth: 10, marginTop: 2 }}>
              {levelIcon(entry.level)}
            </span>
            <span style={{ color: '#374151', fontSize: 10, minWidth: 58, marginTop: 2, flexShrink: 0 }}>
              {entry.time}
            </span>
            <span style={{
              fontSize: 12, color: levelColor(entry.level),
              lineHeight: 1.55, wordBreak: 'break-word', flex: 1,
            }}>{entry.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const [status, setStatus] = useState<Status>('disconnected')
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [task, setTask] = useState('')
  const [adbConnected, setAdbConnected] = useState(false)
  const [adbDevices, setAdbDevices] = useState<string[]>([])
  const [ripples, setRipples] = useState<TapRipple[]>([])
  const [recording, setRecording] = useState(false)
  const [ttsPlaying, setTtsPlaying] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const logIdRef = useRef(0)
  const rippleIdRef = useRef(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  const addLog = useCallback((message: string, level: LogLevel = 'info') => {
    setLogs(prev => [...prev.slice(-400), {
      id: logIdRef.current++, time: timeNow(), level, message,
    }])
  }, [])

  const addRipple = useCallback((xPct: number, yPct: number) => {
    const id = rippleIdRef.current++
    setRipples(prev => [...prev, { id, xPct, yPct }])
    setTimeout(() => setRipples(prev => prev.filter(r => r.id !== id)), 900)
  }, [])

  // Keep fresh refs for WebSocket message handler to avoid stale closures
  const addLogRef = useRef(addLog)
  const addRippleRef = useRef(addRipple)
  useEffect(() => { addLogRef.current = addLog }, [addLog])
  useEffect(() => { addRippleRef.current = addRipple }, [addRipple])

  // ── WebSocket lifecycle ──

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>
    let ws: WebSocket

    const connect = () => {
      ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('idle')
        addLogRef.current('已连接到后端服务', 'success')
        ws.send(JSON.stringify({ type: 'check_adb' }))
      }

      ws.onclose = () => {
        setStatus('disconnected')
        addLogRef.current('与后端断开，5秒后重连...', 'warn')
        reconnectTimer = setTimeout(connect, 5000)
      }

      ws.onerror = () => {
        addLogRef.current('WebSocket 连接失败，请确认: python backend/api_server.py 已启动', 'error')
      }

      ws.onmessage = (e: MessageEvent) => {
        const msg = JSON.parse(e.data as string) as Record<string, unknown>
        const t = msg.type as string

        if (t === 'status') {
          const s = msg.status as Status
          setStatus(prev => (prev === 'disconnected' ? prev : s))
        } else if (t === 'log') {
          addLogRef.current(msg.message as string, msg.level as LogLevel)
        } else if (t === 'screenshot') {
          setScreenshot(msg.data as string)
        } else if (t === 'action_event') {
          const action = msg.action as Record<string, unknown>
          if (action.action === 'tap') {
            // xPct/yPct will be added when we have screen coords from vision grounding
            addRippleRef.current(50, 50)
          }
        } else if (t === 'tts_audio') {
          const b64 = msg.data as string
          try {
            const binary = atob(b64)
            const bytes = new Uint8Array(binary.length)
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
            const blob = new Blob([bytes], { type: 'audio/mp3' })
            const url = URL.createObjectURL(blob)
            const audio = new Audio(url)
            setTtsPlaying(true)
            audio.onended = () => { setTtsPlaying(false); URL.revokeObjectURL(url) }
            audio.play().catch(() => setTtsPlaying(false))
          } catch { setTtsPlaying(false) }
        } else if (t === 'task_transcript') {
          const text = msg.text as string
          setTask(text)
          addLogRef.current(`语音识别: ${text}`, 'info')
        } else if (t === 'adb_status') {
          setAdbConnected(msg.connected as boolean)
          setAdbDevices(msg.devices as string[])
        }
      }
    }

    connect()
    return () => {
      clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])

  const checkAdb = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'check_adb' }))
    }
  }

  const startTask = () => {
    if (!task.trim() || status !== 'idle') return
    wsRef.current?.send(JSON.stringify({ type: 'start_task', task: task.trim() }))
    addLog(`下发任务: ${task.trim()}`)
  }

  const stopTask = () => {
    wsRef.current?.send(JSON.stringify({ type: 'stop_task' }))
  }

  // ── Voice Recording ──

  const startRecording = async () => {
    if (recording || status !== 'idle') return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      mediaRecorderRef.current = mr
      audioChunksRef.current = []
      mr.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data) }
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const ab = await blob.arrayBuffer()
        const bytes = new Uint8Array(ab)
        const b64 = btoa(String.fromCharCode(...Array.from(bytes)))
        const ws = wsRef.current
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'audio_chunk', data: b64 }))
          ws.send(JSON.stringify({ type: 'audio_end' }))
        }
      }
      mr.start()
      setRecording(true)
      addLog('开始录音...')
    } catch {
      addLog('麦克风访问失败，请检查浏览器权限', 'error')
    }
  }

  const stopRecording = () => {
    if (!recording) return
    mediaRecorderRef.current?.stop()
    setRecording(false)
    addLog('录音结束，正在识别...')
  }

  const isRunning = status === 'running'

  // ── Render ──

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#080d1a', overflow: 'hidden' }}>

      {/* ── Header ── */}
      <header style={{
        height: 56, background: '#0f1729', borderBottom: '1px solid #1e2f50',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'linear-gradient(135deg,#3b82f6,#6366f1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
            }}>⚡</div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#e2e8f0', letterSpacing: '-0.01em' }}>
                Step AI · 手机屏幕操控 Agent
              </div>
              <div style={{ fontSize: 10, color: '#374151' }}>
                Multimodal · GUI Grounding · Multi-step Execution · Voice I/O
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <ModelBadge label="step-3.7-flash" />
            <ModelBadge label="stepaudio-2.5-asr" />
            <ModelBadge label="stepaudio-2.5-tts" />
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {ttsPlaying && (
            <span style={{ fontSize: 12, color: '#10b981' }}>🔊 播报中</span>
          )}
          <StatusDot status={status} />
        </div>
      </header>

      {/* ── Body ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', padding: 16, gap: 16 }}>

        {/* Left Panel */}
        <div style={{ width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>

          <AdbStatus connected={adbConnected} devices={adbDevices} onRefresh={checkAdb} />

          {/* Task Card */}
          <div style={{
            background: '#0f1729', border: '1px solid #1e2f50',
            borderRadius: 12, padding: 16,
            display: 'flex', flexDirection: 'column', gap: 10,
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>任务指令</div>

            <textarea
              value={task}
              onChange={e => setTask(e.target.value)}
              placeholder="输入你想让手机完成的任务..."
              disabled={isRunning}
              rows={3}
              style={{
                background: '#141f35', border: '1px solid #1e2f50',
                borderRadius: 8, color: '#e2e8f0', fontSize: 13,
                padding: '10px 12px', resize: 'none', outline: 'none',
                lineHeight: 1.5, width: '100%',
                opacity: isRunning ? 0.5 : 1,
              }}
              onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) startTask() }}
            />

            {/* Voice button */}
            <button
              onMouseDown={startRecording}
              onMouseUp={stopRecording}
              onTouchStart={startRecording}
              onTouchEnd={stopRecording}
              disabled={isRunning || status === 'disconnected'}
              style={{
                background: recording ? 'rgba(239,68,68,0.12)' : 'rgba(59,130,246,0.08)',
                border: `1px solid ${recording ? 'rgba(239,68,68,0.4)' : 'rgba(59,130,246,0.3)'}`,
                color: recording ? '#ef4444' : '#3b82f6',
                borderRadius: 8, padding: '8px 0',
                fontSize: 12, fontWeight: 600, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                opacity: (isRunning || status === 'disconnected') ? 0.35 : 1,
                width: '100%',
              }}
            >
              {recording ? '🔴 松开结束录音' : '🎙 按住语音输入'}
            </button>

            {/* Preset tasks */}
            <div>
              <div style={{ fontSize: 11, color: '#374151', marginBottom: 5 }}>快捷任务</div>
              {PRESET_TASKS.map((t, i) => (
                <button key={i} onClick={() => setTask(t)} disabled={isRunning} style={{
                  display: 'block', width: '100%',
                  background: '#141f35', border: '1px solid #1e2f50',
                  color: '#64748b', borderRadius: 6, padding: '6px 10px',
                  fontSize: 11, textAlign: 'left', cursor: 'pointer',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  marginBottom: 4, opacity: isRunning ? 0.35 : 1,
                }}>{t}</button>
              ))}
            </div>

            {/* Start / Stop */}
            {!isRunning ? (
              <button onClick={startTask} disabled={!task.trim() || status !== 'idle'} style={{
                background: (task.trim() && status === 'idle') ? 'linear-gradient(135deg,#2563eb,#4f46e5)' : '#141f35',
                border: 'none', borderRadius: 8, padding: '10px 0',
                color: '#fff', fontSize: 14, fontWeight: 700,
                cursor: (task.trim() && status === 'idle') ? 'pointer' : 'not-allowed',
                opacity: (task.trim() && status === 'idle') ? 1 : 0.3,
                width: '100%',
              }}>▶ 开始执行</button>
            ) : (
              <button onClick={stopTask} style={{
                background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.4)',
                borderRadius: 8, padding: '10px 0',
                color: '#ef4444', fontSize: 14, fontWeight: 700, cursor: 'pointer', width: '100%',
              }}>⏹ 停止任务</button>
            )}
          </div>

          {/* Info box */}
          <div style={{
            background: 'rgba(59,130,246,0.05)', border: '1px solid rgba(59,130,246,0.18)',
            borderRadius: 8, padding: 12, flex: 1,
          }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#93c5fd', marginBottom: 8 }}>工作原理</div>
            {[
              ['step-3.7-flash', '截图 → 理解屏幕内容'],
              ['step-3.7-flash', '规划动作 + GUI坐标定位'],
              ['ADB', '执行点击/滑动/输入'],
              ['step-3.7-flash', '判断任务是否完成'],
              ['stepaudio-2.5-tts', '语音播报任务结果'],
            ].map(([model, desc], i) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'flex-start' }}>
                <span style={{ color: '#374151', fontSize: 10, minWidth: 14, marginTop: 1 }}>{i + 1}.</span>
                <div>
                  <span style={{ fontSize: 10, color: '#93c5fd', fontWeight: 600 }}>{model}</span>
                  <span style={{ fontSize: 10, color: '#374151' }}> · {desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Center: Phone */}
        <div style={{
          flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#0f1729', border: '1px solid #1e2f50', borderRadius: 16,
        }}>
          <PhoneFrame screenshot={screenshot} ripples={ripples} isRunning={isRunning} />
        </div>

        {/* Right: Logs */}
        <div style={{ width: 340, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
          <LogPanel logs={logs} onClear={() => setLogs([])} />
        </div>

      </div>
    </div>
  )
}
