import os
import platform
import urllib.request
import logging
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class ModelDownloader(QObject):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, model_size="base"):
        super().__init__()
        self.model_size = model_size
        if platform.system() == "Windows":
            self.target_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
        elif platform.system() == "Darwin":
            self.target_dir = os.path.join(os.path.expanduser("~"), "Library", "Caches", "whisper")
        else:
            self.target_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
        self.url = f"https://openaipublic.azureedge.net/main/whisper/models/ed3a0d6b5343c131a985b23b57283907e5e7da71/{model_size}.pt"
        self.target_path = os.path.join(self.target_dir, f"{model_size}.pt")

    def is_model_present(self):
        return os.path.exists(self.target_path)

    def download(self):
        try:
            if not os.path.exists(self.target_dir):
                os.makedirs(self.target_dir)

            self.status_changed.emit("Baixando componentes de IA (necessário apenas uma vez)...")
            
            def _progress(block_num, block_size, total_size):
                if total_size > 0:
                    percent = int(block_num * block_size * 100 / total_size)
                    self.progress_changed.emit(min(percent, 100))

            urllib.request.urlretrieve(self.url, self.target_path, reporthook=_progress)
            self.finished.emit(True, "Download concluído!")
            
        except Exception as e:
            logger.error(f"Erro no download: {e}")
            self.finished.emit(False, f"Falha na conexão ou Firewall bloqueando: {e}")