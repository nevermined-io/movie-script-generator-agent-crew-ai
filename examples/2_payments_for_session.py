from src.core.payments import process_payments
import glob
import os

def get_latest_session_info():
    """
    Get the session ID and agent IDs from the latest session log file.
    
    Returns:
        tuple: (session_id, list of agent_ids) or (None, []) if no log file found
    """
    # Get all session log files
    log_files = glob.glob("src/logs/session_*.txt")
    
    if not log_files:
        return None, []
    
    # Get the most recent log file
    latest_file = max(log_files, key=os.path.getctime)
    
    try:
        with open(latest_file, 'r') as f:
            content = f.read()
            
        # Extract session ID
        session_id = None
        agent_ids = []
        
        for line in content.split('\n'):
            if line.startswith('Session ID:'):
                session_id = line.split('Session ID:')[1].strip()
            elif ':' in line and not line.startswith('Session ID:'):
                # Extract agent ID from lines like "AgentName: agent_id"
                agent_id = line.split(':')[1].strip()
                if agent_id:  # Only add non-empty agent IDs
                    agent_ids.append(agent_id)
        
        return session_id, agent_ids
    except Exception as e:
        print(f"Error reading session log file: {e}")
        return None, []

if __name__ == "__main__":
    # Get agent IDs and session ID from the latest session log file
    session_id, agent_ids = get_latest_session_info()
    
    if agent_ids:
        print(f"\nProcessing payments for session: {session_id}")
        print(f"Found {len(agent_ids)} agents:")
        for agent_id in agent_ids:
            print(f"- {agent_id}")
        process_payments(
            agent_ids=agent_ids,
            session_id=session_id,
            limit=50,
            offset=0
        )  # Default margin is 5% and default exchange rate is 1.0 credits/USD
    else:
        print("No agent IDs found in the latest session log file")

# custom_filter = {
# "request_response_rmt": {
# "latency": {
#     "gte": 0
# }
# }
# }