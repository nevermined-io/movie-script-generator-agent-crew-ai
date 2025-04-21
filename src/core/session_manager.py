"""
Session management for maintaining context between tasks.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..models.a2a import Message, Task

class Session:
    """Represents a conversation session with context."""
    def __init__(self, session_id: str):
        self.id = session_id
        self.tasks: List[Task] = []
        self.last_activity: datetime = datetime.utcnow()
        self.context: Dict = {
            "previous_scripts": [],
            "themes": set(),
            "characters": set()
        }

    def add_task(self, task: Task) -> None:
        """Add a task to the session history."""
        self.tasks.append(task)
        self.last_activity = datetime.utcnow()
        
        # Update context based on the task
        if task.status.message:
            self._update_context(task.status.message)

    def get_context_summary(self) -> str:
        """Get a summary of the session context."""
        return f"Previous scripts: {len(self.context['previous_scripts'])}, " \
               f"Themes: {', '.join(self.context['themes'])}, " \
               f"Characters: {', '.join(self.context['characters'])}"

    def _update_context(self, message: Message) -> None:
        """Update session context based on a message."""
        # Extract text from message parts
        text = " ".join(part.text for part in message.parts)
        
        # Update themes (simple keyword extraction)
        keywords = ["adventure", "romance", "action", "drama", "comedy"]
        self.context["themes"].update(
            theme for theme in keywords if theme.lower() in text.lower()
        )
        
        # Store script summary if it's a completed task
        if any(task.status.state == "completed" for task in self.tasks):
            self.context["previous_scripts"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "summary": text[:200] + "..."  # Store first 200 chars as summary
            })

class SessionManager:
    """Manages all active sessions."""
    def __init__(self, session_timeout: int = 30):
        self.sessions: Dict[str, Session] = {}
        self.session_timeout = timedelta(minutes=session_timeout)

    def get_session(self, session_id: str) -> Session:
        """Get or create a session."""
        self._cleanup_expired_sessions()
        
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(session_id)
        return self.sessions[session_id]

    def add_task_to_session(self, task: Task) -> None:
        """Add a task to its session if it has one."""
        if task.sessionId:
            session = self.get_session(task.sessionId)
            session.add_task(task)

    def get_session_context(self, session_id: str) -> Optional[Dict]:
        """Get the context for a session if it exists."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            return {
                "last_activity": session.last_activity.isoformat(),
                "task_count": len(session.tasks),
                "context": session.context
            }
        return None

    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if current_time - session.last_activity > self.session_timeout
        ]
        for session_id in expired_sessions:
            del self.sessions[session_id]

# Create a singleton instance
session_manager = SessionManager() 