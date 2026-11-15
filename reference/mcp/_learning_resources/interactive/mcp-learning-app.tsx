import React, { useState, useEffect } from 'react';
import { Book, Play, CheckCircle, ChevronRight, ChevronDown, Code, Server, Laptop, ArrowRight, RefreshCw, Zap, AlertCircle, Award } from 'lucide-react';

const lessons = [
  {
    id: 'intro',
    title: '1. What is MCP?',
    sections: [
      {
        title: 'Definition',
        content: 'MCP = Model Context Protocol\n\nA standard way for AI agents to call external tools.',
        keyPoints: ['Standard interface', 'Language-agnostic', 'Plug-and-play tools'],
        analogy: 'Think of MCP as a "USB port" for AI — plug in any tool with the same interface.'
      },
      {
        title: 'Why MCP Matters',
        comparison: {
          without: ['Custom integration per tool', 'Tight coupling', 'Hard to swap tools', 'Vendor lock-in'],
          with: ['Standard interface for all', 'Loose coupling', 'Easy add/remove', 'Interoperability']
        }
      }
    ],
    quiz: [
      { q: 'What does MCP stand for?', options: ['Model Context Protocol', 'Machine Control Protocol', 'Multi-Channel Processor'], answer: 0 },
      { q: 'MCP provides a _____ interface for tools', options: ['Custom', 'Standard', 'Complex'], answer: 1 }
    ]
  },
  {
    id: 'concepts',
    title: '2. Core Concepts',
    sections: [
      {
        title: 'Key Terms',
        terms: [
          { term: 'MCP Server', def: 'Service that EXPOSES tools (provides capabilities)' },
          { term: 'MCP Client', def: 'Service that CALLS tools (consumes capabilities)' },
          { term: 'Tool', def: 'A single function the AI can invoke' },
          { term: 'Transport', def: 'How messages travel (HTTP, SSE, stdio)' },
          { term: 'JSON-RPC', def: 'Message format used by MCP' }
        ]
      },
      {
        title: 'Transport Options',
        transports: [
          { name: 'SSE', desc: 'Server-Sent Events over HTTP (web-friendly)' },
          { name: 'Streamable HTTP', desc: 'Newer transport, bidirectional streaming' },
          { name: 'stdio', desc: 'Standard input/output (local processes)' }
        ]
      }
    ],
    quiz: [
      { q: 'Which component EXPOSES tools?', options: ['MCP Client', 'MCP Server', 'Transport'], answer: 1 },
      { q: 'What message format does MCP use?', options: ['XML', 'JSON-RPC', 'SOAP'], answer: 1 }
    ]
  },
  {
    id: 'tools',
    title: '3. Project Tools',
    sections: [
      {
        title: 'Transaction Server Tools',
        tools: [
          { name: 'search_transactions', purpose: 'Find transactions matching criteria', returns: 'List of transactions' },
          { name: 'get_transaction', purpose: 'Get details for one transaction', returns: 'Single transaction object' },
          { name: 'flag_for_review', purpose: 'Mark transactions for human review', returns: 'Count of updated transactions' }
        ]
      }
    ],
    quiz: [
      { q: 'How many tools does the Transaction Server have?', options: ['2', '3', '5'], answer: 1 },
      { q: 'Which tool marks transactions for review?', options: ['search_transactions', 'get_transaction', 'flag_for_review'], answer: 2 }
    ]
  },
  {
    id: 'messages',
    title: '4. MCP Message Flow',
    sections: [
      {
        title: 'Tool Discovery',
        flow: ['Client sends tools/list', 'Server returns tool definitions', 'Client knows available tools']
      },
      {
        title: 'Tool Execution',
        flow: ['Client sends tools/call with arguments', 'Server executes tool', 'Server returns result']
      }
    ],
    quiz: [
      { q: 'Tool discovery uses which method?', options: ['tools/call', 'tools/list', 'tools/get'], answer: 1 },
      { q: 'Tool execution uses which method?', options: ['tools/call', 'tools/list', 'tools/run'], answer: 0 }
    ]
  },
  {
    id: 'structure',
    title: '5. Server Structure',
    sections: [
      {
        title: 'File Organization',
        files: [
          { name: 'server.py', role: 'MCP setup, tool registration' },
          { name: 'tools.py', role: 'Tool implementations' },
          { name: 'db.py', role: 'Database queries' },
          { name: 'schemas.py', role: 'Data models (Pydantic)' }
        ]
      }
    ],
    quiz: [
      { q: 'Where are tools registered?', options: ['tools.py', 'server.py', 'db.py'], answer: 1 },
      { q: 'Which file handles database queries?', options: ['server.py', 'schemas.py', 'db.py'], answer: 2 }
    ]
  },
  {
    id: 'ui',
    title: '6. UI Integration',
    sections: [
      {
        title: 'Phase Colors',
        phases: [
          { phase: 'REQUEST', color: '#3b82f6', emoji: '🔵', meaning: "User's original message" },
          { phase: 'REASONING', color: '#eab308', emoji: '🟡', meaning: 'AI thinking' },
          { phase: 'MCP_REQUEST', color: '#22c55e', emoji: '🟢', meaning: 'Tool being called' },
          { phase: 'MCP_RESPONSE', color: '#22c55e', emoji: '🟢', meaning: 'Tool returned result' },
          { phase: 'COMPLETE', color: '#6b7280', emoji: '⚪', meaning: 'Final response' }
        ]
      }
    ],
    quiz: [
      { q: 'What color represents REASONING?', options: ['Blue', 'Yellow', 'Green'], answer: 1 },
      { q: 'MCP_REQUEST phase color is?', options: ['Red', 'Green', 'Gray'], answer: 1 }
    ]
  }
];

