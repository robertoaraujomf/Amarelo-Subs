import os
from src.core.translation_engine import TranslationEngine


class SubtitleTranslator:
    """Traduz arquivos de legenda existentes (SRT/ASS)"""

    def __init__(self, config_manager=None):
        self.config = config_manager
        self.translator = TranslationEngine(config_manager)

    def _parse_timestamp(self, time_str, is_ass=False):
        """Converte string de timestamp para segundos"""
        if is_ass:
            parts = time_str.strip().split(":")
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        else:
            parts = time_str.replace(",", ".").split(":")
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

    def _format_srt_time(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _format_ass_time(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def translate(self, subtitle_path, output_path=None, progress_callback=None):
        """Traduz um arquivo de legenda existente"""
        if progress_callback:
            progress_callback(0)

        is_ass = subtitle_path.endswith(".ass")
        target_lang = self.config.get("translation.target_language", "pt")

        with open(subtitle_path, "r", encoding="utf-8") as f:
            content = f.read()

        if progress_callback:
            progress_callback(10)

        segments = []
        if is_ass:
            lines = content.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith("Dialogue:"):
                    parts = line.split(",", 4)
                    if len(parts) >= 5:
                        start = self._parse_timestamp(parts[1], is_ass=True)
                        end = self._parse_timestamp(parts[2], is_ass=True)
                        text = parts[4].replace("\\N", "\n").replace("\\n", "\n")
                        segments.append({"start": start, "end": end, "text": text})
                i += 1
        else:
            lines = content.split("\n")
            i = 0
            while i < len(lines):
                if lines[i].strip().isdigit():
                    timing = lines[i + 1]
                    start_str, end_str = timing.split("-->")
                    start = self._parse_timestamp(start_str.strip())
                    end = self._parse_timestamp(end_str.strip().split(",")[0])
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
            progress_callback(30)

        translated = self.translator.translate_segments(
            segments, target_lang,
            progress_callback=lambda p: progress_callback(30 + int(p * 60)) if progress_callback else None
        )

        if progress_callback:
            progress_callback(95)

        if output_path is None:
            output_path = subtitle_path

        if is_ass:
            self._write_ass(translated, output_path)
        else:
            self._write_srt(translated, output_path)

        if progress_callback:
            progress_callback(100)
        return True

    def _write_srt(self, segments, output_path):
        with open(output_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                f.write(f"{i}\n")
                f.write(f"{self._format_srt_time(seg['start'])} --> {self._format_srt_time(seg['end'])}\n")
                f.write(f"{seg['text'].strip()}\n\n")

    def _write_ass(self, segments, output_path):
        color = self.config.get("font.color", "#f4c430")
        is_bold = self.config.get("font.bold", True)
        size_map = {"Pequeno": "12", "Médio": "18", "Grande": "24"}
        size_label = self.config.get("font.size_label", "Médio")
        fontsize = size_map.get(size_label, "18")

        hex_color = color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        ass_color = f"&H{b:02X}{g:02X}{r:02X}&"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 384\nPlayResY: 288\n\n")
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, Bold, Outline, Shadow, Alignment, MarginV\n")
            f.write(f"Style: Default,Arial,{fontsize},{ass_color},{1 if is_bold else 0},1,1,2,30\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Text\n")
            for seg in segments:
                start = self._format_ass_time(seg['start'])
                end = self._format_ass_time(seg['end'])
                text = seg['text'].strip().replace("\n", "\\N")
                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")
