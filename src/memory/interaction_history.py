from schemas.interaction_schema import Interaction

class StateManager:
    """
    A class to manage the state of the interaction history.
    It stores the history of interactions and provides methods to add, retrieve,
    and clear the history.
    """
    
    def __init__(self):
        self.interaction_history = []
        
    def add_interaction(self, interaction: Interaction):
        self.interaction_history.append(interaction)
        
    def get_last_interaction(self):
        if self.interaction_history:
            return self.interaction_history[-1]
        return None
    
    def get_interaction_history(self):
        return self.interaction_history
    
    def clear_interaction_history(self):
        self.interaction_history = []
        
state_manager = StateManager()