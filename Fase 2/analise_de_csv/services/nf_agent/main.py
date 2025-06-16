# main.py
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime
import os
import re

from agent_manager import AgentManager, create_swarm_group
from agent_manager_sel_group import AgentManagerSelGroup, create_selector_group

app = FastAPI(
    title="NF Agent Service",
    description="Serviço de agentes inteligentes para processamento de tarefas",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent manager instance and available implementations
agent_implementations = {
    "default": AgentManager,
    "sel_group": AgentManagerSelGroup
}
current_implementation = "default"
agent_manager = None

# Semáforo para controlar execuções simultâneas
task_execution_lock = asyncio.Semaphore(1)

def get_agent_manager():
    """Get the current agent manager instance"""
    global agent_manager
    if agent_manager is None:
        agent_manager = agent_implementations[current_implementation]()
    return agent_manager

# Store for task results and input requests
task_store: Dict[str, Dict[str, Any]] = {}
input_requests: Dict[str, Dict[str, Any]] = {}

class TaskRequest(BaseModel):
    task: str
    description: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    waiting_for_input: Optional[bool] = False
    input_prompt: Optional[str] = None
    total_tokens: Optional[int] = None
    logs: Optional[List[str]] = None  # Separar logs do resultado final

class UserInputRequest(BaseModel):
    input: str

class ChatRequest(BaseModel):
    message: str

@app.on_event("startup")
async def startup_event():
    """Initialize the agent manager on startup"""
    try:
        await get_agent_manager().initialize()
        await get_agent_manager().restart_team()  # Força reset do time logo após inicialização
        get_agent_manager().set_input_callback(handle_agent_input_request)
        logger.info("Agent manager initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize agent manager: {e}")

async def handle_agent_input_request(request_data: Dict[str, Any]):
    """Handle input request from agents"""
    task_id = get_agent_manager().current_task_id
    if task_id and task_id in task_store:
        # Store the input request
        input_requests[task_id] = request_data
        
        # Update task status
        task_store[task_id]["status"] = "waiting_for_input"
        task_store[task_id]["waiting_for_input"] = True
        task_store[task_id]["input_prompt"] = request_data.get("prompt", "Input needed")
        
        logger.info(f"Task {task_id} is waiting for user input: {request_data.get('prompt')}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "NF Agent Service",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "create_task": "POST /tasks/",
            "get_task": "GET /tasks/{task_id}",
            "list_tasks": "GET /tasks/",
            "stream_task": "POST /tasks/{task_id}/stream",
            "provide_input": "POST /tasks/{task_id}/input",
            "delete_task": "DELETE /tasks/{task_id}",
            "web_interface": "/static/index.html"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nf_agent"}

@app.get("/status")
async def status_check():
    """Status check endpoint"""
    return {"status": "online", "service": "nf_agent"}

@app.get("/agent-implementations")
async def get_agent_implementations():
    """Get available agent implementations"""
    return {
        "implementations": list(agent_implementations.keys()),
        "current": current_implementation
    }

@app.post("/agent-implementations/{implementation}")
async def switch_agent_implementation(implementation: str):
    """Switch to a different agent implementation"""
    global current_implementation, agent_manager
    
    if implementation not in agent_implementations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid implementation. Available: {list(agent_implementations.keys())}"
        )
    
    # Stop current agent manager if it exists
    if agent_manager is not None:
        await agent_manager.cleanup()
    
    # Switch implementation
    current_implementation = implementation
    agent_manager = None
    
    # Initialize new implementation
    try:
        await get_agent_manager().initialize()
        get_agent_manager().set_input_callback(handle_agent_input_request)
        return {"status": "success", "message": f"Switched to {implementation} implementation"}
    except Exception as e:
        logger.error(f"Failed to switch agent implementation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch implementation: {str(e)}"
        )

@app.post("/tasks/", response_model=TaskResponse)
async def create_task(task_request: TaskRequest):
    """Create a new task for the agents to process"""
    try:
        task_id = str(uuid.uuid4())
        
        # Log de debug para entender o timing
        logger.info(f"Creating task {task_id}: {task_request.task[:100]}...")
        
        # Verifica se já há uma tarefa rodando APENAS para criação de novas tasks
        if task_execution_lock.locked():
            # Dar mais detalhes sobre o que está acontecendo
            running_count = len([tid for tid, task in task_store.items() 
                               if task.get("status") in ["running", "streaming", "processing"]])
            logger.warning(f"Task creation blocked - execution semaphore locked. Running tasks: {running_count}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Sistema processando outra tarefa. Aguarde alguns segundos e tente novamente. (Tarefas ativas: {running_count})"
            )
        
        # Store task info
        task_store[task_id] = {
            "task_id": task_id,
            "status": "created",
            "task": task_request.task,
            "description": task_request.description,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "result": None,
            "error": None,
            "waiting_for_input": False,
            "input_prompt": None,
            "total_tokens": None,
            "logs": [],  # Inicializar lista vazia para logs
            "team_ready_for_stream": True  # Immediately ready for streaming
        }
        
        # Don't start background processing - let streaming handle execution
        # asyncio.create_task(process_task_background(task_id, task_request.task, task_request.description))
        
        logger.info(f"Task {task_id} created and dispatched successfully")
        
        return TaskResponse(
            task_id=task_id,
            status="created",
            message="Task created and processing started"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@app.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a specific task"""
    if task_id not in task_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return TaskStatus(**task_store[task_id])

# Duplicate route with trailing slash for compatibility
@app.get("/tasks/{task_id}/", response_model=TaskStatus)
async def get_task_status_with_slash(task_id: str):
    """Get the status of a specific task (with trailing slash version)"""
    if task_id not in task_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return TaskStatus(**task_store[task_id])

# Duplicate route without trailing slash for compatibility
@app.get("/tasks", response_model=list)
async def list_tasks_no_slash():
    """List all tasks (no trailing slash version)"""
    # Retornar as tarefas ordenadas por data de criação (mais recentes primeiro)
    tasks = list(task_store.values())
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    return tasks[:10]  # Retornar apenas as 10 tarefas mais recentes

@app.get("/tasks/")
async def list_tasks():
    """List all tasks"""
    # Retornar as tarefas ordenadas por data de criação (mais recentes primeiro)
    tasks = list(task_store.values())
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    return tasks[:10]  # Retornar apenas as 10 tarefas mais recentes

@app.post("/tasks/{task_id}/input")
async def provide_task_input(task_id: str, user_input: UserInputRequest):
    """Provide user input for a task that is waiting for input"""
    if task_id not in task_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    task_info = task_store[task_id]
    
    if not task_info.get("waiting_for_input", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is not waiting for input"
        )
    
    try:
        # Provide input to the agent manager
        get_agent_manager().provide_user_input(user_input.input)
        
        # Update task status
        task_info["waiting_for_input"] = False
        task_info["input_prompt"] = None
        task_info["status"] = "processing"
        
        # Remove from input requests
        if task_id in input_requests:
            del input_requests[task_id]
        
        logger.info(f"User input provided for task {task_id}: {user_input.input}")
        
        return {"message": "Input provided successfully", "status": "processing"}
        
    except Exception as e:
        logger.error(f"Error providing input for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error providing input: {str(e)}"
        )

def safe_json(obj):
    """
    Simplified approach: convert everything to readable string format
    instead of trying to serialize complex Autogen objects
    """
    try:
        # If it's already a simple dict with expected fields, keep as JSON
        if isinstance(obj, dict) and ('type' in obj or 'message' in obj or 'content' in obj):
            return json.dumps(obj)
    except:
        pass
    
    # For everything else, convert to a simple string message
    content_str = str(obj)
    
    # Extract useful information from the string representation
    source = 'system'
    if 'FunctionCall' in content_str or 'FunctionExecutionResult' in content_str:
        # Skip complex function calls - they're not useful for the chat UI
        return None
    
    # Try to identify the speaker from common patterns
    if hasattr(obj, 'source'):
        source = getattr(obj, 'source', 'system')
    elif hasattr(obj, 'name'):
        source = getattr(obj, 'name', 'system')
    elif 'assistant' in content_str.lower():
        source = 'assistant'
    elif 'user' in content_str.lower():
        source = 'user'
    
    # Return a simple JSON structure - NO TRUNCATION
    simple_message = {
        "type": "message",
        "source": source,
        "content": content_str,
        "timestamp": None
    }
    
    return json.dumps(simple_message)

# Add route without trailing slash for streaming compatibility  
@app.post("/tasks/{task_id}/stream")
async def stream_task_no_slash(task_id: str):
    """Stream the execution of a task in real-time (no trailing slash version)"""
    return await stream_task_with_slash(task_id)

@app.post("/tasks/{task_id}/stream/")
async def stream_task_with_slash(task_id: str):
    """Stream the execution of a task in real-time"""
    if task_id not in task_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    async def generate_stream():
        try:
            task_info = task_store[task_id]
            
            # No longer need to wait for team ready since we're handling execution here
            logger.info(f"Stream {task_id} - Starting execution and streaming.")
            task_info["status"] = "streaming"
            
            # Get the manager and ensure it's ready
            manager = get_agent_manager()
            if not manager.initialized or not manager.team:
                await manager.restart_team()
                
            # Variables to collect result
            all_messages = []
            total_tokens = 0
            final_result = None
            task_logs = []  # Logs separados do resultado final
            
            # Executar tarefa no background para capturar resultado completo com tokens
            async def execute_task():
                nonlocal final_result, total_tokens
                try:
                    logger.info(f"[BACKGROUND] Starting background execution for task {task_id}")
                    result = await manager.run_task(task_info["task"], task_id)
                    final_result = result
                    
                    # Debug: mostrar estrutura do resultado para entender onde estão os tokens
                    logger.debug(f"[BACKGROUND] Result type: {type(result)}")
                    result_str = str(result)
                    logger.debug(f"[BACKGROUND] Result preview: {result_str[:500]}...")
                    
                    # Extrair tokens do resultado completo usando a função simples
                    total_tokens = extract_tokens_from_logs(result)
                    logger.info(f"Task {task_id} - Background execution completed with {total_tokens} tokens")
                except Exception as e:
                    logger.error(f"Task {task_id} - Background execution failed: {e}")
                    final_result = {"error": str(e)}
            
            # Iniciar execução em background
            background_task = asyncio.create_task(execute_task())
            
            # Variables for message grouping - aguardar mensagens completas
            pending_messages = []
            last_message_time = None
            GROUPING_DELAY = 0.8  # Reduzido para 0.8s - mais responsivo para cada agente
            
            async def flush_pending_messages():
                """Send accumulated messages as complete responses"""
                if pending_messages:
                    logger.info(f"[STREAM] Flushing {len(pending_messages)} pending messages")
                    # Agrupar por fonte para criar mensagens coerentes
                    grouped_by_source = {}
                    
                    for msg in pending_messages:
                        source = msg.get('source', 'System')
                        content = msg.get('content', '')
                        
                        if source not in grouped_by_source:
                            grouped_by_source[source] = []
                        grouped_by_source[source].append(content)
                    
                    # Enviar mensagens completas por fonte
                    for source, contents in grouped_by_source.items():
                        combined_content = ' '.join(contents).strip()
                        if combined_content and len(combined_content) > 1:  # Reduzido de 5 para 1 char - enviar qualquer conteúdo
                            logger.info(f"[STREAM] Sending message from {source}: {combined_content[:100]}...")
                            yield f"data: [{source}] {combined_content}\n\n"
                    
                    pending_messages.clear()
            
            # Stream the task execution
            try:
                logger.info(f"[STREAM] Starting streaming for task {task_id}")
                async for message in manager.run_task_stream(task_info["task"], task_id):
                    # Collect messages for final result - incluindo logs para extração de tokens
                    all_messages.append(message)
                    
                    # Adicionar aos logs da task (versão string para armazenamento)
                    log_entry = str(message)
                    task_logs.append(log_entry)
                    
                    # Debug: capturar qualquer informação de tokens se disponível
                    message_str = str(message)
                    if "prompt_tokens" in message_str or "completion_tokens" in message_str:
                        logger.debug(f"[TOKENS] Token info found in stream: {message_str[:300]}...")
                    
                    # Check if we're waiting for input
                    if task_info.get("waiting_for_input", False):
                        # Flush any pending messages before input request
                        async for flushed in flush_pending_messages():
                            yield flushed
                        yield f"data: {safe_json({'type': 'input_request', 'prompt': task_info.get('input_prompt', 'Input needed')})}\n\n"
                    
                    # For Autogen messages, try sending as simple text first
                    message_text = str(message)
                    logger.debug(f"[STREAM] Processing message: {message_text[:200]}...")
                    
                    # Skip complex function calls completely
                    if 'FunctionCall' in message_text or 'FunctionExecutionResult' in message_text:
                        logger.debug(f"[STREAM] Skipping function call message")
                        continue
                    
                    # Try to extract a clean message content
                    content = None
                    source = 'System'
                    
                    if hasattr(message, 'content'):
                        content = getattr(message, 'content', '')
                        source = getattr(message, 'source', 'Agent')
                    elif isinstance(message, dict) and 'content' in message:
                        content = message.get('content', '')
                        source = message.get('source', 'Agent')
                    else:
                        # Fallback: use string representation if meaningful
                        if message_text.strip() and not message_text.startswith('{'):
                            content = message_text
                            source = 'System'
                    
                    # Add to pending messages if we have content
                    if content and isinstance(content, str) and len(content.strip()) > 0:
                        logger.info(f"[STREAM] Adding message to pending: {source} -> {content[:100]}...")
                        pending_messages.append({
                            'content': content.strip(),
                            'source': source
                        })
                        last_message_time = asyncio.get_event_loop().time()
                        
                        # Enviar mensagens imediatamente quando são úteis, não aguardar acúmulo
                        # Só aguardar acúmulo se for muito curto (provavelmente parte de algo maior)
                        if len(content.strip()) > 10 or len(pending_messages) >= 2:  # Mais responsivo
                            logger.info(f"[STREAM] Triggering flush due to content length ({len(content.strip())}) or count ({len(pending_messages)})")
                            async for flushed in flush_pending_messages():
                                yield flushed
            except Exception as e:
                logger.error(f"Streaming error: {e}")
            
            logger.info(f"[STREAM] Stream loop ended, waiting for background task")
            # Aguardar conclusão da tarefa em background
            await background_task
            
            logger.info(f"[STREAM] Background task completed, flushing remaining messages")
            # Flush any remaining pending messages
            async for flushed in flush_pending_messages():
                yield flushed
            
            # Final status update - save the complete result
            if not task_info.get("waiting_for_input", False):
                task_store[task_id]["status"] = "completed"
                task_store[task_id]["completed_at"] = datetime.now().isoformat()
                
                # Usar tokens da execução background (mais preciso) OU extrair dos logs se não houver
                if final_result and total_tokens > 0:
                    final_tokens = total_tokens
                    logger.info(f"[TOKENS] Usando tokens da execução background: {final_tokens}")
                else:
                    # Fallback: extrair dos logs completos se background falhou
                    logger.info(f"[TOKENS] Extraindo tokens dos logs - tipo: {type(all_messages)}, length: {len(all_messages) if isinstance(all_messages, list) else 'N/A'}")
                    
                    # Debug: mostrar estrutura dos logs
                    if all_messages:
                        if isinstance(all_messages, list) and len(all_messages) > 0:
                            logger.debug(f"[TOKENS] Primeiro item dos logs: {type(all_messages[0])}: {str(all_messages[0])[:200]}...")
                        
                    final_tokens = extract_tokens_from_logs(all_messages)
                    logger.info(f"[TOKENS] Resultado da extração dos logs: {final_tokens}")
                
                task_store[task_id]["total_tokens"] = final_tokens
                
                # Salvar logs separadamente do resultado final
                task_store[task_id]["logs"] = task_logs[:100]  # Limitar a 100 entradas para evitar overhead
                
                # Para o resultado final, procurar pela última mensagem com source 'unknown'
                final_result_content = None
                
                # Procurar pela última mensagem com source 'unknown' nas mensagens coletadas do streaming
                if all_messages:
                    logger.info(f"[RESULT] Procurando última mensagem com source 'unknown' em {len(all_messages)} mensagens coletadas...")
                    
                    for message in reversed(all_messages):
                        # Verificar se é um objeto com source 'unknown'
                        if hasattr(message, 'source') and getattr(message, 'source') == 'unknown':
                            final_result_content = str(getattr(message, 'content', str(message)))
                            logger.info(f"[RESULT] Encontrada mensagem com source 'unknown': {final_result_content[:100]}...")
                            break
                        # Se for string, tentar parsear como JSON para verificar source
                        elif isinstance(message, str):
                            try:
                                parsed = json.loads(message)
                                if isinstance(parsed, dict) and parsed.get('source') == 'unknown':
                                    final_result_content = parsed.get('content', str(parsed))
                                    logger.info(f"[RESULT] Encontrada mensagem JSON com source 'unknown': {final_result_content[:100]}...")
                                    break
                            except:
                                continue
                
                # Se não encontrou nas mensagens do streaming, tentar no resultado da execução background
                if not final_result_content and final_result and "result" in final_result:
                    result_data = final_result["result"]
                    if hasattr(result_data, 'messages') and len(result_data.messages) > 0:
                        # Procurar pela última mensagem com source 'unknown'
                        for message in reversed(result_data.messages):
                            if hasattr(message, 'source') and getattr(message, 'source') == 'unknown':
                                final_result_content = str(getattr(message, 'content', str(message)))
                                logger.info(f"[RESULT] Encontrada mensagem com source 'unknown' no background: {final_result_content[:100]}...")
                                break
                        
                        # Fallback: última mensagem se não houver 'unknown'
                        if not final_result_content:
                            last_message = result_data.messages[-1]
                            final_result_content = str(getattr(last_message, 'content', str(last_message)))
                    else:
                        final_result_content = str(serialize_message(result_data))
                
                # Fallback final se não encontrou nenhuma mensagem com source 'unknown'
                if not final_result_content:
                    logger.info(f"[RESULT] Nenhuma mensagem com source 'unknown' encontrada, usando fallback...")
                    if task_logs:
                        # Usar a última entrada substantiva dos logs
                        for log_entry in reversed(task_logs[-10:]):
                            if len(log_entry.strip()) > 20 and 'TERMINATE' not in log_entry:
                                final_result_content = log_entry.strip()
                                break
                        else:
                            final_result_content = "Task completed successfully"
                    else:
                        final_result_content = "Task completed successfully"
                
                task_store[task_id]["result"] = final_result_content
                logger.info(f"[RESULT] Resultado final salvo: {final_result_content[:200]}...")
                yield f"data: {safe_json({'type': 'completion', 'message': 'Task completed', 'total_tokens': final_tokens})}\n\n"
            
        except Exception as e:
            logger.error(f"Error streaming task {task_id}: {e}", exc_info=True)
            if task_id in task_store:
                task_store[task_id]["status"] = "failed"
                task_store[task_id]["completed_at"] = datetime.now().isoformat()
                error_message = f"Error during execution: {str(e)}"
                task_store[task_id]["result"] = error_message
                task_store[task_id]["error"] = str(e)
                task_store[task_id]["logs"] = [error_message]  # Incluir erro nos logs
            yield f"data: {safe_json({'type': 'error', 'message': f'Erro durante a execução: {str(e)}'})}\\n\\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream", # Mudado para text/event-stream para SSE
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task from the store"""
    if task_id not in task_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Clean up input requests too
    if task_id in input_requests:
        del input_requests[task_id]
    
    del task_store[task_id]
    return {"message": f"Task {task_id} deleted successfully"}

async def process_task_background(task_id: str, task_content: str, description: str = ""):
    """Process task in background"""
    manager = get_agent_manager()
    result = None
    result_data = None
    try:
        # Aguardar semáforo com timeout
        logger.info(f"Task {task_id} - Aguardando liberação do semáforo de execução...")
        if not await asyncio.wait_for(task_execution_lock.acquire(), timeout=30.0):
            logger.error(f"Task {task_id} - Timeout ao aguardar semáforo")
            if task_id in task_store:
                task_store[task_id]["status"] = "failed"
                error_message = "Erro: Sistema ocupado - timeout ao adquirir semáforo"
                task_store[task_id]["result"] = error_message
                task_store[task_id]["error"] = "Timeout acquiring execution lock"
                task_store[task_id]["completed_at"] = datetime.now().isoformat()
                task_store[task_id]["total_tokens"] = 0
                task_store[task_id]["logs"] = [error_message]  # Incluir erro nos logs
            return
        
        try:
            logger.info(f"Task {task_id} - Semáforo adquirido, iniciando processamento...")
            
            # Verificar se já existe uma tarefa rodando (verificação extra, semáforo é o principal)
            running_tasks = [tid for tid, task in task_store.items() 
                           if task.get("status") in ["running", "streaming"] and tid != task_id]
            if running_tasks:
                logger.warning(f"Task {task_id} - Tarefas ainda em execução: {running_tasks}. Aguardando...")
                await asyncio.sleep(2) # Pequeno delay adicional
            
            # Restart team antes da execução para garantir estado limpo
            logger.info(f"Task {task_id} - Executando restart preventivo do team...")
            await manager.restart_team() # Garante que o manager e seu team estão limpos
            
            # Verificar se o manager está pronto
            if not manager.initialized or not manager.team:
                logger.error(f"Task {task_id} - Manager não inicializado adequadamente após restart.")
                # Tentar inicializar novamente como último recurso
                await manager.initialize()
                if not manager.initialized or not manager.team:
                    logger.error(f"Task {task_id} - Falha crítica: Manager não pôde ser inicializado.")
                    raise RuntimeError("Manager initialization failed critically.")
            
            # Aguardar um pouco para garantir que tudo está estabilizado
            await asyncio.sleep(1) 
            
            # Update task store with running status e sinalizar que o team está pronto
            if task_id in task_store:
                task_store[task_id]["status"] = "running"
                task_store[task_id]["started_at"] = datetime.now().isoformat()
                task_store[task_id]["team_ready_for_stream"] = True # SINALIZAÇÃO
                logger.info(f"Task {task_id} - Team pronto para stream e execução principal.")

            # Execute task
            logger.info(f"Task {task_id} - Iniciando execução da tarefa Autogen...")
            result = await manager.run_task(task_content, task_id)
            logger.info(f"Task {task_id} - Tarefa Autogen executada com sucesso.")
            
            # Update task store with result
            if task_id in task_store:
                task_store[task_id]["status"] = "completed"
                task_store[task_id]["completed_at"] = datetime.now().isoformat()
                result_data = result.get("result")
                
                # Separar logs do resultado final como no streaming
                if result_data:
                    # Extrair logs para contagem de tokens
                    result_logs = [str(result_data)]
                    task_store[task_id]["logs"] = result_logs
                    
                    # Para o resultado final, procurar pela última mensagem com source 'unknown'
                    final_result_content = None
                    
                    if hasattr(result_data, 'messages') and len(result_data.messages) > 0:
                        # Procurar pela última mensagem com source 'unknown'
                        for message in reversed(result_data.messages):
                            if hasattr(message, 'source') and getattr(message, 'source') == 'unknown':
                                final_result_content = str(getattr(message, 'content', str(message)))
                                logger.info(f"[RESULT] Encontrada mensagem com source 'unknown': {final_result_content[:100]}...")
                                break
                        
                        # Fallback: última mensagem se não houver 'unknown'
                        if not final_result_content:
                            last_message = result_data.messages[-1]
                            final_result_content = str(getattr(last_message, 'content', str(last_message)))
                    else:
                        final_result_content = str(serialize_message(result_data))
                    
                    task_store[task_id]["result"] = final_result_content
                else:
                    task_store[task_id]["logs"] = []
                    task_store[task_id]["result"] = "Task completed successfully"
                
                # Usar extração simples de tokens dos logs, não do resultado
                final_tokens = extract_tokens_from_logs(task_store[task_id]["logs"])
                task_store[task_id]["total_tokens"] = final_tokens
                logger.info(f"Task {task_id} completed successfully with {final_tokens} tokens")
            
        except Exception as e:
            logger.error(f"Task {task_id} - Erro durante execução principal: {str(e)}", exc_info=True)
            if task_id in task_store:
                task_store[task_id]["status"] = "failed"
                task_store[task_id]["team_ready_for_stream"] = True # Mesmo em erro, o team foi tentado, então o stream pode tentar pegar o erro
                task_store[task_id]["completed_at"] = datetime.now().isoformat()
                error_message = f"Erro na execução principal: {str(e)}"
                task_store[task_id]["result"] = error_message 
                task_store[task_id]["error"] = str(e)
                task_store[task_id]["logs"] = [error_message]  # Incluir erro nos logs também
                
                # Usar extração simples de tokens dos logs
                final_tokens = extract_tokens_from_logs(task_store[task_id]["logs"]) if task_store[task_id]["logs"] else 0
                task_store[task_id]["total_tokens"] = final_tokens
                logger.info(f"Task {task_id} FAILED. Tokens (best effort): {final_tokens}")

        finally:
            # Liberar semáforo
            if task_execution_lock.locked(): # Apenas liberar se este processo adquiriu
                 logger.info(f"Task {task_id} - Liberando semáforo de execução.")
                 task_execution_lock.release()
            else:
                 logger.warning(f"Task {task_id} - Semáforo já estava liberado ao final do processamento.")
            # Log final do estado da task no store
            if task_id in task_store:
                 logger.info(f"Task {task_id} - Estado final no store: status={task_store[task_id].get('status')}, tokens={task_store[task_id].get('total_tokens')}")
            
    except asyncio.TimeoutError:
        logger.error(f"Task {task_id} - Timeout geral ao aguardar semáforo")
        if task_id in task_store:
            task_store[task_id]["status"] = "failed"
            error_message = "Erro: Timeout geral ao aguardar semáforo"
            task_store[task_id]["result"] = error_message
            task_store[task_id]["error"] = "Overall timeout waiting for execution lock"
            task_store[task_id]["completed_at"] = datetime.now().isoformat()
            task_store[task_id]["total_tokens"] = 0
            task_store[task_id]["logs"] = [error_message]  # Incluir erro nos logs
            task_store[task_id]["team_ready_for_stream"] = True # Sinaliza para stream não ficar preso
    except Exception as e:
        logger.error(f"Task {task_id} - Erro crítico não tratado em process_task_background: {str(e)}", exc_info=True)
        if task_id in task_store:
            task_store[task_id]["status"] = "failed"
            error_message = f"Erro crítico no processamento: {str(e)}"
            task_store[task_id]["result"] = error_message
            task_store[task_id]["error"] = f"Critical unhandled error: {str(e)}"
            task_store[task_id]["completed_at"] = datetime.now().isoformat()
            task_store[task_id]["total_tokens"] = 0
            task_store[task_id]["logs"] = [error_message]  # Incluir erro nos logs
            task_store[task_id]["team_ready_for_stream"] = True # Sinaliza para stream não ficar preso

@app.post("/restart-agents/")
async def restart_agents():
    """Restart the agent team"""
    start_time = datetime.now()
    try:
        logger.info("Iniciando processo de restart dos agentes...")
        
        # Aguarda que qualquer tarefa em execução termine
        logger.info("Aguardando liberação do semáforo de execução...")
        async with task_execution_lock:
            logger.info("Semáforo adquirido, iniciando restart...")
            
            # Limpar store de tasks pendentes se necessário
            running_tasks = [tid for tid, task in task_store.items() if task.get("status") in ["running", "streaming"]]
            if running_tasks:
                logger.info(f"Limpando {len(running_tasks)} tarefas em execução: {running_tasks}")
                for task_id in running_tasks:
                    task_store[task_id]["status"] = "cancelled"
                    error_message = "Cancelled due to agent restart"
                    task_store[task_id]["error"] = error_message
                    task_store[task_id]["completed_at"] = datetime.now().isoformat()
                    task_store[task_id]["logs"] = [error_message]  # Incluir motivo do cancelamento nos logs
            
            # Executar restart
            await get_agent_manager().restart_team()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Agent team restarted successfully in {duration:.2f} seconds")
            return {
                "status": "success", 
                "message": "Agent team restarted successfully",
                "duration_seconds": duration,
                "cancelled_tasks": len(running_tasks) if running_tasks else 0,
                "timestamp": end_time.isoformat()
            }
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        error_msg = f"Failed to restart agent team after {duration:.2f} seconds: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@app.get("/agent-status/")
async def get_agent_status():
    """Get detailed status of the agent team for diagnostics"""
    try:
        manager = get_agent_manager()
        status_info = {
            "initialized": manager.initialized,
            "has_team": manager.team is not None,
            "has_model_client": manager.model_client is not None,
            "has_model_client2": manager.model_client2 is not None,
            "has_user_proxy": manager.user_proxy is not None,
            "current_task_id": manager.current_task_id,
            "total_tokens": manager.total_tokens,
            "chat_enabled": manager.chat_enabled,
            "has_input_callback": manager.input_callback is not None,
            "has_log_callback": manager.log_callback is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Se o team existir, adicionar informações sobre os agentes
        if manager.team:
            try:
                if hasattr(manager.team, 'agents'):
                    status_info["agents"] = list(manager.team.agents.keys()) if manager.team.agents else []
                elif hasattr(manager.team, '_agents'):
                    status_info["agents"] = [agent.name for agent in manager.team._agents] if manager.team._agents else []
                else:
                    status_info["agents"] = ["Unable to determine agents"]
            except Exception as e:
                status_info["agents_error"] = str(e)
        
        # Informações sobre tarefas em execução
        running_tasks = [tid for tid, task in task_store.items() if task.get("status") in ["running", "streaming", "pending"]]
        status_info["running_tasks_count"] = len(running_tasks)
        status_info["running_tasks"] = running_tasks[:5]  # Máximo 5 para não sobrecarregar
        
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/force-clean/")
async def force_clean_tasks():
    """Force clean any stuck tasks and reset team state"""
    try:
        logger.info("Iniciando limpeza forçada do sistema...")
        
        # Identificar tarefas potencialmente travadas
        stuck_tasks = []
        current_time = datetime.now()
        
        for task_id, task_data in task_store.items():
            if task_data.get("status") in ["running", "streaming"]:
                # Verificar se a tarefa está rodando há muito tempo (mais de 5 minutos)
                started_at = task_data.get("started_at")
                if started_at:
                    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    if (current_time - start_time.replace(tzinfo=None)).total_seconds() > 300:  # 5 minutos
                        stuck_tasks.append(task_id)
        
        # Marcar tarefas travadas como failed
        for task_id in stuck_tasks:
            logger.warning(f"Marcando tarefa travada como failed: {task_id}")
            task_store[task_id]["status"] = "failed"
            error_message = "Tarefa interrompida por limpeza forçada"
            task_store[task_id]["result"] = error_message
            task_store[task_id]["completed_at"] = datetime.now().isoformat()
            task_store[task_id]["logs"] = [error_message]  # Incluir motivo nos logs
        
        # Forçar liberação do semáforo se estiver travado
        if task_execution_lock.locked():
            logger.warning("Forçando liberação do semáforo travado...")
            # Reset do semáforo
            task_execution_lock._value = 1
            task_execution_lock._waiters.clear()
        
        # Restart forçado do team
        manager = get_agent_manager()
        await manager.restart_team()
        
        logger.info(f"Limpeza forçada concluída. Tarefas limpas: {len(stuck_tasks)}")
        
        return {
            "message": "Sistema limpo com sucesso",
            "stuck_tasks_cleaned": len(stuck_tasks),
            "cleaned_task_ids": stuck_tasks,
            "semaphore_reset": True,
            "team_restarted": True
        }
        
    except Exception as e:
        logger.error(f"Erro durante limpeza forçada: {str(e)}", exc_info=True)
        return {"error": f"Erro durante limpeza: {str(e)}"}

def extract_tokens_from_logs(logs_or_result):
    """
    Extrai tokens dos logs de uma task de forma simples usando regex.
    Procura por padrões como "prompt_tokens":123,"completion_tokens":456
    """
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    # Converter para string se necessário
    if isinstance(logs_or_result, (list, dict)):
        text = str(logs_or_result)
    else:
        text = str(logs_or_result)
    
    # Procurar por padrões de tokens nos logs - especialmente dos logs autogen_core.events
    prompt_patterns = [
        r'"prompt_tokens":\s*(\d+)',
        r'prompt_tokens=(\d+)',
        r'prompt_tokens":\s*(\d+)',
        r'"prompt_tokens":\s?(\d+)',  # Variação sem espaço
        r'RequestUsage\(prompt_tokens=(\d+)',  # Formato RequestUsage
    ]
    
    completion_patterns = [
        r'"completion_tokens":\s*(\d+)',
        r'completion_tokens=(\d+)', 
        r'completion_tokens":\s*(\d+)',
        r'"completion_tokens":\s?(\d+)',  # Variação sem espaço
        r'RequestUsage\([^)]*completion_tokens=(\d+)', # Formato RequestUsage
    ]
    
    # Aplicar todos os padrões para prompt tokens
    for pattern in prompt_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            total_prompt_tokens += int(match)
            logger.debug(f"[TOKENS] Encontrado prompt_tokens: {match} (padrão: {pattern})")
    
    # Aplicar todos os padrões para completion tokens
    for pattern in completion_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            total_completion_tokens += int(match)
            logger.debug(f"[TOKENS] Encontrado completion_tokens: {match} (padrão: {pattern})")
    
    total_tokens = total_prompt_tokens + total_completion_tokens
    
    if total_tokens > 0:
        logger.info(f"Tokens extraídos dos logs: {total_prompt_tokens} prompt + {total_completion_tokens} completion = {total_tokens} total")
    else:
        logger.warning("Nenhum token encontrado nos logs")
        # Debug: mostrar uma parte dos logs para verificar o formato
        if len(text) > 500:
            # Procurar por linhas que contenham "prompt_tokens" ou "completion_tokens"
            lines_with_tokens = [line for line in text.split('\n') if 'prompt_tokens' in line or 'completion_tokens' in line]
            if lines_with_tokens:
                logger.debug(f"Linhas com tokens encontradas: {lines_with_tokens[:3]}...")  # Mostrar até 3 linhas
            else:
                logger.debug(f"Amostra dos logs para debug: {text[:300]}...")
    
    return total_tokens

def serialize_message(msg):
    try:
        if hasattr(msg, "to_dict"):
            return msg.to_dict()
        elif hasattr(msg, "__dict__"):
            # Remove atributos não serializáveis se necessário
            return {k: serialize_message(v) for k, v in msg.__dict__.items() if not k.startswith('_')}
        elif isinstance(msg, (list, tuple)):
            return [serialize_message(m) for m in msg]
        else:
            return str(msg)
    except Exception as e:
        logger.error(f"Erro ao serializar mensagem do tipo {type(msg)}: {e}")
        return {"error": f"Erro ao serializar objeto do tipo {type(msg).__name__}", "repr": repr(msg)}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Endpoint para chat com agentes"""
    
    global current_task_id
    current_task_id = str(uuid.uuid4())
    logger.info(f"Iniciando chat com task_id: {current_task_id}")
    
    try:
        # Valida se há um agent manager
        if agent_manager is None:
            raise HTTPException(status_code=503, detail="Agente não inicializado")
        
        # Obtém os agentes do manager atual
        agents = agent_manager.get_agents()
        
        # Cria o time baseado na implementação escolhida
        if current_implementation == "sel_group":
            team = create_selector_group(agents, request.message)
        else:  # default (swarm)
            team = create_swarm_group(agents, request.message)
        
        # Inicia o chat com a mensagem do usuário
        result = await team.run(task=request.message)
        
        return {
            "response": str(result),
            "task_id": current_task_id,
            "implementation": current_implementation
        }
        
    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 