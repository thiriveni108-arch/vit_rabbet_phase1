import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import DATA_DIR
from backend.study_graph import StudyGraph
from backend.atlas_agent import Atlas
from backend.schemas import Question, Answer

app = FastAPI(
    title="ATLAS Clinical Trial AI Agent API",
    description="Backend AI Agent API for ATLAS Clinical Trial QA and Factual Evidence Retrieval",
    version="1.0.0"
)

# Enable CORS for frontend teammates
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global graph and agent instances
global_graph: Optional[StudyGraph] = None
global_agent: Optional[Atlas] = None

@app.on_event("startup")
def startup_event():
    global global_graph, global_agent
    print(f"[INIT] Initializing StudyGraph from data dir: {DATA_DIR}")
    global_graph = StudyGraph(DATA_DIR)
    stats = global_graph.build()
    print(f"[INIT] Graph built: {stats['nodes']} nodes, {stats['edges']} edges, {stats['subjects']} subjects in {stats['ms']}ms.")
    global_agent = Atlas(global_graph)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=dict)
def ask_question(question: Question):
    global global_agent
    if not global_agent:
        raise HTTPException(status_code=500, detail="Atlas Agent not initialized.")
    
    try:
        ans: Answer = global_agent.answer(question)
        return ans.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reload")
def reload_data(payload: Optional[Dict[str, Any]] = None):
    global global_graph, global_agent
    cut = None
    if payload and "cut" in payload:
        try:
            cut = int(payload["cut"])
        except ValueError:
            pass

    print(f"[RELOAD] Rebuilding graph at cut: {cut}")
    global_graph = StudyGraph(DATA_DIR)
    stats = global_graph.build(cut=cut)
    global_agent = Atlas(global_graph)
    
    return {
        "status": "reloaded",
        "cut": cut,
        "nodes": stats["nodes"],
        "edges": stats["edges"],
        "subjects": stats["subjects"],
        "ms": stats["ms"]
    }
