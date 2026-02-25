import sys
import os

# Add the echo_backend folder and its parent to sys.path
# This file is at: echo_backend/Core_Brain/__init__.py
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir)
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
            "Suzi": Suzi(),
            # "mentor": MentorPersonality(),
            # "therapist": TherapistPersonality(),
            # "coach": CoachPersonality()
            # Add other personalities here as needed
        }

        self.active = "echo"  # default

    def set_personality(self, personality_name):
        if personality_name in self.personalities:
            self.active = personality_name
        else:
            raise ValueError(f"Personality '{personality_name}' not found.")

    def get_response(self, user_input, memory):
        try:
            if self.active in self.personalities:
                return self.personalities[self.active].respond(user_input, memory)
            else:
                # Fallback to echo personality if active personality not found
                return self.personalities["echo"].respond(user_input, memory)
        except Exception as e:
            # Return a safe fallback response
            return "I'm having trouble processing your request right now. Please try again."