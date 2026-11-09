import { createFileRoute, useParams } from "@tanstack/react-router";
import { useState, useRef, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Send, Bot, User, Activity, CheckCircle, XCircle, AlertCircle, Clock, ShieldCheck, FileText, CheckCircle2, Link as LinkIcon, Database, AlertTriangle } from "lucide-react";
import { ReactFlow, MiniMap, Controls, Background, MarkerType, Node, Edge, useNodesState, useEdgesState } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { sendAgentMessage, executionStatusQuery, executionEvidenceQuery, ExecutionStatusResult, createReport, getReportStatus } from "@/api/agent";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";

export const Route = createFileRoute("/workspaces/$workspaceId/agent")({
  component: AgentConsole,
});

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  executionId?: string | null;
};

function ExecutionGraph({ executionId }: { executionId: string }) {
  const { data: exec } = useQuery(executionStatusQuery(executionId, true));
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (!exec) return;

    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    // Layout simply: planner -> capability nodes (parallel) -> synthesis
    
    const plannerNode = exec.nodes.find(n => n.node_id === "planner");
    const synthesisNode = exec.nodes.find(n => n.node_id === "synthesis");
    const capNodes = exec.nodes.filter(n => n.node_type === "capability");

    if (plannerNode) {
      newNodes.push({
        id: "planner",
        position: { x: 250, y: 50 },
        data: { label: `Planner (${plannerNode.status})` },
        style: {
          background: plannerNode.status === "completed" ? "#dcfce7" : plannerNode.status === "running" ? "#fef08a" : "#f3f4f6",
          border: "1px solid #16a34a"
        }
      });
    }

    capNodes.forEach((cn, i) => {
      newNodes.push({
        id: cn.node_id,
        position: { x: 100 + i * 200, y: 150 },
        data: { label: `${cn.agent_code}\n${cn.capability_code}\n(${cn.status})` },
        style: {
          background: cn.status === "completed" ? "#dbeafe" : cn.status === "running" ? "#fef08a" : cn.status === "retrying" ? "#fdba74" : cn.status === "failed" ? "#fee2e2" : "#f3f4f6",
          border: "1px solid #2563eb",
          borderRadius: "8px",
          padding: "10px",
          textAlign: "center"
        }
      });
    });

    if (synthesisNode) {
      newNodes.push({
        id: "synthesis",
        position: { x: 250, y: 300 },
        data: { label: `Synthesis (${synthesisNode.status})` },
        style: {
          background: synthesisNode.status === "completed" ? "#f3e8ff" : synthesisNode.status === "running" ? "#fef08a" : "#f3f4f6",
          border: "1px solid #9333ea"
        }
      });
    }

    exec.edges.forEach(e => {
      newEdges.push({
        id: `${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
      });
    });

    // If edges are empty but we have nodes, just draw synthetic edges
    if (exec.edges.length === 0) {
      capNodes.forEach(cn => {
        newEdges.push({ id: `e-planner-${cn.node_id}`, source: "planner", target: cn.node_id, animated: true });
        newEdges.push({ id: `e-${cn.node_id}-synthesis`, source: cn.node_id, target: "synthesis", animated: true });
      });
    }

    setNodes(newNodes);
    setEdges(newEdges);
  }, [exec, setNodes, setEdges]);

  return (
    <div className="w-full h-[400px] border rounded-md bg-slate-50">
      <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function EvidencePanel({ executionId }: { executionId: string }) {
  const { data: evidenceData } = useQuery(executionEvidenceQuery(executionId));

  if (!evidenceData) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 text-sm gap-2">
        <ShieldCheck className="w-8 h-8 opacity-50" />
        <div>Awaiting Evidence & Verification Data...</div>
      </div>
    );
  }

  const claims = evidenceData.claims || [];
  const evidenceList = evidenceData.evidence || [];

  return (
    <div className="flex flex-col gap-4">
      {claims.length === 0 && (
        <div className="text-sm text-slate-500 bg-slate-100 p-3 rounded text-center">
          No structured claims generated for this execution.
        </div>
      )}

      {claims.map((claim) => {
        let StatusIcon = CheckCircle2;
        let statusColor = "text-green-600 bg-green-50 border-green-200";
        if (claim.verification_status === "UNVERIFIABLE") {
          StatusIcon = AlertTriangle;
          statusColor = "text-orange-600 bg-orange-50 border-orange-200";
        } else if (claim.verification_status === "UNSUPPORTED" || claim.verification_status === "CONFLICTING") {
          StatusIcon = XCircle;
          statusColor = "text-red-600 bg-red-50 border-red-200";
        } else if (claim.verification_status === "PARTIALLY_SUPPORTED") {
          StatusIcon = AlertCircle;
          statusColor = "text-yellow-600 bg-yellow-50 border-yellow-200";
        }

        const linkedEvidence = claim.evidence_ids.map(eid => evidenceList.find(e => e.id === eid)).filter(Boolean) as typeof evidenceList;

        return (
          <div key={claim.id} className={`border rounded-lg p-4 ${statusColor}`}>
            <div className="flex items-start gap-3">
              <StatusIcon className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="font-semibold mb-1 text-slate-800">{claim.text}</div>
                <div className="text-xs font-mono mb-2 uppercase tracking-wide opacity-80">
                  {claim.verification_status} — {claim.type}
                </div>
                {claim.reason && (
                  <div className="text-sm text-slate-700 bg-white/50 p-2 rounded mb-3 border border-black/5">
                    {claim.reason}
                  </div>
                )}
                
                {linkedEvidence.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-black/10">
                    <div className="text-xs font-semibold mb-2 flex items-center gap-1 uppercase opacity-75">
                      <Database className="w-3 h-3" /> Supporting Evidence
                    </div>
                    <div className="flex flex-col gap-2">
                      {linkedEvidence.map((ev) => (
                        <div key={ev.id} className="bg-white/80 rounded p-2 text-xs border border-black/5 flex flex-col gap-1 text-slate-700">
                          <div className="font-medium flex items-center gap-1 text-blue-700">
                            <LinkIcon className="w-3 h-3" />
                            {ev.dataset_id} ({ev.source_name})
                          </div>
                          {ev.observation_time && <div>Observed: {new Date(ev.observation_time).toLocaleString()}</div>}
                          {ev.computation && <div>Method: {ev.computation}</div>}
                          {ev.summary && <div>Summary: {ev.summary}</div>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}


function ReportPanel({ executionId }: { executionId: string }) {
  const [packageId, setPackageId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [artifacts, setArtifacts] = useState<{type: string, url: string}[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const generateReport = async () => {
    try {
      setError(null);
      const res = await createReport({ execution_id: executionId, title: `ORCA Execution Report - ${executionId.slice(0,8)}` });
      setPackageId(res.package_id);
      setStatus(res.status);
      setIsPolling(true);
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    if (!isPolling || !packageId) return;
    const interval = setInterval(async () => {
      try {
        const res = await getReportStatus(packageId);
        setStatus(res.status);
        if (res.status === "COMPLETED") {
          setArtifacts(res.artifacts || []);
          setIsPolling(false);
          clearInterval(interval);
        } else if (res.status === "FAILED") {
          setError(res.summary);
          setIsPolling(false);
          clearInterval(interval);
        }
      } catch (err: any) {
        setError(err.message);
        setIsPolling(false);
        clearInterval(interval);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [isPolling, packageId]);

  return (
    <div className="flex flex-col gap-4 p-4 items-center justify-center h-full">
      <FileText className="w-12 h-12 text-slate-300 mb-2" />
      <h3 className="font-semibold text-lg text-slate-700">Research & Decision Support Package</h3>
      <p className="text-sm text-slate-500 text-center max-w-sm mb-4">
        Generate a comprehensive, verifiable report package (PDF, HTML, JSON) documenting this execution, including all scientific provenance and limits.
      </p>

      {!packageId ? (
        <Button onClick={generateReport} className="bg-blue-600 hover:bg-blue-700">
          Generate Report Package
        </Button>
      ) : (
        <div className="flex flex-col items-center gap-4 w-full max-w-md bg-slate-50 p-6 rounded-xl border border-slate-200">
          <div className="flex items-center gap-2">
            {status === "PENDING" || status === "GENERATING" ? (
              <Activity className="w-5 h-5 animate-pulse text-blue-500" />
            ) : status === "COMPLETED" ? (
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-red-500" />
            )}
            <span className="font-semibold text-slate-700">Status: {status}</span>
          </div>

          {error && <div className="text-red-500 text-sm bg-red-50 p-2 rounded">{error}</div>}

          {status === "COMPLETED" && artifacts.length > 0 && (
            <div className="flex flex-wrap gap-2 justify-center mt-2">
              {artifacts.map(a => (
                <a key={a.type} href={`http://localhost:8000${a.url}`} target="_blank" rel="noreferrer" className="flex items-center gap-1 bg-white border border-slate-300 hover:bg-slate-50 px-4 py-2 rounded-lg text-sm font-medium text-slate-700 transition-colors">
                  <FileText className="w-4 h-4" />
                  Download {a.type}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function AgentConsole({ workspaceIdProp }: { workspaceIdProp?: string } = {}) {
  const params = useParams({ strict: false });
  const workspaceId = workspaceIdProp || (params as any)?.workspaceId || "command-center";
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: execStatus } = useQuery(executionStatusQuery(activeExecutionId, !!activeExecutionId));

  const chatMutation = useMutation({
    mutationFn: sendAgentMessage,
    onSuccess: (data) => {
      setActiveConversationId(data.conversation_id);
      setActiveExecutionId(data.execution_id);
      setMessages(prev => [...prev, { id: data.execution_id, role: "assistant", content: data.answer, executionId: data.execution_id }]);
    },
    onError: (err: any) => {
      setMessages(prev => [...prev, { id: Date.now().toString(), role: "assistant", content: `Error: ${err.message}` }]);
    }
  });

  const handleSend = (overrideInput?: string) => {
    const query = overrideInput || input;
    if (!query.trim()) return;
    const mId = Date.now().toString();
    setMessages(prev => [...prev, { id: mId, role: "user", content: query }]);
    chatMutation.mutate({
      conversation_id: activeConversationId,
      workspace_code: workspaceId,
      message: query,
    });
    setInput("");
  };

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
      handleSend(q);
      // clean up URL
      window.history.replaceState({}, '', window.location.pathname);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (execStatus && activeExecutionId && (execStatus.status === 'completed' || execStatus.status === 'failed')) {
      const synthNode = execStatus.nodes?.find((n: any) => n.node_type === 'synthesis' || n.node_id === 'synthesis');
      const finalMsg = synthNode?.output?.answer || synthNode?.output?.final_answer || "Execution finished.";
      
      setMessages(prev => {
        const alreadyHasFinal = prev.some(m => m.id === `final-${activeExecutionId}`);
        if (alreadyHasFinal) return prev;
        return [
          ...prev.filter(m => m.id !== activeExecutionId),
          { id: `final-${activeExecutionId}`, role: "assistant", content: finalMsg, executionId: activeExecutionId }
        ];
      });
    }
  }, [execStatus, activeExecutionId]);


  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, execStatus]);

  const [activeTab, setActiveTab] = useState<"graph" | "details" | "evidence" | "report">("graph");

  return (
    <div className="flex h-full w-full gap-4 p-4">
      <div className="flex flex-col w-1/2 border rounded-xl bg-white shadow-sm overflow-hidden">
        <div className="p-4 border-b bg-slate-50 flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-600" />
          <h2 className="font-semibold">ORCA Agent Console</h2>
          <div className="ml-auto text-xs text-slate-500 bg-slate-200 px-2 py-1 rounded-full">{workspaceId}</div>
        </div>
        
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="flex flex-col gap-4">
            {messages.length === 0 && (
              <div className="text-center text-slate-400 mt-10">
                <Bot className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>Hello. I am the ORCA Planner.</p>
                <p className="text-sm">Ask me about weather, ocean conditions, or coastal exposure.</p>
              </div>
            )}
            
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === "user" ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-600"}`}>
                  {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className={`px-4 py-3 rounded-2xl max-w-[85%] ${msg.role === "user" ? "bg-blue-600 text-white rounded-tr-sm" : "bg-slate-100 text-slate-800 rounded-tl-sm"}`}>
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                </div>
              </div>
            ))}

            {chatMutation.isPending && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center">
                  <Bot size={16} />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-slate-100 text-slate-500 text-sm flex items-center gap-2">
                  <Activity className="w-4 h-4 animate-pulse" /> Thinking and Planning...
                </div>
              </div>
            )}
            
            {/* If there's an active execution still running */}
            {activeExecutionId && execStatus?.status === 'running' && !chatMutation.isPending && (
               <div className="flex gap-3">
                 <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center">
                   <Bot size={16} />
                 </div>
                 <div className="px-4 py-3 rounded-2xl bg-slate-100 text-slate-500 text-sm flex items-center gap-2 border border-blue-200 bg-blue-50">
                   <Activity className="w-4 h-4 animate-pulse text-blue-500" /> Executing Plan...
                 </div>
               </div>
            )}
          </div>
        </ScrollArea>
        
        <div className="p-4 border-t bg-slate-50">
          <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2">
            <input 
              type="text" 
              value={input} 
              onChange={e => setInput(e.target.value)} 
              placeholder="Ask ORCA..."
              className="flex-1 px-4 py-2 border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={chatMutation.isPending || (execStatus && execStatus.status === 'running')}
            />
            <Button type="submit" size="icon" className="rounded-full" disabled={chatMutation.isPending || !input.trim() || (execStatus && execStatus.status === 'running')}>
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </div>

      <div className="flex flex-col w-1/2 gap-4">
        {/* Right Panel Tabs */}
        <div className="flex flex-col border rounded-xl bg-white shadow-sm overflow-hidden h-full">
          <div className="p-3 border-b bg-slate-50 flex items-center gap-2 overflow-x-auto">
            <Button variant={activeTab === "graph" ? "default" : "ghost"} size="sm" onClick={() => setActiveTab("graph")} className="text-xs h-8">
              <Activity className="w-3 h-3 mr-1" /> Graph
            </Button>
            <Button variant={activeTab === "details" ? "default" : "ghost"} size="sm" onClick={() => setActiveTab("details")} className="text-xs h-8">
              <AlertCircle className="w-3 h-3 mr-1" /> Log
            </Button>
            <Button variant={activeTab === "evidence" ? "default" : "ghost"} size="sm" onClick={() => setActiveTab("evidence")} className="text-xs h-8">
              <ShieldCheck className="w-3 h-3 mr-1" /> Evidence
            </Button>
            <Button variant={activeTab === "report" ? "default" : "ghost"} size="sm" onClick={() => setActiveTab("report")} className="text-xs h-8">
              <FileText className="w-3 h-3 mr-1" /> Report
            </Button>

            {execStatus && (
              <span className={`ml-auto text-xs px-2 py-1 rounded-full capitalize shrink-0 ${execStatus.status === 'completed' ? 'bg-green-100 text-green-700' : execStatus.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                {execStatus.status}
              </span>
            )}
          </div>
          
          <div className="flex-1 overflow-hidden">
            {activeTab === "graph" && (
              <div className="w-full h-full p-4">
                {activeExecutionId ? (
                  <ExecutionGraph executionId={activeExecutionId} />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
                    No active execution
                  </div>
                )}
              </div>
            )}

            {activeTab === "details" && (
              <ScrollArea className="h-full p-4">
            {execStatus ? (
              <div className="space-y-4">
                <div className="text-xs text-slate-500 font-mono bg-slate-100 p-2 rounded">
                  Intent: {execStatus.intent || "Unknown"}
                </div>
                {execStatus.nodes.filter(n => n.node_type === "capability").map(n => (
                  <div key={n.id} className="border rounded p-3 text-sm flex flex-col gap-2">
                    <div className="flex items-center gap-2 font-medium">
                      {n.status === "completed" ? <CheckCircle className="w-4 h-4 text-green-500" /> : n.status === "failed" ? <XCircle className="w-4 h-4 text-red-500" /> : <Clock className="w-4 h-4 text-blue-500" />}
                      {n.agent_code} / {n.capability_code}
                    </div>
                    {n.error && (
                      <div className="text-red-600 text-xs mt-1 bg-red-50 p-2 rounded border border-red-100">
                        {n.error}
                      </div>
                    )}
                    {n.output?.status === "SUCCESS" && n.output?.metadata && (
                      <div className="text-xs text-slate-600 space-y-1">
                        <div><span className="font-semibold">Source:</span> {n.output?.data?.source || "Unknown"}</div>
                        <div><span className="font-semibold">Dataset:</span> {n.output?.data?.dataset || "Unknown"}</div>
                        <div><span className="font-semibold">Cached:</span> {n.output?.metadata?.is_cached ? "Yes" : "No"}</div>
                        <div><span className="font-semibold">Latency:</span> {n.duration_ms}ms</div>
                      </div>
                    )}
                    {n.output?.status === "UNAVAILABLE" && (
                      <div className="text-orange-600 text-xs mt-1 bg-orange-50 p-2 rounded">
                        Provider Unavailable. Errors: {n.output.errors?.join(", ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
                Details will appear here during execution
              </div>
            )}
          </ScrollArea>
            )}

            {activeTab === "evidence" && (
              <ScrollArea className="h-full p-4">
                {activeExecutionId ? (
                  <EvidencePanel executionId={activeExecutionId} />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
                    No active execution to show evidence for
                  </div>
                )}
              </ScrollArea>
            )}

            {activeTab === "report" && (
              <div className="h-full">
                {activeExecutionId ? (
                  <ReportPanel executionId={activeExecutionId} />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
                    No active execution to generate report for
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
