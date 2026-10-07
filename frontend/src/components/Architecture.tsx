export function Architecture() {
  return (
    <div className="arch">
      <p>
        One goal in, four pieces of approved copy out. Agents are LangGraph nodes; the only way
        they can touch the bank's data is through an MCP server; nothing ships without a human
        click; every step is written to a hash-chained audit log.
      </p>
      <svg viewBox="0 0 980 440" className="arch-svg" role="img" aria-label="Architecture diagram">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="currentColor" />
          </marker>
        </defs>

        {/* UI */}
        <g className="box ui">
          <rect x="20" y="40" width="150" height="70" rx="10" />
          <text x="95" y="68" textAnchor="middle">React + Vite</text>
          <text x="95" y="90" textAnchor="middle" className="sub">goal · timeline · approve</text>
        </g>
        <line x1="170" y1="75" x2="230" y2="75" markerEnd="url(#arrow)" />
        <text x="200" y="65" textAnchor="middle" className="edge">SSE / JSON</text>

        {/* API */}
        <g className="box api">
          <rect x="230" y="40" width="150" height="70" rx="10" />
          <text x="305" y="68" textAnchor="middle">FastAPI</text>
          <text x="305" y="90" textAnchor="middle" className="sub">/api/runs · /decision</text>
        </g>
        <line x1="305" y1="110" x2="305" y2="150" markerEnd="url(#arrow)" />

        {/* Graph */}
        <g className="box graph">
          <rect x="40" y="150" width="620" height="170" rx="12" />
          <text x="60" y="175" className="title">LangGraph StateGraph · MemorySaver · recursion_limit 25</text>
          {["planner", "audience", "copy", "compliance", "evaluator", "publish"].map((n, i) => (
            <g key={n} className={`node ${n}`}>
              <rect x={60 + i * 100} y={200} width="86" height="44" rx="8" />
              <text x={103 + i * 100} y={227} textAnchor="middle">{n}</text>
              {i < 5 && <line x1={146 + i * 100} y1={222} x2={160 + i * 100} y2={222} markerEnd="url(#arrow)" />}
            </g>
          ))}
          <path d="M 503 244 C 503 290, 303 290, 303 244" fill="none" markerEnd="url(#arrow)" className="loop" />
          <text x="403" y="285" textAnchor="middle" className="edge">revise (max 2)</text>
          <line x1="560" y1="200" x2="560" y2="178" className="gate" />
          <text x="560" y="172" textAnchor="middle" className="edge gate">interrupt_before · human approval</text>
        </g>

        {/* MCP */}
        <g className="box mcp">
          <rect x="720" y="150" width="220" height="80" rx="10" />
          <text x="830" y="178" textAnchor="middle">MCP server (stdio)</text>
          <text x="830" y="198" textAnchor="middle" className="sub">resolve_branches · query_segments</text>
          <text x="830" y="216" textAnchor="middle" className="sub">branch_performance · past_campaign_results</text>
        </g>
        <line x1="660" y1="222" x2="720" y2="195" markerEnd="url(#arrow)" />
        <line x1="830" y1="230" x2="830" y2="260" markerEnd="url(#arrow)" />
        <g className="box data">
          <rect x="745" y="260" width="170" height="50" rx="10" />
          <text x="830" y="282" textAnchor="middle">SQLite (read-only)</text>
          <text x="830" y="300" textAnchor="middle" className="sub">5,000 customers · 12 branches</text>
        </g>

        {/* Side services */}
        <g className="box llm">
          <rect x="40" y="350" width="190" height="60" rx="10" />
          <text x="135" y="374" textAnchor="middle">Claude (structured outputs)</text>
          <text x="135" y="394" textAnchor="middle" className="sub">or MOCK_LLM=1 deterministic</text>
        </g>
        <g className="box rag">
          <rect x="260" y="350" width="190" height="60" rx="10" />
          <text x="355" y="374" textAnchor="middle">Policy RAG (BM25)</text>
          <text x="355" y="394" textAnchor="middle" className="sub">policies/*.txt → citations</text>
        </g>
        <g className="box audit">
          <rect x="480" y="350" width="190" height="60" rx="10" />
          <text x="575" y="374" textAnchor="middle">Audit log (JSONL)</text>
          <text x="575" y="394" textAnchor="middle" className="sub">SHA-256 hash chain</text>
        </g>
        <line x1="135" y1="350" x2="135" y2="320" markerEnd="url(#arrow)" />
        <line x1="355" y1="350" x2="355" y2="320" markerEnd="url(#arrow)" />
        <line x1="575" y1="320" x2="575" y2="350" markerEnd="url(#arrow)" />
      </svg>

      <div className="arch-notes">
        <div>
          <h4>Why LangGraph</h4>
          <p>Explicit state, explicit edges, a checkpointer, and a built-in way to pause before a node. The revision loop and the approval gate are two lines of graph definition, not custom control flow.</p>
        </div>
        <div>
          <h4>Why MCP for data</h4>
          <p>The agents never see SQL. Four typed tools are the whole surface, so the same server works from Claude Desktop, the MCP Inspector, or this workflow, and every call is logged.</p>
        </div>
        <div>
          <h4>Why rules + RAG, not model-only compliance</h4>
          <p>Whether copy says "guaranteed" is not a judgement call. Deterministic rules decide; retrieval cites the paragraph; the model only proposes rewrites.</p>
        </div>
        <div>
          <h4>Why a hash chain</h4>
          <p>Marketing at a bank is regulated. Each audit line hashes the previous one, so editing or deleting history breaks verification. The Audit tab lets you check it.</p>
        </div>
      </div>
    </div>
  );
}
