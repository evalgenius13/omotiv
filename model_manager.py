import torch
from demucs.pretrained import get_model

class ModelManager:
    def __init__(self, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    def load_model_safely(self, model_name, status_callback=None):
        try:
            if status_callback:
                status_callback(f"Loading model {model_name} on {self.device}...")
            if model_name.startswith("mdx"):
                # MDX is handled in processor; just pass path/name
                return model_name
            model = get_model(model_name)
            return model
        except Exception as e:
            if status_callback:
                status_callback(f"Error loading model {model_name}: {e}")
            raise