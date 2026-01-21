from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Assistant"]
)

class ChatPayload(BaseModel):
    message: str
    context: Optional[str] = ""
    user_email: Optional[str] = ""

class ChatResponse(BaseModel):
    text: str
    action: Optional[str] = ""

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatPayload):
    """
    Receives natural language from Revit Plugin, 
    processes intent (Rule-based or LLM),
    returns text response and optional Action Key.
    """
    msg = payload.message.lower()
    
    # --- INTENT RECOGNITION LOGIC ---
    # This is where we can plug in OpenAI/Gemini API later.
    # For now, we migrate the logic from C# to here.
    
    response_text = ""
    action_key = ""

    if "audit" in msg or "auditar" in msg or "duplicado" in msg:
        response_text = "Entendido. He detectado que deseas auditar el modelo en busca de duplicados. Iniciando proceso de auditoría..."
        action_key = "AUDIT_WALLS"
        
    elif "acotar" in msg or "dimensionar" in msg or "cotas" in msg:
        response_text = "Entendido. Procederé a generar las cotas automáticas para los ejes visibles en tu vista actual."
        action_key = "AUTO_DIMENSION"
        
    elif "despiece" in msg or "agrupar" in msg or "assembly" in msg:
        response_text = "Analizaré la geometría seleccionada para identificar elementos idénticos y generar sus montajes (assemblies)."
        action_key = "GENERATE_SHOP_DRAWINGS"
        
    elif "tubería" in msg or "ducto" in msg or "mep" in msg or "sanitaria" in msg:
        response_text = "Correcto. Convertiré las líneas de modelo seleccionadas en elementos MEP inteligentes."
        action_key = "GENERATE_MEP"
        
    else:
        # Fallback / General Chat
        response_text = "Entendido. Actualmente puedo ayudarte con tareas como: 'Auditar Muros', 'Acotar Ejes', 'Generar Despieces' o 'Crear Tuberías desde Líneas'. ¿Qué te gustaría intentar?"
        action_key = ""

    # Simulate thinking time? frontend handles await, so we can be fast.
    
    return ChatResponse(
        text=response_text,
        action=action_key
    )
