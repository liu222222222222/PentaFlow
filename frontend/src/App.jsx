import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Play, Square, Terminal, Activity, ChevronDown, ChevronUp, Zap, TrendingUp, GitBranch } from 'lucide-react'
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts'
import './App.css'

// API 配置
const API_BASE = window.location.origin + '/api/v1'
const WS_URL = (() => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/ws/progress`
})()

// 智能体配置
const AGENT_CONFIG = {
  '资本代言人': { icon: '🏦', color: '#ffd700', role: 'Capital' },
  '技术执行者': { icon: '🔧', color: '#58a6ff', role: 'Tech' },
  '创意指挥官': { icon: '🎨', color: '#f778ba', role: 'Creative' },
  '社会观察员': { icon: '👁️', color: '#a371f7', role: 'Social' },
  '政策监管者': { icon: '⚖️', color: '#39c5cf', role: 'Policy' },
  '用户代表': { icon: '👤', color: '#7ee787', role: 'User' },
  '旁观者': { icon: '🤔', color: '#ff7b72', role: 'Observer' }
}

// 五维配置 (与后端 metrics 键名对应)
const DIMENSIONS = [
  { key: 'technology_penetration', name: '技术渗透', color: '#58a6ff' },
  { key: 'economic_disruption', name: '经济颠覆', color: '#ffd700' },
  { key: 'employment_volatility', name: '就业波动', color: '#f778ba' },
  { key: 'process_reconstruction', name: '流程重构', color: '#a371f7' },
  { key: 'ethical_risk', name: '伦理风险', color: '#39c5cf' }
]

// 矩阵背景组件
function MatrixBackground() {
  const canvasRef = useRef(null)
  
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
    
    const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン'
    const fontSize = 14
    const columns = canvas.width / fontSize
    const drops = Array(Math.floor(columns)).fill(1)
    
    let animationId
    const draw = () => {
      ctx.fillStyle = 'rgba(13, 17, 23, 0.05)'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      
      ctx.fillStyle = '#0f0'
      ctx.font = `${fontSize}px monospace`
      
      for (let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)]
        ctx.fillStyle = `rgba(0, 255, 0, ${Math.random() * 0.3})`
        ctx.fillText(text, i * fontSize, drops[i] * fontSize)
        
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
          drops[i] = 0
        }
        drops[i]++
      }
      
      animationId = requestAnimationFrame(draw)
    }
    
    draw()
    
    const handleResize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    window.addEventListener('resize', handleResize)
    
    return () => {
      cancelAnimationFrame(animationId)
      window.removeEventListener('resize', handleResize)
    }
  }, [])
  
  return <canvas ref={canvasRef} className="matrix-bg" />
}

// 五维星图组件
function RadarChartComponent({ metrics, previousMetrics, round }) {
  const safeMetrics = metrics || {}
  const prevMetrics = previousMetrics || {}
  
  const data = DIMENSIONS.map(dim => ({
    dimension: dim.name,
    current: Math.round((safeMetrics[dim.key] || 0) * 100),
    previous: prevMetrics[dim.key] ? Math.round((prevMetrics[dim.key] || 0) * 100) : 0,
    fullMark: 100
  }))

  return (
    <div className="radar-chart-container">
      <h4 className="radar-title">
        <TrendingUp size={16} /> 五维影响力分析 - Round {round}
      </h4>
      <ResponsiveContainer width="100%" height={200}>
        <RadarChart cx="50%" cy="50%" outerRadius="60%" data={data}>
          <PolarGrid stroke="#30363d" />
          <PolarAngleAxis dataKey="dimension" tick={{ fill: '#8b949e', fontSize: 11 }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
          {previousMetrics && (
            <Radar
              name="上一轮"
              dataKey="previous"
              stroke="#8b949e"
              strokeWidth={1}
              fill="#8b949e"
              fillOpacity={0.1}
            />
          )}
          <Radar
            name="当前轮次"
            dataKey="current"
            stroke="#58a6ff"
            strokeWidth={2}
            fill="#58a6ff"
            fillOpacity={0.3}
          />
        </RadarChart>
      </ResponsiveContainer>
      <div className="dimension-scores">
        {DIMENSIONS.map(dim => {
          const score = Math.round((safeMetrics[dim.key] || 0) * 100)
          const prevScore = prevMetrics[dim.key] ? Math.round((prevMetrics[dim.key] || 0) * 100) : null
          const change = prevScore !== null ? score - prevScore : null
          return (
            <div key={dim.key} className="dimension-score">
              <span className="dim-name" style={{ color: dim.color }}>{dim.name}</span>
              <span className="dim-value">{score}</span>
              {change !== null && change !== 0 && (
                <span className={`dim-change ${change >= 0 ? 'positive' : 'negative'}`}>
                  {change >= 0 ? '+' : ''}{change}
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// 控制台组件
function Console({ logs, isActive }) {
  const consoleEndRef = useRef(null)
  
  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])
  
  return (
    <div className={`console-container ${isActive ? 'active' : ''}`}>
      <div className="console-header">
        <Terminal size={16} />
        <span>SYSTEM CONSOLE</span>
        {isActive && <span className="live-badge">LIVE</span>}
      </div>
      <div className="console-content">
        {logs.length === 0 ? (
          <div className="console-line system">
            <span className="timestamp">[{new Date().toLocaleTimeString()}]</span>
            <span className="message">等待推演开始...</span>
          </div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className={`console-line ${log.type}`}>
              <span className="timestamp">[{log.time}]</span>
              <span className="message">{log.message}</span>
            </div>
          ))
        )}
        <div ref={consoleEndRef} />
      </div>
    </div>
  )
}

// 智能体面板组件
function AgentPanel({ name, status, progress, opinion }) {
  const config = AGENT_CONFIG[name] || { icon: '🤖', color: '#888', role: 'Unknown' }
  
  // 从 scores 中获取该智能体的主要评分
  const scores = opinion?.scores || {}
  const mainScore = Object.values(scores)[0] || null
  
  // 获取分析摘要
  const reasoning = opinion?.reasoning || ''
  const summary = reasoning.length > 80 ? reasoning.substring(0, 80) + '...' : reasoning
  
  return (
    <motion.div 
      className={`agent-panel ${status}`}
      animate={{ 
        borderColor: status === 'analyzing' ? config.color : '#30363d',
        boxShadow: status === 'analyzing' ? `0 0 20px ${config.color}40` : 'none'
      }}
    >
      <div className="agent-header">
        <div className="agent-avatar" style={{ borderColor: config.color }}>
          {config.icon}
        </div>
        <div className="agent-info">
          <div className="agent-name">{name}</div>
          <div className="agent-role">
            {config.role}
            {mainScore !== null && (
              <span className="agent-score"> | 评分: {(mainScore * 100).toFixed(0)}</span>
            )}
          </div>
        </div>
        <span className={`status-badge ${status}`}>{status.toUpperCase()}</span>
      </div>
      <div className="agent-progress">
        <div className="progress-bar">
          <motion.div 
            className="progress-fill"
            style={{ backgroundColor: config.color }}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>
      <div className="agent-output">{summary || 'Waiting...'}</div>
    </motion.div>
  )
}

// Markdown 渲染组件
function MarkdownRenderer({ content }) {
  if (!content) return <div className="markdown-content">无内容</div>
  
  // 简单的 markdown 解析
  const renderMarkdown = (text) => {
    // 处理代码块
    text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
    
    // 处理行内代码
    text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    
    // 处理标题
    text = text.replace(/^### (.*$)/gim, '<h3 class="md-h3">$1</h3>')
    text = text.replace(/^## (.*$)/gim, '<h2 class="md-h2">$1</h2>')
    text = text.replace(/^# (.*$)/gim, '<h1 class="md-h1">$1</h1>')
    
    // 处理粗体
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    
    // 处理斜体
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>')
    
    // 处理列表
    text = text.replace(/^\s*[-*+]\s+(.*$)/gim, '<li class="md-li">$1</li>')
    text = text.replace(/(<li[^>]*>.*<\/li>)/s, '<ul class="md-ul">$1</ul>')
    
    // 处理数字列表
    text = text.replace(/^\s*\d+\.\s+(.*$)/gim, '<li class="md-li">$1</li>')
    
    // 处理引用
    text = text.replace(/^>\s*(.*$)/gim, '<blockquote class="md-quote">$1</blockquote>')
    
    // 处理分隔线
    text = text.replace(/^---$/gim, '<hr class="md-hr" />')
    
    // 处理换行
    text = text.replace(/\n/g, '<br />')
    
    return text
  }
  
  return (
    <div 
      className="markdown-content"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  )
}

// 观点展示组件
function OpinionCard({ opinion }) {
  const config = AGENT_CONFIG[opinion.agent_name] || { icon: '🤖', color: '#888', role: 'Unknown' }
  const scores = opinion.scores || {}
  
  // 格式化评分显示
  const scoreEntries = Object.entries(scores).slice(0, 3) // 最多显示3个维度
  
  return (
    <div className="opinion-card">
      <div className="opinion-header">
        <span className="opinion-icon" style={{ color: config.color }}>{config.icon}</span>
        <span className="opinion-name">{opinion.agent_name}</span>
        <span className="opinion-perspective">({opinion.perspective})</span>
      </div>
      {scoreEntries.length > 0 && (
        <div className="opinion-scores">
          {scoreEntries.map(([key, value]) => (
            <span key={key} className="opinion-score-tag">
              {key}: {(value * 100).toFixed(0)}
            </span>
          ))}
        </div>
      )}
      <div className="opinion-reasoning">
        <MarkdownRenderer content={opinion.reasoning} />
      </div>
    </div>
  )
}

// 思维演变线组件
function EvolutionTimeline({ rounds }) {
  return (
    <div className="evolution-timeline">
      <h4><GitBranch size={16} /> 思维演变线</h4>
      <div className="timeline-track">
        {rounds.map((round, index) => (
          <div key={round.round} className="timeline-node">
            <div className={`node-dot ${round.status}`}>
              {index + 1}
            </div>
            <div className="node-content">
              <span className="node-round">Round {round.round}</span>
              <span className="node-score">{round.composite_score?.toFixed(3) || 'N/A'}</span>
            </div>
            {index < rounds.length - 1 && <div className="node-connector" />}
          </div>
        ))}
      </div>
    </div>
  )
}

// 轮次卡片组件
function RoundCard({ round, data, onContinue, onTerminate, isLatest, previousRound }) {
  const [expanded, setExpanded] = useState(true)
  const [showOpinions, setShowOpinions] = useState(false)
  
  // 获取智能体对应的分析结果
  const getAgentOpinion = (agentName) => {
    if (!data.agent_opinions) return null
    return data.agent_opinions.find(op => op.agent_name === agentName)
  }
  
  // 获取非旁观者观点
  const otherOpinions = (data.agent_opinions || []).filter(op => op.agent_name !== '旁观者')
  const bystanderOpinion = (data.agent_opinions || []).find(op => op.agent_name === '旁观者')
  
  return (
    <motion.div 
      className="round-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      <div className="round-header" onClick={() => setExpanded(!expanded)}>
        <div className="round-title">
          <Zap size={18} />
          <span>Round {round}</span>
          {data.status === 'completed' && (
            <span className="score-badge">Score: {data.composite_score?.toFixed(3) || 'N/A'}</span>
          )}
        </div>
        <button className="expand-btn">
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
      </div>
      
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            {/* 智能体网格 */}
            <div className="agent-grid">
              {Object.keys(AGENT_CONFIG).map(agentName => {
                const agentData = data.agents?.[agentName] || { status: 'idle', progress: 0 }
                const opinion = getAgentOpinion(agentName)
                return (
                  <AgentPanel
                    key={agentName}
                    name={agentName}
                    status={agentData.status}
                    progress={agentData.progress}
                    opinion={opinion}
                  />
                )
              })}
            </div>
            
            {/* 控制台日志 */}
            <Console logs={data.logs || []} isActive={data.status === 'running'} />
            
            {/* 报告区域 - 只在完成时显示 */}
            {data.status === 'completed' && (
              <motion.div 
                className="report-section"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                {/* 五维星图 */}
                <RadarChartComponent 
                  metrics={data.metrics} 
                  previousMetrics={previousRound?.metrics}
                  round={round}
                />
                
                {/* 各方观点汇总 */}
                <div className="opinions-section">
                  <h4 onClick={() => setShowOpinions(!showOpinions)} style={{ cursor: 'pointer' }}>
                    📋 各方观点汇总 {showOpinions ? '▼' : '▶'}
                  </h4>
                  {showOpinions && (
                    <div className="opinions-grid">
                      {otherOpinions.map((opinion, idx) => (
                        <OpinionCard key={idx} opinion={opinion} />
                      ))}
                    </div>
                  )}
                </div>
                
                {/* 旁观者总结 */}
                {bystanderOpinion && (
                  <div className="bystander-section">
                    <h4>🤔 旁观者总结</h4>
                    <div className="bystander-content">
                      <MarkdownRenderer content={bystanderOpinion.reasoning} />
                    </div>
                  </div>
                )}
                
                {/* 操作按钮 */}
                {isLatest && (
                  <motion.div 
                    className="action-buttons"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                  >
                    <button className="btn-continue" onClick={onContinue}>
                      <Play size={16} /> 继续推演
                    </button>
                    <button className="btn-terminate" onClick={onTerminate}>
                      <Square size={16} /> 终止推演
                    </button>
                  </motion.div>
                )}
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// API Key 配置弹窗组件
function ApiKeyModal({ onSave, onClose }) {
  const [llmKey, setLlmKey] = useState(localStorage.getItem('llm_api_key') || '')
  const [searchKey, setSearchKey] = useState(localStorage.getItem('search_api_key') || '')
  
  const handleSave = () => {
    if (!llmKey.trim() || !searchKey.trim()) {
      alert('请填写两个 API Key')
      return
    }
    localStorage.setItem('llm_api_key', llmKey.trim())
    localStorage.setItem('search_api_key', searchKey.trim())
    onSave()
  }
  
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>🔑 API Key 配置</h2>
        <p className="modal-desc">欢迎使用 PentaFlow 五维推演系统！请先配置 API Key 以使用完整功能。</p>
        
        <div className="form-group">
          <label style={{ color: '#ff6b6b' }}>* LLM API Key (必填)</label>
          <input 
            type="password" 
            value={llmKey}
            onChange={(e) => setLlmKey(e.target.value)}
            placeholder="请输入阿里百炼 API Key"
          />
          <div className="help-text">
            <a href="https://www.aliyun.com/benefit/ai/aistar" target="_blank" rel="noopener noreferrer">
              📝 点击注册阿里百炼获取 API Key
            </a>
            <br />
            <small>使用模型：qwen3.5-plus（阿里云 DashScope）</small>
          </div>
        </div>
        
        <div className="form-group">
          <label style={{ color: '#ff6b6b' }}>* 搜索 API Key (必填)</label>
          <input 
            type="password" 
            value={searchKey}
            onChange={(e) => setSearchKey(e.target.value)}
            placeholder="请输入 Tavily API Key"
          />
          <div className="help-text">
            <a href="https://www.tavily.com/" target="_blank" rel="noopener noreferrer">
              📝 点击注册 Tavily 获取 API Key
            </a>
            <br />
            <small>使用 Tavily 搜索 API，效果更好且稳定</small>
          </div>
        </div>
        
        <button className="btn-save" onClick={handleSave}>
          ✅ 保存配置并开始使用
        </button>
      </div>
    </div>
  )
}

// 主应用组件
function App() {
  const [eventName, setEventName] = useState('')
  const [eventDesc, setEventDesc] = useState('')
  const [eventCategory, setEventCategory] = useState('技术突破')
  const [rounds, setRounds] = useState([])
  const [currentRound, setCurrentRound] = useState(0)
  const [isRunning, setIsRunning] = useState(false)
  const [taskId, setTaskId] = useState(null)
  const [showKeyModal, setShowKeyModal] = useState(false)
  const [showSummaryModal, setShowSummaryModal] = useState(false)
  
  const wsRef = useRef(null)
  const currentRoundRef = useRef(0)
  
  // 检查 API Key
  useEffect(() => {
    const llmKey = localStorage.getItem('llm_api_key')
    const searchKey = localStorage.getItem('search_api_key')
    if (!llmKey || !searchKey) {
      setShowKeyModal(true)
    }
  }, [])
  
  useEffect(() => {
    currentRoundRef.current = currentRound
  }, [currentRound])
  
  // WebSocket 连接
  const connectWebSocket = useCallback((tid) => {
    if (wsRef.current) {
      wsRef.current.close()
    }
    
    const websocket = new WebSocket(WS_URL)
    
    websocket.onopen = () => {
      websocket.send(JSON.stringify({ type: 'register_task', task_id: tid }))
    }
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleWebSocketMessage(data)
    }
    
    wsRef.current = websocket
  }, [])
  
  // 处理 WebSocket 消息
  const handleWebSocketMessage = (data) => {
    if (data.type === 'task_registered') return
    
    const progress = data.progress_data || data
    const round = currentRoundRef.current || 1
    
    setRounds(prev => {
      const newRounds = [...prev]
      const roundIndex = round - 1
      
      if (!newRounds[roundIndex]) {
        newRounds[roundIndex] = {
          round,
          status: 'running',
          agents: {},
          logs: [],
          agent_opinions: [],
          composite_score: 0,
          metrics: {}
        }
      }
      
      const roundData = newRounds[roundIndex]
      
      switch (progress.status) {
        case 'started':
          roundData.logs.push({ time: new Date().toLocaleTimeString(), message: `推演开始: ${progress.event_name}`, type: 'system' })
          break
          
        case 'agent_searching':
          roundData.agents[progress.agent_name] = { status: 'searching', progress: 20 }
          roundData.logs.push({ time: new Date().toLocaleTimeString(), message: `[${progress.agent_name}] 搜索中...`, type: 'info' })
          break
          
        case 'agent_analyzing':
          roundData.agents[progress.agent_name] = { status: 'analyzing', progress: 60 }
          roundData.logs.push({ time: new Date().toLocaleTimeString(), message: `[${progress.agent_name}] 分析中...`, type: 'agent' })
          break
          
        case 'agent_completed':
          roundData.agents[progress.agent_name] = { status: 'complete', progress: 100 }
          roundData.logs.push({ 
            time: new Date().toLocaleTimeString(), 
            message: `[${progress.agent_name}] 分析完成`, 
            type: 'success' 
          })
          break
          
        case 'round_completed':
          roundData.status = 'completed'
          roundData.agent_opinions = progress.agent_opinions || []
          roundData.composite_score = progress.composite_score
          roundData.metrics = progress.metrics || {}
          roundData.logs.push({ 
            time: new Date().toLocaleTimeString(), 
            message: `✓ Round ${round} 完成! 综合得分: ${progress.composite_score?.toFixed(3)}`, 
            type: 'success' 
          })
          setIsRunning(false)
          break
          
        case 'error':
          roundData.logs.push({ time: new Date().toLocaleTimeString(), message: `Error: ${progress.message}`, type: 'error' })
          setIsRunning(false)
          break
      }
      
      return newRounds
    })
  }
  
  // 自动补全事件信息
  const enrichEvent = async () => {
    if (!eventName || eventName.length < 3) return
    
    try {
      const response = await fetch(`${API_BASE}/events/enrich`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: eventName,
          llm_api_key: localStorage.getItem('llm_api_key') || '',
          search_api_key: localStorage.getItem('search_api_key') || ''
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.description && !eventDesc) {
          setEventDesc(data.description)
        }
        if (data.category && data.category !== '其他') {
          setEventCategory(data.category)
        }
      }
    } catch (error) {
      console.error('Enrich failed:', error)
    }
  }
  
  // 开始分析
  const startAnalysis = async () => {
    // 如果没有描述，先尝试补全
    if (!eventDesc && eventName) {
      await enrichEvent()
    }
    
    const name = eventName || 'OpenClaw在国内的爆火'
    const desc = eventDesc || 'OpenClaw是一款开源AI Agent项目，近期在中国市场迅速爆火，GitHub星标数超越众多经典项目。'
    
    setEventName(name)
    setEventDesc(desc)
    
    setIsRunning(true)
    setCurrentRound(1)
    
    try {
      const response = await fetch(`${API_BASE}/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: {
            id: 'event_' + Date.now(),
            name: name,
            description: desc,
            category: eventCategory,
            timestamp: new Date().toISOString()
          },
          llm_api_key: localStorage.getItem('llm_api_key') || '',
          search_api_key: localStorage.getItem('search_api_key') || ''
        })
      })
      
      const data = await response.json()
      setTaskId(data.task_id)
      connectWebSocket(data.task_id)
      
    } catch (error) {
      console.error('Start analysis failed:', error)
      setIsRunning(false)
    }
  }
  
  // 继续下一轮
  const continueRound = async () => {
    const nextRound = currentRound + 1
    setCurrentRound(nextRound)
    setIsRunning(true)
    
    try {
      await fetch(`${API_BASE}/analysis/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          action: 'next_round',
          round: currentRound
        })
      })
    } catch (error) {
      console.error('Continue failed:', error)
    }
  }
  
  // 推演总结弹窗组件
function SummaryModal({ rounds, eventName, onClose }) {
  const [summary, setSummary] = useState('')
  const [timeline, setTimeline] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    generateSummary()
  }, [])
  
  const generateSummary = async () => {
    try {
      // 构建各轮数据
      const roundsData = rounds.map(r => ({
        round: r.round,
        composite_score: r.composite_score,
        metrics: r.metrics,
        agent_opinions: r.agent_opinions?.map(op => ({
          agent_name: op.agent_name,
          perspective: op.perspective,
          reasoning: op.reasoning,
          scores: op.scores
        })) || []
      }))
      
      const response = await fetch(`${API_BASE}/analysis/generate_timeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rounds: roundsData,
          event_name: eventName,
          llm_api_key: localStorage.getItem('llm_api_key') || ''
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        
        // 处理返回的数据
        let timelineData = data.timeline || []
        let trendSummary = data.overall_trend || ''
        
        // 如果 overall_trend 是 JSON 字符串（包含 timeline），需要解析
        if (typeof trendSummary === 'string' && trendSummary.includes('"timeline"')) {
          try {
            const parsed = JSON.parse(trendSummary)
            if (parsed.timeline) {
              timelineData = parsed.timeline
            }
            if (parsed.overall_trend) {
              trendSummary = parsed.overall_trend
            }
          } catch (e) {
            // 解析失败，使用原始字符串
          }
        }
        
        setTimeline(timelineData)
        setSummary(trendSummary || '生成总结失败')
      } else {
        setSummary('生成总结失败，请稍后重试')
      }
    } catch (error) {
      console.error('Generate summary failed:', error)
      setSummary('生成总结时出错')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content summary-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📊 推演总结报告</h2>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>
        
        {loading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>正在生成多轮推演总结...</p>
          </div>
        ) : (
          <div className="summary-content">
            {/* 时间线 */}
            {timeline && timeline.length > 0 && (
              <div className="timeline-section">
                <h3>🔄 推演时间线</h3>
                {timeline.map((round, idx) => (
                  <div key={idx} className="timeline-round">
                    <h4>{round.title || `第${round.round}轮`}</h4>
                    {round.agents && (
                      <div className="agent-views">
                        {round.agents.map((agent, aidx) => (
                          <div key={aidx} className="agent-view-item">
                            <strong>{agent.name}:</strong> {agent.core_view}
                            {agent.change && agent.change !== '与上一轮对比（第1轮无此项）' && (
                              <span className="view-change">→ {agent.change}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {round.bystander && (
                      <div className="bystander-round-summary">
                        <strong>旁观者:</strong> {round.bystander.summary}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {/* 整体趋势 */}
            <div className="overall-trend">
              <h3>📈 整体趋势分析</h3>
              <MarkdownRenderer content={summary} />
            </div>
          </div>
        )}
        
        <div className="modal-footer">
          <button className="btn-close-modal" onClick={onClose}>关闭</button>
        </div>
      </div>
    </div>
  )
}

// 终止推演
  const terminateSimulation = () => {
    // 如果有多个轮次，显示总结弹窗
    if (rounds.length > 1) {
      setShowSummaryModal(true)
    }
  }
  
  return (
    <div className="app">
      {/* API Key 弹窗 */}
      {showKeyModal && (
        <ApiKeyModal 
          onSave={() => setShowKeyModal(false)} 
        />
      )}
      
      {/* 推演总结弹窗 */}
      {showSummaryModal && (
        <SummaryModal 
          rounds={rounds}
          eventName={eventName}
          onClose={() => setShowSummaryModal(false)}
        />
      )}
      
      {/* 重新配置按钮 */}
      <button 
        className="btn-reconfigure"
        onClick={() => setShowKeyModal(true)}
        title="重新配置 API Key"
      >
        🔑 配置 Key
      </button>
      
      <MatrixBackground />
      
      <header className="app-header">
        <h1>PentaFlow <span className="highlight">五维推演</span></h1>
        <p>AI Impact Analysis System</p>
      </header>
      
      <main className="app-main">
        {/* 输入区域 */}
        <section className="input-section">
          <div className="input-card">
            <h2><Activity size={20} /> Event Input</h2>
            <div className="form-group">
              <label>Event Name</label>
              <input 
                type="text" 
                value={eventName}
                onChange={(e) => setEventName(e.target.value)}
                placeholder="Enter event name..."
                disabled={isRunning}
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea 
                value={eventDesc}
                onChange={(e) => setEventDesc(e.target.value)}
                placeholder="Enter event description..."
                rows={4}
                disabled={isRunning}
              />
            </div>
            <div className="form-group">
              <label>Category</label>
              <select 
                value={eventCategory}
                onChange={(e) => setEventCategory(e.target.value)}
                disabled={isRunning}
              >
                <option>技术突破</option>
                <option>产品发布</option>
                <option>政策法规</option>
                <option>行业应用</option>
                <option>投资并购</option>
                <option>其他</option>
              </select>
            </div>
            {/* 按钮组 */}
            <div className="button-group">
              <button 
                className={`btn-enrich ${eventDesc ? 'completed' : ''}`}
                onClick={enrichEvent}
                disabled={isRunning || !eventName || eventName.length < 3 || eventDesc}
              >
                {eventDesc ? '✓ Enriched' : 'Enrich Event'}
              </button>
              <button 
                className="btn-start"
                onClick={startAnalysis}
                disabled={isRunning || !eventDesc}
              >
                <Play size={18} />
                {isRunning ? 'Analyzing...' : 'Start Analysis'}
              </button>
            </div>
          </div>
          
          {/* 思维演变线 */}
          {rounds.length > 0 && <EvolutionTimeline rounds={rounds} />}
        </section>
        
        {/* 轮次瀑布流 */}
        <section className="rounds-section">
          <AnimatePresence>
            {rounds.map((round, index) => (
              <RoundCard
                key={round.round}
                round={round.round}
                data={round}
                isLatest={index === rounds.length - 1}
                previousRound={index > 0 ? rounds[index - 1] : null}
                onContinue={continueRound}
                onTerminate={terminateSimulation}
              />
            ))}
          </AnimatePresence>
          
          {rounds.length === 0 && !isRunning && (
            <div className="empty-state">
              <Terminal size={48} />
              <p>Enter an event and start analysis</p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App