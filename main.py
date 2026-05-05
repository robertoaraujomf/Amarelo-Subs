import sys
import os
import traceback
import subprocess
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from src.gui.main_window import MainWindow
from src.utils.config_manager import ConfigManager

def exception_hook(exctype, value, tb):
    """Captura erros fatais e exibe em uma caixa de diálogo."""
    trcback = ''.join(traceback.format_exception(exctype, value, tb))
    print(trcback)
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setText("Ocorreu um erro inesperado:")
    msg.setInformativeText(str(value))
    msg.setDetailedText(trcback)
    msg.setWindowTitle("Erro Fatal")
    msg.exec()
    sys.exit(1)

def apply_windows_taskbar_fix():
    """Fix para o cone aparecer na barra de tarefas do Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = 'yellowsubs.v1.0.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

def main():
    # --- CONFIGURAÇÕES PRÉ-INSTÂNCIA (OBRIGATÓRIO SEREM AQUI) ---
    
    # 1. Ajuste de DPI - Define como o Qt lida com escalas (125%, 150%, etc)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    # 2. Política de Arredondamento - DEVE vir antes do QApplication
    # Isso evita que o Qt arredonde 125% para 100% ou 200%, mantendo a nitidez.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 3. Hook de exceções para capturar erros de inicialização
    sys.excepthook = exception_hook

    # 4. Fix do ícone da barra de tarefas
    apply_windows_taskbar_fix()

    # --- CRIAÇÃO DA INSTÂNCIA ---

    app = QApplication(sys.argv)
    app.setApplicationName("Amarelo Subs")

    # 5. Inicializar Configurações
    try:
        config = ConfigManager()
    except Exception as e:
        QMessageBox.critical(None, "Erro de Configuração", f"Falha ao carregar configurações: {e}")
        return

    # 6. Criar e Exibir a Janela Principal
    window = MainWindow(config)
    
    # Se a janela não foi mostrada pelo showMaximized no __init__, forçamos aqui
    if not window.isVisible():
        window.show()

    # 7. Execução do Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()