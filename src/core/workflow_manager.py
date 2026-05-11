import os
from PyQt6.QtCore import QThread, pyqtSignal
from src.core.transcription_engine import TranscriptionEngine
from src.core.translation_engine import TranslationEngine
from src.core.subtitle_generator import SubtitleGenerator
from src.core.subtitle_syncer import SubtitleSyncer
from src.core.subtitle_translator import SubtitleTranslator
from src.core.video_merger import VideoMerger

MODE_FULL = 0
MODE_TRANSCRIBE_ONLY = 1
MODE_TRANSLATE_ONLY = 2
MODE_FORMAT_ONLY = 3
MODE_SYNC_ONLY = 4
MODE_MERGE_ONLY = 5


class WorkflowManager(QThread):
    progress_individual = pyqtSignal(int)
    progress_general = pyqtSignal(int)
    preview_update = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.directory = ""
        self.transcriber = TranscriptionEngine(self.config)
        self.translator = TranslationEngine(self.config)
        self.subtitle_gen = SubtitleGenerator(self.config)
        self.subtitle_syncer = SubtitleSyncer(self.config)
        self.subtitle_translator = SubtitleTranslator(self.config)
        self.video_merger = VideoMerger(self.config)

    def set_directory(self, directory):
        self.directory = directory

    def _get_files(self, mode):
        video_ext = ('.mp4', '.mkv', '.avi', '.mov')
        sub_ext = ('.srt', '.ass')
        
        videos = [f for f in os.listdir(self.directory) if f.lower().endswith(video_ext)]
        subtitles = [f for f in os.listdir(self.directory) if f.lower().endswith(sub_ext)]
        
        if mode in [MODE_FULL, MODE_TRANSCRIBE_ONLY]:
            return {"videos": videos, "subtitles": []}
        elif mode in [MODE_MERGE_ONLY]:
            pairs = []
            for video in videos:
                base = os.path.splitext(video)[0]
                for ext in sub_ext:
                    sub_file = base + ext
                    if sub_file in subtitles:
                        pairs.append({"video": video, "subtitle": sub_file})
                        break
            return {"pairs": pairs}
        else:
            return {"subtitles": subtitles}

    def _format_subtitle(self, sub_path, progress_callback=None):
        """Formata uma legenda existente (gera versão .ass estilizada)"""
        if progress_callback:
            progress_callback(0)
        
        if sub_path.endswith(".ass"):
            if progress_callback:
                progress_callback(100)
            return True, sub_path
        
        srt_path = os.path.join(self.directory, sub_path)
        ass_path = srt_path.replace(".srt", ".ass")
        
        segments = []
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():
                timing = lines[i + 1]
                start_str, end_str = timing.split("-->")
                start = self._parse_srt_time(start_str.strip())
                end = self._parse_srt_time(end_str.strip().split(",")[0])
                i += 2
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i])
                    i += 1
                text = "\n".join(text_lines)
                segments.append({"start": start, "end": end, "text": text})
            else:
                i += 1
        
        if progress_callback:
            progress_callback(50)
        
        self.subtitle_gen.generate_ass(segments, ass_path)
        
        if progress_callback:
            progress_callback(100)
        return True, ass_path

    def _parse_srt_time(self, time_str):
        parts = time_str.replace(",", ".").split(":")
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

    def _translate_subtitle(self, sub_path, progress_callback=None):
        """Traduz uma legenda existente"""
        sub_full = os.path.join(self.directory, sub_path)
        output = sub_full.replace(".srt", "_translated.srt").replace(".ass", "_translated.ass")
        self.subtitle_translator.translate(sub_full, output, progress_callback)
        return True, output

    def _sync_subtitle(self, sub_path, video_name, progress_callback=None):
        """Sincroniza legenda com vídeo"""
        sub_full = os.path.join(self.directory, sub_path)
        video_full = os.path.join(self.directory, video_name)
        output = sub_full.replace(".srt", "_sync.srt").replace(".ass", "_sync.ass")
        self.subtitle_syncer.sync(sub_full, video_full, output, progress_callback)
        return True, output

    def run(self):
        try:
            mode = self.config.get("operation.mode", MODE_FULL)
            files = self._get_files(mode)
            
            total = 0
            if mode == MODE_FULL:
                total = len(files.get("videos", []))
            elif mode == MODE_TRANSCRIBE_ONLY:
                total = len(files.get("videos", []))
            elif mode == MODE_TRANSLATE_ONLY:
                total = len(files.get("subtitles", []))
            elif mode == MODE_FORMAT_ONLY:
                total = len(files.get("subtitles", []))
            elif mode == MODE_SYNC_ONLY:
                total = len(files.get("subtitles", []))
            elif mode == MODE_MERGE_ONLY:
                total = len(files.get("pairs", []))
            
            if total == 0:
                self.finished.emit(False, "Nenhum arquivo para processar.")
                return
            
            self.progress_general.emit(0)
            self.progress_individual.emit(0)
            processed = 0

            if mode == MODE_FULL:
                for video in files.get("videos", []):
                    video_path = os.path.join(self.directory, video)
                    self.preview_update.emit(f"<b>🎬 Processando ({processed+1}/{total}):</b> {video}")
                    
                    def trans_cb(p):
                        self.progress_individual.emit(int(p * 0.4))
                        self.progress_general.emit(int(((processed + p * 0.4) / total) * 100))
                    
                    result = self.transcriber.transcribe(video_path, progress_callback=trans_cb)
                    segments = result['segments']
                    
                    is_enabled = self.config.get("translation.enabled", False)
                    target_lang = self.config.get("translation.target_language", "pt")
                    
                    if is_enabled:
                        def trad_cb(p):
                            self.progress_individual.emit(40 + int(p * 0.15))
                            self.progress_general.emit(int(((processed + 0.4 + p * 0.15) / total) * 100))
                        segments = self.translator.translate_segments(segments, target_lang, progress_callback=trad_cb)
                    else:
                        self.progress_individual.emit(55)
                    
                    srt_path = os.path.join(self.directory, os.path.splitext(video)[0] + ".srt")
                    self.subtitle_gen.generate(segments, srt_path)
                    self.preview_update.emit(f"   <b>Legenda gerada:</b> {os.path.basename(srt_path)}")
                    self.progress_individual.emit(60)
                    
                    ass_path = srt_path.replace(".srt", ".ass")
                    base_name = os.path.splitext(video)[0]
                    ext = self.config.get("video.output_format", "mp4")
                    output_video = os.path.join(self.directory, f"{base_name}_legendado.{ext}")
                    
                    def merge_cb(p):
                        pct = 60 + int(p * 0.4)
                        self.progress_individual.emit(pct)
                        self.progress_general.emit(int(((processed + pct / 100) / total) * 100))
                    
                    success = self.video_merger.merge(video_path, srt_path, output_video, progress_callback=merge_cb)
                    if success:
                        self.preview_update.emit(f"   <b>Vídeo com legenda:</b> {os.path.basename(output_video)}")
                    else:
                        self.preview_update.emit(f"   <b>AVISO:</b> Falha ao mesclar legenda.")
                    
                    processed += 1
                    self.progress_individual.emit(100)
            
            elif mode == MODE_TRANSCRIBE_ONLY:
                for video in files.get("videos", []):
                    video_path = os.path.join(self.directory, video)
                    self.preview_update.emit(f"<b>🎬 Transcrevendo ({processed+1}/{total}):</b> {video}")
                    
                    def trans_cb(p):
                        self.progress_individual.emit(int(p * 100))
                        self.progress_general.emit(int(((processed + p) / total) * 100))
                    
                    result = self.transcriber.transcribe(video_path, progress_callback=trans_cb)
                    segments = result['segments']
                    
                    is_enabled = self.config.get("translation.enabled", False)
                    target_lang = self.config.get("translation.target_language", "pt")
                    
                    if is_enabled:
                        def trad_cb(p):
                            self.progress_individual.emit(50 + int(p * 50))
                            self.progress_general.emit(int(((processed + 0.5 + p * 0.5) / total) * 100))
                        segments = self.translator.translate_segments(segments, target_lang, progress_callback=trad_cb)
                    
                    srt_path = os.path.join(self.directory, os.path.splitext(video)[0] + ".srt")
                    self.subtitle_gen.generate(segments, srt_path)
                    self.preview_update.emit(f"   <b>Legenda gerada:</b> {os.path.basename(srt_path)}")
                    processed += 1
                    self.progress_individual.emit(100)
            
            elif mode == MODE_TRANSLATE_ONLY:
                for sub in files.get("subtitles", []):
                    self.preview_update.emit(f"<b>🌐 Traduzindo ({processed+1}/{total}):</b> {sub}")
                    
                    def progress_cb(p):
                        self.progress_individual.emit(p)
                        self.progress_general.emit(int(((processed + p / 100) / total) * 100))
                    
                    success, output = self._translate_subtitle(sub, progress_cb)
                    if success:
                        self.preview_update.emit(f"   <b>Legenda traduzida:</b> {os.path.basename(output)}")
                    processed += 1
                    self.progress_individual.emit(100)
            
            elif mode == MODE_FORMAT_ONLY:
                for sub in files.get("subtitles", []):
                    self.preview_update.emit(f"<b>🎨 Formatando ({processed+1}/{total}):</b> {sub}")
                    
                    def progress_cb(p):
                        self.progress_individual.emit(p)
                        self.progress_general.emit(int(((processed + p / 100) / total) * 100))
                    
                    success, output = self._format_subtitle(sub, progress_cb)
                    if success:
                        self.preview_update.emit(f"   <b>Legenda formatada:</b> {os.path.basename(output)}")
                    processed += 1
                    self.progress_individual.emit(100)
            
            elif mode == MODE_SYNC_ONLY:
                for sub in files.get("subtitles", []):
                    base = os.path.splitext(sub)[0]
                    video_name = base + ".mp4"
                    if video_name not in files.get("videos", []):
                        video_name = base + ".mkv"
                    if video_name not in files.get("videos", []):
                        video_name = base + ".avi"
                    if video_name not in files.get("videos", []):
                        video_name = base + ".mov"
                    if video_name not in files.get("videos", []):
                        self.preview_update.emit(f"   <b>AVISO:</b> Vídeo não encontrado para: {sub}")
                        continue
                    
                    self.preview_update.emit(f"<b>⏱ Sincronizando ({processed+1}/{total}):</b> {sub} com {video_name}")
                    
                    def progress_cb(p):
                        self.progress_individual.emit(p)
                        self.progress_general.emit(int(((processed + p / 100) / total) * 100))
                    
                    success, output = self._sync_subtitle(sub, video_name, progress_cb)
                    if success:
                        self.preview_update.emit(f"   <b>Legenda sincronizada:</b> {os.path.basename(output)}")
                    processed += 1
                    self.progress_individual.emit(100)
            
            elif mode == MODE_MERGE_ONLY:
                for pair in files.get("pairs", []):
                    video = pair["video"]
                    sub = pair["subtitle"]
                    video_path = os.path.join(self.directory, video)
                    sub_path = os.path.join(self.directory, sub)
                    
                    self.preview_update.emit(f"<b>🔗 Mesclando ({processed+1}/{total}):</b> {video} + {sub}")
                    
                    base_name = os.path.splitext(video)[0]
                    ext = self.config.get("video.output_format", "mp4")
                    output_video = os.path.join(self.directory, f"{base_name}_legendado.{ext}")
                    
                    def merge_cb(p):
                        self.progress_individual.emit(p)
                        self.progress_general.emit(int(((processed + p / 100) / total) * 100))
                    
                    success = self.video_merger.merge(video_path, sub_path, output_video, progress_callback=merge_cb)
                    if success:
                        self.preview_update.emit(f"   <b>Vídeo com legenda:</b> {os.path.basename(output_video)}")
                    else:
                        self.preview_update.emit(f"   <b>AVISO:</b> Falha ao mesclar.")
                    processed += 1
                    self.progress_individual.emit(100)
            
            self.progress_general.emit(100)
            self.finished.emit(True, "Sucesso")
        except Exception as e:
            self.finished.emit(False, str(e))