const toolParams = {
  search_transactions: [
    { name: 'merchant_name', type: 'string', required: false, desc: 'Partial match' },
    { name: 'min_amount', type: 'number', required: false, desc: 'Minimum amount' },
    { name: 'max_amount', type: 'number', required: false, desc: 'Maximum amount' },
    { name: 'risk_level', type: 'string', required: false, desc: 'low/medium/high' },
    { name: 'status', type: 'string', required: false, desc: 'pending/approved/declined/flagged' },
    { name: 'limit', type: 'number', required: false, desc: 'Max results (default: 10)' }
  ],
  get_transaction: [
    { name: 'transaction_id', type: 'string', required: true, desc: 'Transaction ID' }
  ],
  flag_for_review: [
    { name: 'transaction_ids', type: 'array', required: true, desc: 'Array of IDs' },
    { name: 'reason', type: 'string', required: true, desc: 'Why flagging' }
  ]
};

const mockResponses = {
  search_transactions: { transactions: [{ transaction_id: 'TXN-001', amount: 15000.00, merchant_name: 'Luxury Watches Inc', risk_level: 'high', status: 'pending' }, { transaction_id: 'TXN-002', amount: 8500.00, merchant_name: 'Tech Store', risk_level: 'medium', status: 'approved' }] },
  get_transaction: { transaction_id: 'TXN-001', amount: 15000.00, currency: 'USD', merchant_name: 'Luxury Watches Inc', merchant_category: 'jewelry', card_last_four: '4242', status: 'pending', risk_level: 'high', country_code: 'US', created_at: '2024-01-15T10:30:00Z' },
  flag_for_review: { updated_count: 2, transaction_ids: ['TXN-001', 'TXN-002'] }
};

