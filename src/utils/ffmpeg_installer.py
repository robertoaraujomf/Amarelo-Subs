import os
import sys
import subprocess
import tempfile
import zipfile
import platform
import shutil

class FFmpegInstaller:
    """Instalador automático de FFmpeg para Windows, Linux e macOS"""

    def __init__(self):
        self.system = platform.system().lower()

    def check_ffmpeg(self):
        """Verifica se FFmpeg está disponível no PATH"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def install(self):
        """Instala FFmpeg automaticamente de acordo com o sistema"""
        if 'win' in self.system:
            return self._install_windows()
        elif 'linux' in self.system:
            return self._install_linux()
        elif 'darwin' in self.system:
            return self._install_macos()
        else:
            print(f"Sistema não suportado: {self.system}")
            return False

    def _install_windows(self):
        """Instala FFmpeg no Windows"""
        import winreg
        import requests
        
        print("Baixando FFmpeg para Windows...")
        
        # URL do FFmpeg para Windows (última versão estática)
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, 'ffmpeg.zip')
        
        try:
            # Download
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extrair
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Encontrar ffmpeg.exe
            ffmpeg_exe = None
            for root, dirs, files in os.walk(temp_dir):
                if 'ffmpeg.exe' in files:
                    ffmpeg_exe = os.path.join(root, 'ffmpeg.exe')
                    break
            
            if not ffmpeg_exe:
                print("Não encontrou ffmpeg.exe no arquivo baixado")
                return False
            
            # Criar pasta ffmpeg no projeto
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            ffmpeg_dir = os.path.join(project_dir, 'ffmpeg')
            os.makedirs(ffmpeg_dir, exist_ok=True)
            
            # Copiar executáveis
            bin_dir = os.path.dirname(ffmpeg_exe)
            for exe in ['ffmpeg.exe', 'ffplay.exe', 'ffprobe.exe']:
                src = os.path.join(bin_dir, exe)
                if os.path.exists(src):
                    dst = os.path.join(ffmpeg_dir, exe)
                    shutil.copy(src, dst)
                    print(f"Copiado: {exe}")
            
            # Adicionar ao PATH da sessão atual
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
            
            # Tentar adicionar permanentemente ao PATH do usuário
            try:
                self._add_to_windows_path(ffmpeg_dir)
            except Exception as e:
                print(f"AVISO: Não foi possível adicionar ao PATH permanente: {e}")
                print("FFmpeg funcionará apenas nesta sessão")
            
            print(f"FFmpeg instalado em: {ffmpeg_dir}")
            return True
            
        except Exception as e:
            print(f"Erro ao instalar FFmpeg: {e}")
            return False
        finally:
            # Limpar
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    def _add_to_windows_path(self, path):
        """Adiciona diretório ao PATH do usuário no Windows"""
        # Abrir registro
        reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(reg, r'Environment', 0, winreg.KEY_ALL_ACCESS)
        
        try:
            # Ler PATH atual
            current_path, _ = winreg.QueryValueEx(key, 'Path')
        except FileNotFoundError:
            current_path = ''
        
        # Adicionar se não estiver
        if path not in current_path:
            new_path = current_path + ';' + path if current_path else path
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
        
        winreg.CloseKey(key)
        winreg.CloseKey(reg)
        
    def _install_linux(self):
        """Instala FFmpeg no Linux"""
        try:
            # Tenta apt (Debian/Ubuntu)
            subprocess.run(['sudo', 'apt-get', 'update'], 
                         check=True, capture_output=True, timeout=60)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'],
                         check=True, capture_output=True, timeout=60)
            return True
        except subprocess.CalledProcessError:
            try:
                # Tenta yum (RHEL/CentOS)
                subprocess.run(['sudo', 'yum', 'install', '-y', 'ffmpeg'],
                             check=True, capture_output=True, timeout=60)
                return True
            except subprocess.CalledProcessError:
                print("Instalação automática falhou. Instale manualmente:")
                print("  Debian/Ubuntu: sudo apt install ffmpeg")
                print("  RHEL/CentOS: sudo yum install ffmpeg")
                return False
    
    def _install_macos(self):
        """Instala FFmpeg no macOS"""
        try:
            # Tenta Homebrew
            subprocess.run(['brew', 'install', 'ffmpeg'],
                         check=True, capture_output=True, timeout=300)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Instalação automática falhou. Instale manualmente:")
            print("  brew install ffmpeg")
            return False