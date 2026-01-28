from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
import datetime
from openai import AsyncOpenAI
# Import database to log stats
from common.database import SessionLocal
# We need a model to log AI stats. Let's reuse models.PluginActivity or create new?
# Ideally we add a simple function in database.py to log this.
# For now, we'll inline a simple logger or import if I add it to database.py
# Let's import the session and do it here or add helper. 
# Better pattern: Add helper in database.py. But to succeed quickly, I will add helper import here assuming I will create it next step.
# Actually I will implement the logic inside the endpoint to be self-contained for this task to avoid circular imports if database.py imports ai.

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Assistant"]
)

# Initialize OpenAI Client (Conditional)
api_key = os.getenv("OPENAI_API_KEY")
aclient = None
if api_key:
    try:
        aclient = AsyncOpenAI(api_key=api_key)
    except Exception as e:
        print(f"Failed to initialize OpenAI client: {e}")
else:
    print("WARNING: OPENAI_API_KEY not found. AI features will stay in fallback mode.")

class ChatAttachment(BaseModel):
    name: str
    content: str # Base64
    type: str # "image", "text", "excel"

class ChatPayload(BaseModel):
    message: str
    context: Optional[str] = ""
    user_email: Optional[str] = ""
    attachments: Optional[List[ChatAttachment]] = []

class ChatResponse(BaseModel):
    text: str
    action: Optional[str] = ""

SYSTEM_PROMPT = """
You are the AI Brain of the "AO Development" Revit Plugin. 
Your goal is to assist architects and engineers by analyzing their natural language requests and deciding if a specific Plugin Command (Action) should be executed.

AVAILABLE ACTIONS:
- AUDIT_WALLS: Checks for overlapping or duplicate walls.
- AUTO_DIMENSION: Automatically dimensions visible grids in the current view.
- GENERATE_SHOP_DRAWINGS: Groups selected elements by geometry and prepares assembly/shop drawings.
- GENERATE_MEP: Converts selected model lines into MEP Pipes/Ducts based on smart detection.
- GENERATE_MEP: Converts selected model lines into MEP Pipes/Ducts based on smart detection.
- COUNT_ELEMENTS: Counts selected elements or visible elements.
- CREATE_SHEET_LIST: Creates a Schedule View (Tabla de Planificación) listing all Sheets in the project.

INSTRUCTIONS:
1. Analyze the USER MESSAGE to understand intent.
2. If the user provided ATTACHMENTS (Images, Excel, Code), analyze their content provided in the context.
3. If the user wants to perform one of the actions above, set "action" to the corresponding key.
4. If the user just wants to chat or ask questions, set "action" to empty string "".
5. Generate a helpful, professional, and concise "text" response in Spanish (Español).

OUTPUT FORMAT:
Return ONLY a raw JSON object (no markdown formatting) with keys: "text" and "action".
Example: { "text": "Entendido, voy a auditar los muros.", "action": "AUDIT_WALLS" }
"""

# Simple In-Memory Stats (migrating to DB recommended for production)
# For the urgency, we will append to a JSON file or use a global list?
# User wants "Monitor". A simple JSON file is robust enough for a quick feature.
STATS_FILE = "ai_stats_log.json"

def log_ai_usage(user_email, action, message):
    try:
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user": user_email,
            "action": action if action else "Chat/Q&A",
            "message_length": len(message)
        }
        
        # Simple file append
        mode = "r+" if os.path.exists(STATS_FILE) else "w"
        try:
            with open(STATS_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []
            
        data.append(entry)
        
        with open(STATS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Stats Log Error: {e}")

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatPayload):
    msg = payload.message
    
    # Prepare Context with Attachments
    full_context = f"Context: {payload.context}\n"
    if payload.attachments:
        full_context += "ATTACHMENTS PROVIDED:\n"
        for att in payload.attachments:
             # Truncate content if too long for tokens? GPT-4o has 128k context, usually fine.
             # But let's be careful. if Image, we can't just pass base64 text to "content" unless we use Vision API format.
             # For this iteration, we assume text-based analysis or acknowledge image presence.
             # To support Image Analysis properly we need to change messages format to include image_url with base64.
             # Let's support Text/Excel (CSV) content directly.
             if att.type in ["image", "png", "jpg"]:
                 full_context += f"[Image Attachment: {att.name} - Vision Analysis skipped in this v1.3 iteration, treated as context presence]\n"
             else:
                 # Text/Code
                 # Limit characters
                 content_snippet = att.content[:10000] 
                 full_context += f"[File: {att.name}]\nContent:\n{content_snippet}\n...\n"

    try:
        if not aclient:
            return fallback_logic(msg)

        response = await aclient.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"User: {msg}\n{full_context}"}
            ],
            temperature=0.3,
            max_tokens=300,
            response_format={ "type": "json_object" } 
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        
        resp_text = data.get("text", "Procesado.")
        resp_action = data.get("action", "")
        
        # LOG STATS
        BackgroundTasks().add_task(log_ai_usage, payload.user_email, resp_action, msg)
        # Actually BackgroundTasks needs to be passed in verify function signature? 
        # Fast fix: just call it sync or use simple non-await
        log_ai_usage(payload.user_email, resp_action, msg)
        
        return ChatResponse(
            text=resp_text,
            action=resp_action
        )

    except Exception as e:
        print(f"OpenAI Error: {e}")
        return fallback_logic(msg)

@router.get("/stats")
async def get_ai_stats():
    """Returns AI usage statistics for the Monitor Window"""
    try:
        if not os.path.exists(STATS_FILE):
             return {"total_requests": 0, "top_users": [], "recent_activity": []}
             
        with open(STATS_FILE, "r") as f:
            data = json.load(f)
            
        total = len(data)
        # Aggregate Top Users
        users = {}
        for d in data:
            u = d.get("user", "Unknown")
            users[u] = users.get(u, 0) + 1
            
        sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)
        top_users = [{"email": k, "count": v} for k, v in sorted_users[:5]]
        
        # Recent 10
        recent = data[-10:]
        recent.reverse()
        
        return {
            "total_requests": total,
            "top_users": top_users,
            "recent_activity": recent
        }
    except Exception as e:
        return {"error": str(e)}

def fallback_logic(msg: str) -> ChatResponse:
    msg = msg.lower()
    text = "Lo siento, mi cerebro IA no está disponible en este momento. Usando lógica básica."
    action = ""

    if "audit" in msg or "auditar" in msg:
        text = "Modo Fallback: Auditar Muros."
        action = "AUDIT_WALLS"
    elif "acotar" in msg:
        text = "Modo Fallback: Acotar Ejes."
        action = "AUTO_DIMENSION"
    
    return ChatResponse(text=text, action=action)
