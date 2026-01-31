import os
from fastapi.responses import FileResponse

class ImageService:
    def __init__(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.cells_dir = os.path.join(base, "output", "cells")

    def serve_image(self, filename):
        file_path = os.path.join(self.cells_dir, filename)

        if not os.path.exists(file_path):
            return {"error": "Imagen no encontrada"}

        return FileResponse(file_path)
