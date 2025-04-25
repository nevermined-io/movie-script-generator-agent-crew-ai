# """
# A2A Server implementation for the Movie Script Generator Agent
# """
# from typing import Dict, Any, Optional, List
# from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import StreamingResponse, JSONResponse
# from sse_starlette.sse import EventSourceResponse
# import json
# import uuid
# from datetime import datetime
# import asyncio
# from .core.task_processor import TaskProcessor
# from .models.task import Task, TaskStatus, Message, TaskState
# from .models.a2a import TaskSendParams, PushNotificationConfig
# from .models.agent_card import AGENT_CARD

# # Create FastAPI app
# app = FastAPI(title="Movie Script Generator A2A Agent")

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Load agent card
# @app.get("/.well-known/agent.json")
# async def get_agent_card():
#     """
#     Get the agent card with capabilities and metadata
#     """
#     return AGENT_CARD.dict()

# def get_task_processor() -> TaskProcessor:
#     """
#     Dependency injection for task processor
#     """
#     return TaskProcessor()

# # A2A Protocol endpoints
# @app.post("/tasks/send")
# async def send_task(task_params: Dict[str, Any], processor: TaskProcessor = Depends(get_task_processor)) -> Dict[str, Any]:
#     """
#     Send a task and get the initial response
    
#     This endpoint immediately returns the task in SUBMITTED state and starts processing in the background
#     """
#     try:
#         # Create and store task
#         task = await processor.create_task(task_params)
        
#         # Start processing in background
#         background_tasks = BackgroundTasks()
#         background_tasks.add_task(processor.process_task_async, task.id)
        
#         # Return immediate response with task in SUBMITTED state
#         return JSONResponse(
#             content=task.to_dict(),
#             background=background_tasks
#         )
            
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/tasks/sendSubscribe")
# async def send_task_subscribe(
#     request: Request,
#     task_params: Dict[str, Any],
#     processor: TaskProcessor = Depends(get_task_processor)
# ) -> EventSourceResponse:
#     """
#     Send a task and subscribe to updates via SSE
#     """
#     try:
#         # Create task first
#         task = await processor.create_task(task_params)
        
#         async def event_generator():
#             try:
#                 async for update in processor.get_task_updates(task.id):
#                     if isinstance(update, dict):
#                         yield {
#                             "event": "update",
#                             "data": json.dumps(update)
#                         }
#                     else:
#                         yield {
#                             "event": "update",
#                             "data": json.dumps(update.to_dict())
#                         }
#             except Exception as e:
#                 yield {
#                     "event": "error",
#                     "data": json.dumps({"error": str(e)})
#                 }
#                 return

#         return EventSourceResponse(event_generator())
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/tasks/{task_id}")
# async def get_task(task_id: str, processor: TaskProcessor = Depends(get_task_processor)) -> Dict[str, Any]:
#     """
#     Get a task by ID
#     """
#     try:
#         task = await processor.get_task(task_id)
#         if task is None:
#             raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
#         return task.to_dict() if not isinstance(task, dict) else task
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/tasks/{task_id}/cancel")
# async def cancel_task(task_id: str, processor: TaskProcessor = Depends(get_task_processor)) -> Dict[str, Any]:
#     """
#     Cancel an ongoing task
#     """
#     try:
#         task = await processor.cancel_task(task_id)
#         if not task:
#             raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
#         return task.to_dict() if not isinstance(task, dict) else task
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/tasks/{task_id}/pushNotification")
# async def set_push_notification(
#     task_id: str, 
#     config: PushNotificationConfig,
#     processor: TaskProcessor = Depends(get_task_processor)
# ) -> Dict[str, Any]:
#     """
#     Configure push notifications for a task
#     """
#     try:
#         result = await processor.set_push_notification(task_id, config)
#         return result.to_dict() if not isinstance(result, dict) else result
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/tasks/{task_id}/pushNotification")
# async def get_push_notification(
#     task_id: str,
#     processor: TaskProcessor = Depends(get_task_processor)
# ) -> Dict[str, Any]:
#     """
#     Get push notification configuration for a task
#     """
#     try:
#         config = await processor.get_push_notification(task_id)
#         if not config:
#             raise HTTPException(status_code=404, detail=f"No push notification config found for task {task_id}")
#         return config.to_dict() if not isinstance(config, dict) else config
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000) 