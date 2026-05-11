import os
import subprocess
import platform


class SubtitleSyncer:
    """Sincroniza legendas com a duração do vídeo usando FFmpeg"""

    def __init__(self, config_manager=None):
        self.config = config_manager

    def get_video_duration(self, video_path):
        """Retorna a duração do vídeo em segundos usando ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"Erro ao obter duração do vídeo: {e}")
            return None

    def get_subtitle_duration(self, srt_path):
        """Retorna a duração total das legendas (último timestamp final)"""
        if srt_path.endswith(".ass"):
            return self._get_ass_duration(srt_path)
        return self._get_srt_duration(srt_path)

    def _get_srt_duration(self, srt_path):
        """Extrai o último timestamp de fim de um SRT"""
        last_end = 0.0
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        for line in content.split("\n"):
            if "-->" in line:
                end_str = line.split("-->")[1].strip().split(",")[0]
                last_end = self._parse_srt_time(end_str)
        return last_end

    def _get_ass_duration(self, ass_path):
        """Extrai o último timestamp de fim de um ASS"""
        last_end = 0.0
        with open(ass_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Dialogue:"):
                    parts = line.split(",")
                    if len(parts) >= 4:
                        last_end = self._parse_ass_time(parts[3])
        return last_end

    def _parse_srt_time(self, time_str):
        """Converte HH:MM:SS,mmm para segundos"""
        parts = time_str.replace(",", ".").split(":")
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

    def _parse_ass_time(self, time_str):
        """Converte H:MM:SS.cc para segundos"""
        parts = time_str.strip().split(":")
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

    def sync(self, subtitle_path, video_path, output_path=None, progress_callback=None):
        """Ajusta os timestamps da legenda para coincidir com a duração do vídeo"""
        if progress_callback:
            progress_callback(10)

        video_duration = self.get_video_duration(video_path)
        if video_duration is None:
            print("Não foi possível obter duração do vídeo")
            return False

        if progress_callback:
            progress_callback(30)

        if subtitle_path.endswith(".ass"):
            return self._sync_ass(subtitle_path, video_duration, output_path, progress_callback)
        else:
            return self._sync_srt(subtitle_path, video_duration, output_path, progress_callback)

    def _sync_srt(self, srt_path, video_duration, output_path, progress_callback):
        """Sincroniza timestamps de um arquivo SRT"""
        sub_duration = self._get_srt_duration(srt_path)
        if sub_duration <= 0:
            print("Duração da legenda inválida")
            return False

        ratio = video_duration / sub_duration
        last_timestamp = 0.0
        cumulative_time = 0.0

        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        if progress_callback:
            progress_callback(60)

        lines = content.split("\n")
        result_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if "-->" in line:
                start_str, end_str = line.split("-->")
                start_str = start_str.strip()
                end_str = end_str.strip().split(",")[0].strip()

                old_start = self._parse_srt_time(start_str)
                old_end = self._parse_srt_time(end_str)

                new_start = old_start * ratio
                new_end = old_end * ratio

                last_timestamp = new_end
                cumulative_time = new_start - old_start

                result_lines.append(f"{self._format_srt_time(new_start)} --> {self._format_srt_time(new_end)}")
                i += 1
                while i < len(lines) and lines[i].strip():
                    result_lines.append(lines[i])
                    i += 1
            else:
                result_lines.append(line)
                i += 1

        if progress_callback:
            progress_callback(90)

        if output_path is None:
            output_path = srt_path

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(result_lines))

        if progress_callback:
            progress_callback(100)
        return True

    def _sync_ass(self, ass_path, video_duration, output_path, progress_callback):
        """Sincroniza timestamps de um arquivo ASS"""
        sub_duration = self._get_ass_duration(ass_path)
        if sub_duration <= 0:
            print("Duração da legenda inválida")
            return False

        ratio = video_duration / sub_duration

        with open(ass_path, "r", encoding="utf-8") as f:
            content = f.read()

        if progress_callback:
            progress_callback(60)

        lines = content.split("\n")
        result_lines = []
        for line in lines:
            if line.startswith("Dialogue:"):
                parts = line.split(",", 4)
                if len(parts) >= 4:
                    old_start = self._parse_ass_time(parts[1])
                    old_end = self._parse_ass_time(parts[2])
                    new_start = old_start * ratio
                    new_end = old_end * ratio
                    parts[1] = self._format_ass_time(new_start)
                    parts[2] = self._format_ass_time(new_end)
                    line = ",".join(parts)
            result_lines.append(line)

        if progress_callback:
            progress_callback(90)

        if output_path is None:
            output_path = ass_path

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(result_lines))

        if progress_callback:
            progress_callback(100)
        return True

    def _format_srt_time(self, seconds):
        """Converte segundos para o formato SRT: HH:MM:SS,mmm"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _format_ass_time(self, seconds):
        """Converte segundos para o formato ASS: H:MM:SS.cc"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
