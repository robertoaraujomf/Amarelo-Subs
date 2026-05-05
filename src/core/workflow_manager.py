import os
from PyQt6.QtCore import QThread, pyqtSignal
from src.core.transcription_engine import TranscriptionEngine
from src.core.translation_engine import TranslationEngine
from src.core.subtitle_generator import SubtitleGenerator
from src.core.video_merger import VideoMerger

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
        self.video_merger = VideoMerger(self.config)

    def set_directory(self, directory):
        self.directory = directory

    def run(self):
        try:
            extensions = ('.mp4', '.mkv', '.avi', '.mov')
            videos = [f for f in os.listdir(self.directory) if f.lower().endswith(extensions)]
            
            if not videos:
                self.finished.emit(False, "Nenhum vídeo encontrado.")
                return

            total_videos = len(videos)
            self.progress_general.emit(0)
            self.progress_individual.emit(0)

            for index, video in enumerate(videos):
                video_path = os.path.join(self.directory, video)
                self.preview_update.emit(f"<b>🎬 Processando ({index+1}/{total_videos}):</b> {video}")
                
                base_geral = int((index / total_videos) * 100)
                porcao_video = 100 / total_videos

                def update_sync_progress(p_ind):
                    self.progress_individual.emit(p_ind)
                    # Sincronização em tempo real da barra geral
                    p_geral = int(base_geral + (p_ind * porcao_video / 100))
                    self.progress_general.emit(p_geral)

                # 1. Transcrição (0-40%)
                def trans_cb(p):
                    update_sync_progress(int(p * 0.4))

                result = self.transcriber.transcribe(video_path, progress_callback=trans_cb)
                segments = result['segments']

                # 2. Tradução (40-55%)
                is_enabled = self.config.get("translation.enabled", False)
                target_lang = self.config.get("translation.target_language", "pt")
                
                if is_enabled:
                    def trad_cb(p):
                        update_sync_progress(40 + int(p * 0.15))
                    segments = self.translator.translate_segments(segments, target_lang, progress_callback=trad_cb)
                else:
                    update_sync_progress(55)

                # 3. Gerar Arquivo SRT
                srt_path = os.path.join(self.directory, os.path.splitext(video)[0] + ".srt")
                self.subtitle_gen.generate(segments, srt_path)
                self.preview_update.emit(f"   <b>Legenda gerada:</b> {os.path.basename(srt_path)}")
                update_sync_progress(60)

                # 4. Mesclar legenda no vdeo (hardcode) (60-100%)
                merge_enabled = self.config.get("video.merge_subtitles", True)
                if merge_enabled:
                    self.preview_update.emit(f"   <b>Mesclando legenda no vdeo...</b>")
                    base_name = os.path.splitext(video)[0]
                    ext = self.config.get("video.output_format", "mp4")
                    output_video = os.path.join(self.directory, f"{base_name}_legendado.{ext}")

                    def merge_cb(p):
                        update_sync_progress(60 + int(p * 0.4))

                    success = self.video_merger.merge(
                        video_path, srt_path, output_video, progress_callback=merge_cb
                    )
                    if success:
                        self.preview_update.emit(f"   <b>Vdeo com legenda:</b> {os.path.basename(output_video)}")
                    else:
                        self.preview_update.emit(f"   <b>AVISO:</b> Falha ao mesclar legenda no vdeo.")
                
            self.progress_general.emit(100)
            self.finished.emit(True, "Sucesso")
        except Exception as e:
            self.finished.emit(False, str(e))