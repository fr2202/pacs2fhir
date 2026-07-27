"""
RTF Parser Agent
Converts RTF-encoded clinical text to structured plain-text sections.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

try:
    from striprtf.striprtf import rtf_to_text
except ImportError:
    def rtf_to_text(rtf: str, errors: str = "ignore") -> str:  # type: ignore
        text = re.sub(r'\{[^{}]*\}', '', rtf)
        text = re.sub(r'\\[a-z]+\d*\s?', ' ', text)
        text = re.sub(r'[{}\\]', '', text)
        return re.sub(r'\s+', ' ', text).strip()


@dataclass
class ParsedRTF:
    raw_text: str = ""
    episode_id: Optional[str] = None
    exam_date: Optional[str] = None
    exam_time: Optional[str] = None
    cabinet: Optional[str] = None
    clinical_info: Optional[str] = None
    technical_protocol: Optional[str] = None
    report_text: Optional[str] = None
    radiologist: Optional[str] = None
    extra_sections: dict = field(default_factory=dict)


class RTFParserAgent:
    """Parses a single RTF string into a structured ParsedRTF object."""

    _EP_PATTERN = re.compile(r"Epis[oó]dio[:\s]+\S+\s+-\s+(\d+)", re.IGNORECASE)
    _DATE_PATTERN = re.compile(r"Data[:\s]+(\d{2}-\d{2}-\d{4})", re.IGNORECASE)
    _TIME_PATTERN = re.compile(r"Hora[:\s]+(\d{2}:\d{2})", re.IGNORECASE)
    _CABINET_PATTERN = re.compile(r"Gabinete[:\s]+(\w+)", re.IGNORECASE)
    _RADIOLOGIST_PATTERN = re.compile(
        r"(?:(?:[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇÀÈÌÒÙ][a-záéíóúâêîôûãõçàèìòù]+\s+){1,4})"
        r"\\F\\\s*"
        r"(?:[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇÀÈÌÒÙ][a-záéíóúâêîôûãõçàèìòù]+(?:\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇÀÈÌÒÙ]"
        r"[a-záéíóúâêîôûãõçàèìòù]+)*)"
    )

    # Headers must appear as standalone lines (start of line + colon) to avoid
    # matching the same words when they appear mid-sentence inside clinical text.
    _SECTION_HEADERS = {
        "clinical_info": re.compile(
            r"(?:^|\n)\s*Informa[cç][aã]o\s+cl[ií]nica\s*:\s*\n?", re.IGNORECASE
        ),
        "technical_protocol": re.compile(
            r"(?:^|\n)\s*Protocolo\s+t[eé]cnico\s*:\s*\n?", re.IGNORECASE
        ),
        "report_text": re.compile(
            r"(?:^|\n)\s*Relat[oó]rio\s*:\s*\n?", re.IGNORECASE
        ),
    }

    def parse(self, rtf_str: str) -> ParsedRTF:
        result = ParsedRTF()
        if not rtf_str:
            return result

        try:
            plain = rtf_to_text(rtf_str, errors="ignore")
        except Exception:
            plain = rtf_str
        result.raw_text = plain

        ep_m = self._EP_PATTERN.search(plain)
        if ep_m:
            result.episode_id = ep_m.group(1)

        date_m = self._DATE_PATTERN.search(plain)
        if date_m:
            result.exam_date = date_m.group(1)

        time_m = self._TIME_PATTERN.search(plain)
        if time_m:
            result.exam_time = time_m.group(1)

        cab_m = self._CABINET_PATTERN.search(plain)
        if cab_m:
            result.cabinet = cab_m.group(1)

        result.clinical_info = self._extract_section(plain, "clinical_info")
        result.technical_protocol = self._extract_section(plain, "technical_protocol")
        result.report_text = self._extract_section(plain, "report_text")

        # Fallback: if no section headers found but there is real content,
        # treat the whole text as report_text (older/cardiology reports skip headers).
        has_scheduling_only = bool(result.episode_id or result.exam_date)
        if not result.report_text and not result.clinical_info:
            stripped = plain.strip()
            # Ignore if it's only scheduling text (Agendamento block)
            if stripped and not has_scheduling_only:
                result.report_text = stripped
            elif stripped and len(stripped) > 150:
                # Long text even with scheduling info = contains real report content
                result.report_text = stripped

        rad_m = self._RADIOLOGIST_PATTERN.search(rtf_str)
        if rad_m:
            result.radiologist = re.sub(r"\\F\\", "/", rad_m.group(0)).strip()

        return result

    def _extract_section(self, text: str, section: str) -> Optional[str]:
        header_re = self._SECTION_HEADERS.get(section)
        if not header_re:
            return None
        m = header_re.search(text)
        if not m:
            return None
        start = m.end()
        next_header_pos = len(text)
        for other, other_re in self._SECTION_HEADERS.items():
            if other == section:
                continue
            om = other_re.search(text, start)
            if om and om.start() < next_header_pos:
                next_header_pos = om.start()
        content = text[start:next_header_pos].strip()
        return content if content else None
