class SubtitleGenerator:
    def __init__(self, config_manager=None):
        self.config = config_manager

    def format_timestamp(self, seconds):
        """Converte segundos para o formato SRT: HH:MM:SS,mmm"""
        td_hours = int(seconds // 3600)
        td_mins = int((seconds % 3600) // 60)
        td_secs = int(seconds % 60)
        td_msecs = int((seconds - int(seconds)) * 1000)
        return f"{td_hours:02d}:{td_mins:02d}:{td_secs:02d},{td_msecs:03d}"

    def _hex_to_ass_color(self, hex_color):
        """Converte cor hexadecimal para formato ASS (&HBBGGRR&)"""
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f"&H{b:02X}{g:02X}{r:02X}&"

    def generate_ass(self, segments, output_path):
        """Gera o arquivo .ass com formatação ASS/SSA"""
        color = self.config.get("font.color", "#f4c430")
        is_bold = self.config.get("font.bold", True)
        size_map = {"Pequeno": "12", "Médio": "18", "Grande": "24"}
        size_label = self.config.get("font.size_label", "Médio")
        fontsize = size_map.get(size_label, "18")
        ass_color = self._hex_to_ass_color(color)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 384\n")
            f.write("PlayResY: 288\n")
            f.write("\n")
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, Bold, Outline, Shadow, Alignment, MarginV\n")
            style = f"Default,Arial,{fontsize},{ass_color},{1 if is_bold else 0},1,1,2,30\n"
            f.write(f"Style: {style}\n")
            f.write("\n")
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Text\n")
            for segment in segments:
                start = self._format_timestamp_ass(segment['start'])
                end = self._format_timestamp_ass(segment['end'])
                text = segment['text'].strip().replace("\n", "\\N")
                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

    def _format_timestamp_ass(self, seconds):
        """Converte segundos para o formato ASS: H:MM:SS.cc"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def generate(self, segments, output_path):
        """Gera o arquivo .srt aplicando cor, negrito e tamanho"""
        output_ass = output_path.replace(".srt", ".ass")
        self.generate_ass(segments, output_ass)
        return True