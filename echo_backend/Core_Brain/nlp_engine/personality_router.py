import sys
import os

# Add the echo_backend folder and its parent to sys.path
# This file is at: echo_backend/Core_Brain/nlp_engine/personality_router.py
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
project_root = os.path.dirname(backend_root)

if backend_root not in sys.path:
    sys.path.append(backend_root)
if project_root not in sys.path:
    sys.path.append(project_root)

from personalities.Suzi import Suzi
from personalities.EchoPersonality import EchoPersonality

class PersonalityRouter:
    def __init__(self):
        self.personalities = {
            "echo": EchoPersonality(),
            "suzi": Suzi(),
            # "mentor": MentorPersonality(),
            # "therapist": TherapistPersonality(),
            # "coach": CoachPersonality()
            # Add other personalities here as needed
        }

        self.active = "echo"  # default

    def set_personality(self, personality_name):
        # Normalize the name to lowercase for consistent lookup
        name = personality_name.lower()
        if name in self.personalities:
            self.active = name
        elif "suzi" in name:
            self.active = "suzi"
        elif "echo" in name:
            self.active = "echo"
        else:
            # Fallback to echo if not found, instead of raising error which crashes backend
            self.active = "echo"

    def get_response(self, user_input, memory, analysis=None):
        try:
            if self.active in self.personalities:
                return self.personalities[self.active].respond(user_input, memory, analysis)
            else:
                # Fallback to echo personality if active personality not found
                return self.personalities["echo"].respond(user_input, memory, analysis)
        except Exception as e:
            # Return a safe fallback response
            return "I'm having trouble processing your request right now. Please try again."