export default function MCPLearningApp() {
  const [currentLesson, setCurrentLesson] = useState(0);
  const [expandedSections, setExpandedSections] = useState({});
  const [quizAnswers, setQuizAnswers] = useState({});
  const [showQuizResults, setShowQuizResults] = useState({});
  const [completedLessons, setCompletedLessons] = useState([]);
  const [activeTab, setActiveTab] = useState('learn');
  const [selectedTool, setSelectedTool] = useState('search_transactions');
  const [toolInput, setToolInput] = useState({});
  const [simulatorState, setSimulatorState] = useState('idle');
  const [simulatorMessages, setSimulatorMessages] = useState([]);
  const [progress, setProgress] = useState({});

  useEffect(() => {
    const saved = { completedLessons: [], progress: {} };
    setCompletedLessons(saved.completedLessons);
    setProgress(saved.progress);
  }, []);

  const toggleSection = (lessonId, sectionIdx) => {
    const key = `${lessonId}-${sectionIdx}`;
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleQuizAnswer = (lessonId, qIdx, answerIdx) => {
    const key = `${lessonId}-${qIdx}`;
    setQuizAnswers(prev => ({ ...prev, [key]: answerIdx }));
  };

  const checkQuiz = (lessonId) => {
    setShowQuizResults(prev => ({ ...prev, [lessonId]: true }));
    const lesson = lessons.find(l => l.id === lessonId);
    const allCorrect = lesson.quiz.every((q, i) => quizAnswers[`${lessonId}-${i}`] === q.answer);
    if (allCorrect && !completedLessons.includes(lessonId)) {
      setCompletedLessons(prev => [...prev, lessonId]);
    }
  };

  const runSimulator = async () => {
    setSimulatorState('running');
    setSimulatorMessages([]);
    
    const msgs = [];
    
    // Step 1: Request
    msgs.push({ phase: 'REQUEST', color: '#3b82f6', content: `Tool: ${selectedTool}`, args: JSON.stringify(toolInput, null, 2) });
    setSimulatorMessages([...msgs]);
    await new Promise(r => setTimeout(r, 800));
    
    // Step 2: JSON-RPC Request
    const jsonRpcReq = { jsonrpc: '2.0', method: 'tools/call', params: { name: selectedTool, arguments: toolInput }, id: 1 };
    msgs.push({ phase: 'MCP_REQUEST', color: '#22c55e', content: 'JSON-RPC Request', json: JSON.stringify(jsonRpcReq, null, 2) });
    setSimulatorMessages([...msgs]);
    await new Promise(r => setTimeout(r, 1000));
    
    // Step 3: JSON-RPC Response
    const jsonRpcResp = { jsonrpc: '2.0', id: 1, result: { content: [{ type: 'text', text: JSON.stringify(mockResponses[selectedTool]) }] } };
    msgs.push({ phase: 'MCP_RESPONSE', color: '#22c55e', content: 'JSON-RPC Response', json: JSON.stringify(jsonRpcResp, null, 2) });
    setSimulatorMessages([...msgs]);
    await new Promise(r => setTimeout(r, 800));
    
    // Step 4: Complete
    msgs.push({ phase: 'COMPLETE', color: '#6b7280', content: 'Tool execution complete', result: JSON.stringify(mockResponses[selectedTool], null, 2) });
    setSimulatorMessages([...msgs]);
    
    setSimulatorState('complete');
  };

  const renderLesson = (lesson) => (
    <div className="space-y-4">
      {lesson.sections.map((section, idx) => {
        const key = `${lesson.id}-${idx}`;
        const isExpanded = expandedSections[key] !== false;
        
        return (
          <div key={idx} className="border border-gray-700 rounded-lg overflow-hidden">
            <button onClick={() => toggleSection(lesson.id, idx)} className="w-full flex items-center justify-between p-3 bg-gray-800 hover:bg-gray-750 text-left">
              <span className="font-medium text-white">{section.title}</span>
              {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </button>
            
            {isExpanded && (
              <div className="p-4 bg-gray-900 space-y-3">
                {section.content && <pre className="text-sm text-gray-300 whitespace-pre-wrap">{section.content}</pre>}
                
                {section.keyPoints && (
                  <div className="space-y-1">
                    <div className="text-xs text-gray-500 uppercase">Key Points:</div>
                    {section.keyPoints.map((p, i) => <div key={i} className="flex items-center gap-2 text-sm"><CheckCircle size={14} className="text-green-500" />{p}</div>)}
                  </div>
                )}
                
                {section.analogy && (
                  <div className="p-3 bg-blue-900/30 border border-blue-700 rounded text-sm">
                    <span className="text-blue-400 font-medium">💡 Analogy:</span> {section.analogy}
                  </div>
                )}
                
                {section.comparison && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-red-900/20 border border-red-800 rounded">
                      <div className="text-red-400 font-medium text-sm mb-2">WITHOUT MCP</div>
                      {section.comparison.without.map((item, i) => <div key={i} className="text-sm text-gray-400">• {item}</div>)}
                    </div>
                    <div className="p-3 bg-green-900/20 border border-green-800 rounded">
                      <div className="text-green-400 font-medium text-sm mb-2">WITH MCP</div>
                      {section.comparison.with.map((item, i) => <div key={i} className="text-sm text-gray-400">• {item}</div>)}
                    </div>
                  </div>
                )}
                
                {section.terms && (
                  <table className="w-full text-sm">
                    <thead><tr className="border-b border-gray-700"><th className="text-left p-2 text-gray-400">Term</th><th className="text-left p-2 text-gray-400">Definition</th></tr></thead>
                    <tbody>{section.terms.map((t, i) => <tr key={i} className="border-b border-gray-800"><td className="p-2 text-cyan-400 font-mono">{t.term}</td><td className="p-2 text-gray-300">{t.def}</td></tr>)}</tbody>
                  </table>
                )}
                
                {section.transports && (
                  <div className="space-y-2">
                    {section.transports.map((t, i) => (
                      <div key={i} className="flex items-start gap-3 p-2 bg-gray-800 rounded">
                        <span className="px-2 py-1 bg-purple-900 text-purple-300 text-xs rounded font-mono">{t.name}</span>
                        <span className="text-sm text-gray-400">{t.desc}</span>
                      </div>
                    ))}
                  </div>
                )}
                
                {section.tools && (
                  <div className="space-y-2">
                    {section.tools.map((t, i) => (
                      <div key={i} className="p-3 bg-gray-800 rounded border-l-4 border-green-500">
                        <div className="font-mono text-green-400">{t.name}</div>
                        <div className="text-sm text-gray-400 mt-1">Purpose: {t.purpose}</div>
                        <div className="text-sm text-gray-500">Returns: {t.returns}</div>
                      </div>
                    ))}
                  </div>
                )}
                
                {section.flow && (
                  <div className="flex flex-wrap items-center gap-2">
                    {section.flow.map((step, i) => (
                      <React.Fragment key={i}>
                        <div className="px-3 py-2 bg-gray-800 rounded text-sm">{step}</div>
                        {i < section.flow.length - 1 && <ArrowRight size={16} className="text-gray-600" />}
                      </React.Fragment>
                    ))}
                  </div>
                )}
                
                {section.files && (
                  <div className="space-y-2">
                    {section.files.map((f, i) => (
                      <div key={i} className="flex items-center gap-3 p-2 bg-gray-800 rounded">
                        <Code size={16} className="text-yellow-500" />
                        <span className="font-mono text-yellow-400">{f.name}</span>
                        <span className="text-gray-500">→</span>
                        <span className="text-sm text-gray-400">{f.role}</span>
                      </div>
                    ))}
                  </div>
                )}
                
                {section.phases && (
                  <div className="space-y-2">
                    {section.phases.map((p, i) => (
                      <div key={i} className="flex items-center gap-3 p-2 bg-gray-800 rounded">
                        <span className="text-xl">{p.emoji}</span>
                        <span className="font-mono text-sm" style={{ color: p.color }}>{p.phase}</span>
                        <span className="text-gray-500">→</span>
                        <span className="text-sm text-gray-400">{p.meaning}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
      
      {/* Quiz Section */}
      <div className="mt-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Award size={20} className="text-yellow-500" />
          <span className="font-medium">Knowledge Check</span>
        </div>
        
        {lesson.quiz.map((q, qIdx) => {
          const key = `${lesson.id}-${qIdx}`;
          const answered = quizAnswers[key] !== undefined;
          const isCorrect = quizAnswers[key] === q.answer;
          const showResult = showQuizResults[lesson.id];
          
          return (
            <div key={qIdx} className="mb-4">
              <div className="text-sm mb-2">{q.q}</div>
              <div className="space-y-1">
                {q.options.map((opt, oIdx) => (
                  <button
                    key={oIdx}
                    onClick={() => handleQuizAnswer(lesson.id, qIdx, oIdx)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                      quizAnswers[key] === oIdx
                        ? showResult
                          ? oIdx === q.answer ? 'bg-green-900 border-green-500' : 'bg-red-900 border-red-500'
                          : 'bg-blue-900 border-blue-500'
                        : 'bg-gray-700 hover:bg-gray-600'
                    } border border-transparent`}
                  >
                    {opt}
                    {showResult && oIdx === q.answer && <CheckCircle size={14} className="inline ml-2 text-green-400" />}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
        
        <button
          onClick={() => checkQuiz(lesson.id)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors"
        >
          Check Answers
        </button>
        
        {showQuizResults[lesson.id] && completedLessons.includes(lesson.id) && (
          <div className="mt-3 p-2 bg-green-900/30 border border-green-700 rounded text-sm text-green-400 flex items-center gap-2">
            <CheckCircle size={16} /> All correct! Lesson completed.
          </div>
        )}
      </div>
    </div>
  );

  const renderSimulator = () => (
    <div className="space-y-4">
      <div className="p-4 bg-gray-800 rounded-lg">
        <div className="flex items-center gap-2 mb-4">
          <Zap size={20} className="text-yellow-500" />
          <span className="font-medium">Tool Call Simulator</span>
        </div>
        
        {/* Tool Selection */}
        <div className="mb-4">
          <label className="text-sm text-gray-400 block mb-2">Select Tool:</label>
          <select
            value={selectedTool}
            onChange={(e) => { setSelectedTool(e.target.value); setToolInput({}); }}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
          >
            {Object.keys(toolParams).map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        
        {/* Parameters */}
        <div className="mb-4 space-y-3">
          <label className="text-sm text-gray-400 block">Parameters:</label>
          {toolParams[selectedTool].map((p, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className={`text-xs px-1 rounded ${p.required ? 'bg-red-900 text-red-300' : 'bg-gray-700 text-gray-400'}`}>
                {p.required ? 'REQ' : 'OPT'}
              </span>
              <span className="font-mono text-cyan-400 text-sm w-32">{p.name}</span>
              <input
                type={p.type === 'number' ? 'number' : 'text'}
                placeholder={p.desc}
                value={toolInput[p.name] || ''}
                onChange={(e) => setToolInput(prev => ({ ...prev, [p.name]: p.type === 'number' ? Number(e.target.value) : e.target.value }))}
                className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm"
              />
            </div>
          ))}
        </div>
        
        <button
          onClick={runSimulator}
          disabled={simulatorState === 'running'}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded text-sm font-medium transition-colors"
        >
          {simulatorState === 'running' ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
          {simulatorState === 'running' ? 'Running...' : 'Run Tool Call'}
        </button>
      </div>
      
      {/* Message Flow */}
      {simulatorMessages.length > 0 && (
        <div className="p-4 bg-gray-800 rounded-lg">
          <div className="text-sm text-gray-400 mb-3">MCP Message Flow:</div>
          <div className="space-y-3">
            {simulatorMessages.map((msg, i) => (
              <div key={i} className="border-l-4 pl-3 py-2" style={{ borderColor: msg.color }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: msg.color + '33', color: msg.color }}>
                    {msg.phase}
                  </span>
                  <span className="text-sm text-gray-300">{msg.content}</span>
                </div>
                {msg.json && (
                  <pre className="text-xs bg-gray-900 p-2 rounded overflow-x-auto text-gray-400">{msg.json}</pre>
                )}
                {msg.args && (
                  <pre className="text-xs bg-gray-900 p-2 rounded overflow-x-auto text-gray-400">Arguments: {msg.args}</pre>
                )}
                {msg.result && (
                  <pre className="text-xs bg-gray-900 p-2 rounded overflow-x-auto text-green-400">{msg.result}</pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const progressPercent = Math.round((completedLessons.length / lessons.length) * 100);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <Book className="text-blue-500" />
            MCP Learning Application
          </h1>
          <div className="mt-2 flex items-center gap-4">
            <div className="flex-1 bg-gray-800 rounded-full h-2">
              <div className="bg-green-500 h-2 rounded-full transition-all" style={{ width: `${progressPercent}%` }} />
            </div>
            <span className="text-sm text-gray-400">{progressPercent}% Complete</span>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('learn')}
            className={`px-4 py-2 rounded-t text-sm font-medium transition-colors ${activeTab === 'learn' ? 'bg-gray-800 text-white' : 'bg-gray-900 text-gray-400 hover:text-white'}`}
          >
            <Book size={16} className="inline mr-2" />Lessons
          </button>
          <button
            onClick={() => setActiveTab('simulate')}
            className={`px-4 py-2 rounded-t text-sm font-medium transition-colors ${activeTab === 'simulate' ? 'bg-gray-800 text-white' : 'bg-gray-900 text-gray-400 hover:text-white'}`}
          >
            <Play size={16} className="inline mr-2" />Simulator
          </button>
        </div>
        
        {/* Content */}
        <div className="bg-gray-800 rounded-lg p-4">
          {activeTab === 'learn' && (
            <div className="flex gap-4">
              {/* Lesson List */}
              <div className="w-48 shrink-0 space-y-1">
                {lessons.map((lesson, idx) => (
                  <button
                    key={lesson.id}
                    onClick={() => setCurrentLesson(idx)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition-colors flex items-center gap-2 ${
                      currentLesson === idx ? 'bg-blue-900 text-white' : 'hover:bg-gray-700 text-gray-300'
                    }`}
                  >
                    {completedLessons.includes(lesson.id) ? (
                      <CheckCircle size={14} className="text-green-500 shrink-0" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-gray-600 shrink-0" />
                    )}
                    <span className="truncate">{lesson.title}</span>
                  </button>
                ))}
              </div>
              
              {/* Lesson Content */}
              <div className="flex-1">
                <h2 className="text-lg font-semibold mb-4">{lessons[currentLesson].title}</h2>
                {renderLesson(lessons[currentLesson])}
              </div>
            </div>
          )}
          
          {activeTab === 'simulate' && renderSimulator()}
        </div>
        
        {/* Footer */}
        <div className="mt-4 text-center text-xs text-gray-600">
          Based on Transaction Search Agent MCP Learning Guide
        </div>
      </div>
    </div>
  );
}
