import os
import json
import platform
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """Gerenciador de configurações"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Evitar múltiplas inicializações
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.config_file = None
        self.config = {}
        self._default_config = self._get_default_config()

    def initialize(self, config_file: str = None):
        """Inicializa com arquivo de configuração"""
        if config_file is None:
            if platform.system() == "Windows":
                app_data = os.environ.get("APPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Roaming"))
                config_dir = os.path.join(app_data, 'AmareloSubs')
            elif platform.system() == "Darwin":
                config_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "AmareloSubs")
            else:
                config_dir = os.path.join(os.path.expanduser("~"), '.amarelo_subs')
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, 'config.json')
        
        self.config_file = config_file
        self.load()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Retorna configuração padrão do Amarelo Subs"""
        return {
            'app_name': 'Amarelo Subs',  # Nome fixo da marca
            'version': '1.0.0',
            'general': {
                'output_dir': 'output',
                'language': 'pt_BR',
                'theme': 'dark'
            },
            'transcription': {
                'model': 'base',
                'device': 'auto',
                'language': 'auto'
            },
            'translation': {
                'enabled': False,
                'target_language': 'pt',
                'provider': 'google'
            },
            'font': {
                'name': 'Arial',
                'size': 20,
                'color': '#FFFF00', # Sugestão: Amarelo para combinar com a marca!
                'bold': False,
                'format_type': 'ass'
            }
        }
        
    def load(self):
        """Carrega configurações do arquivo"""
        try:
            if self.config_file and os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"Configurações carregadas de {self.config_file}")
            else:
                self.config = self._default_config.copy()
                logger.info("Usando configurações padrão")
                
            # Garantir que todas as chaves padrão existam
            self._merge_configs(self.config, self._default_config)
            
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            self.config = self._default_config.copy()
    
    def _merge_configs(self, target: Dict, source: Dict):
        """Mescla configurações recursivamente"""
        for key, value in source.items():
            if key not in target:
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                self._merge_configs(target[key], value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração"""
        keys = key.split('.')
        config = self.config
        
        for k in keys:
            if isinstance(config, dict) and k in config:
                config = config[k]
            else:
                return default
        
        return config
    
    def set(self, key: str, value: Any):
        """Define valor de configuração"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save()
    
    def save(self):
        """Salva configurações no arquivo"""
        try:
            if self.config_file:
                config_dir = os.path.dirname(self.config_file)
                os.makedirs(config_dir, exist_ok=True)
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Configurações salvas em {self.config_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
    
    def get_font_config(self) -> Dict[str, Any]:
        """Obtém configurações de fonte"""
        return self.config.get('font', {})

# Instância global (não inicializada automaticamente)
config_manager = ConfigManager()