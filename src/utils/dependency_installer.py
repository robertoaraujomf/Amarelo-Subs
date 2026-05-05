import subprocess
import sys
import importlib
import platform

class DependencyInstaller:
    """Instala dependências automaticamente de forma cross-platform"""

    def __init__(self):
        self.required_packages = [
            'PyQt6',
            'openai-whisper',
            'deep-translator',
            'setuptools',
            'requests',
        ]

    def install_required_packages(self):
        """Instala pacotes ausentes"""
        pip_cmd = [sys.executable, "-m", "pip"]
        if platform.system() == "Linux":
            pip_cmd.append("--user")

        for package in self.required_packages:
            try:
                importlib.import_module(self._get_module_name(package))
                print(f"  {package} já está instalado")
            except ImportError:
                print(f"Instalando {package}...")
                try:
                    subprocess.check_call(pip_cmd + ["install", package])
                    print(f"  {package} instalado com sucesso")
                except subprocess.CalledProcessError:
                    print(f"  Falha ao instalar {package}")

    def _get_module_name(self, package):
        """Obtém o nome do módulo para importação"""
        name_map = {
            'openai-whisper': 'whisper',
            'opencv-python': 'cv2',
            'python-dotenv': 'dotenv',
            'deep-translator': 'deep_translator',
        }
        return name_map.get(package, package.split('==')[0].split('>=')[0])