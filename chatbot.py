"""
Car Expert Chatbot - Single Input Mode
One input type: the model detects intent (consulting/mechanic/general) automatically.
"""

import json
import os
import uuid
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configuration
STORAGE = Path("chat_history")
STORAGE.mkdir(exist_ok=True)

SYSTEM_PROMPT = (
    "You are a professional car expert assistant who should sound natural and human. "
    "For each user message, detect intent automatically and adapt your response style: "
    "(1) consultant mode for buying/pricing/market guidance, "
    "(2) mechanic mode for diagnostics/repairs/maintenance, "
    "(3) general mode for other car topics. "
    "Do not force one fixed structure for every reply. Keep responses conversational and context-aware. "
    "Use short answers for simple questions and detailed answers for complex ones. "
    "Use bullets only when they improve clarity; otherwise reply in natural paragraphs. "
    "Ask a brief follow-up question only when required to give accurate advice. "
    "Prioritize safety for mechanical issues, avoid unnecessary repetition, and use prior chat context."
)

# ==================== Storage Functions ====================

def save_chat(session_id: str, messages: list):
    """Save conversation to JSON file"""
    path = STORAGE / f"{session_id}.json"
    with open(path, "w") as f:
        json.dump({"messages": messages}, f, indent=2)

def load_chat(session_id: str) -> list:
    """Load conversation from JSON file"""
    path = STORAGE / f"{session_id}.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f).get("messages", [])
    return []

def delete_chat(session_id: str):
    """Delete conversation file"""
    path = STORAGE / f"{session_id}.json"
    if path.exists():
        path.unlink()

# ==================== Main Chat Function ====================

def chat(session_id: str, user_message: str) -> dict:
    """
    Send one user input and get response with full conversation context.
    The model automatically understands intent from the message.
    """
    # Validate inputs
    if not user_message.strip():
        raise ValueError("Invalid message")
    
    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")
    
    client = OpenAI(api_key=api_key)
    
    # Load conversation history
    history = load_chat(session_id)
    
    # Build messages for API with one intent-aware system prompt and history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message.strip()})
    
    # Call OpenAI gpt-4o (best model for car consultation)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.9,
        top_p=0.95,
        presence_penalty=0.3,
        max_tokens=1500
    )
    
    # Extract response
    assistant_response = response.choices[0].message.content
    tokens_used = response.usage.total_tokens
    
    # Save to history
    history.append({"role": "user", "content": user_message.strip()})
    history.append({"role": "assistant", "content": assistant_response})
    save_chat(session_id, history)
    
    return {
        "session_id": session_id,
        "user_message": user_message,
        "response": assistant_response,
        "tokens": tokens_used
    }

# ==================== Helper Functions ====================

def get_history(session_id: str) -> dict:
    """Get conversation history"""
    messages = load_chat(session_id)
    if not messages:
        return None
    return {
        "session_id": session_id,
        "total_messages": len(messages),
        "messages": messages
    }

def clear_history(session_id: str):
    """Clear conversation"""
    delete_chat(session_id)
   
def new_session() -> str:
    """Create new session ID"""
    return str(uuid.uuid4())

# ==================== Interactive CLI ====================

def run_interactive():
    """Run interactive chatbot in terminal"""
    print("\n" + "=" * 50)
    print("CAR EXPERT CHATBOT")
    print("=" * 50)
    print("\nSingle input mode: ask anything about cars.")
    session_id = new_session()
    print(f"\nSession: {session_id[:8]}...")
    print("\nCommands: 'history' | 'clear' | 'exit'\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() == "exit":
                print("\nGoodbye!")
                break
            
            if user_input.lower() == "history":
                hist = get_history(session_id)
                if hist:
                    print(f"\n--- History ({hist['total_messages']} messages) ---")
                    for msg in hist['messages']:
                        print(f"\n[{msg['role'].upper()}]\n{msg['content']}\n")
                else:
                    print("No history yet.\n")
                continue
            
            if user_input.lower() == "clear":
                clear_history(session_id)
                session_id = new_session()
                print(f"✓ History cleared. New session: {session_id[:8]}...\n")
                continue
            
            # Send to chatbot
            print("\nLoading...")
            result = chat(session_id, user_input)
            print(f"\nEXPERT:\n{result['response']}\n")
            print(f"[Tokens: {result['tokens']}]\n")
            
        except KeyboardInterrupt:
            print("\n\nSession ended.")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

# ==================== Main Entry Point ====================

if __name__ == "__main__":
    run_interactive()
