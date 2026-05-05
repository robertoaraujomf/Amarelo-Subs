import os
import subprocess
import platform


class VideoMerger:
    """Mescla legendas em vdeos usando FFmpeg (hardcode/burn-in)"""

    def __init__(self, config_manager=None):
        self.config = config_manager

    def _escape_path(self, path):
        """Escapa caracteres especiais no caminho para o filter do FFmpeg."""
        path = path.replace("\\", "/")
        if platform.system() == "Windows":
            path = path.replace(":", r"\:")
        for ch in ["'", ":", "[", "]", ","]:
            path = path.replace(ch, f"\\{ch}")
        return path

    def merge(self, video_path, srt_path, output_path, progress_callback=None):
        """
        Queima (hardcode) as legendas do arquivo SRT no vdeo.
        Retorna True em caso de sucesso, False caso contrrio.
        """
        if progress_callback:
            progress_callback(0)

        color = self.config.get("font.color", "#f4c430")
        is_bold = self.config.get("font.bold", True)
        size_map = {"Pequeno": "12", "Mdio": "18", "Grande": "24"}
        size_label = self.config.get("font.size_label", "Mdio")
        fontsize = size_map.get(size_label, "18")

        bold_val = 1 if is_bold else 0
        escaped_srt = self._escape_path(srt_path)

        force_style = (
            f"FontName=Arial,FontSize={fontsize},"
            f"PrimaryColour=&H{color[1:]}&,Bold={bold_val},"
            f"Outline=1,Shadow=1,MarginV=30"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{escaped_srt}':force_style='{force_style}'",
            "-c:a", "copy",
            "-preset", "fast",
            "-movflags", "+faststart",
            output_path,
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
            )

            total_duration = None
            current_time = 0.0

            while True:
                line = process.stderr.readline()
                if not line:
                    break

                if total_duration is None:
                    dur_match = self._parse_duration_from_line(line, "Duration:")
                    if dur_match is not None:
                        total_duration = dur_match

                time_match = self._parse_duration_from_line(line, "time=")
                if time_match is not None:
                    current_time = time_match

                if total_duration and total_duration > 0 and progress_callback:
                    pct = int(min((current_time / total_duration) * 100, 100))
                    progress_callback(pct)

            process.wait()

            if process.returncode != 0:
                stderr_output = process.stderr.read() if process.stderr else ""
                print(f"FFmpeg error: {stderr_output}")
                return False

            if progress_callback:
                progress_callback(100)
            return True

        except FileNotFoundError:
            print("FFmpeg no encontrado. Instale FFmpeg para mesclar legendas.")
            return False
        except Exception as e:
            print(f"Erro ao mesclar vdeo: {e}")
            return False

    def _parse_duration_from_line(self, line, prefix):
        """Extrai duracao em segundos de uma linha de output do FFmpeg."""
        try:
            idx = line.find(prefix)
            if idx == -1:
                return None
            rest = line[idx + len(prefix):].strip()
            if prefix == "time=":
                time_str = rest.split()[0]
            else:
                time_str = rest.split(",")[0].strip()
            parts = time_str.split(":")
            if len(parts) == 3:
                h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
                return h * 3600 + m * 60 + s
        except (ValueError, IndexError):
            pass
        return None
