#!/usr/bin/env python3
"""
core/unified/phone_analyzer.py
==============================
Analyzes simulated (or real) phone extractions for relationship dynamics,
sentiment patterns, coercion markers, and emotional affair indicators.

ELI5: This is like a forensic electrician who reads the load patterns
      on every circuit. They can tell which outlets are overheating,
      which wires are frayed, and where the power is being diverted
      — all without touching a single breaker.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SentimentScore:
    """ELI5: One meter reading — how hot or cold a wire is running."""

    positive: float = 0.0
    negative: float = 0.0
    neutral: float = 0.0
    dominant: str = "neutral"


@dataclass
class ThreadAnalysis:
    """ELI5: The complete inspection report for one circuit."""

    thread_id: str
    participants: List[str]
    message_count: int
    sentiment: SentimentScore
    red_flags: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    power_imbalance: Optional[str] = None
    intimacy_score: float = 0.0  # 0-1, higher = more emotional intimacy
    control_score: float = 0.0  # 0-1, higher = controlling/abusive patterns


@dataclass
class PhoneExtractionReport:
    """ELI5: The building-wide electrical audit after testing every floor."""

    device_owner: str
    total_messages: int
    total_calls: int
    total_media: int
    contact_count: int
    thread_analyses: List[ThreadAnalysis]
    relationship_map: Dict[str, List[str]]
    overall_assessment: str = ""
    risk_level: str = "low"  # low | moderate | high | critical


class PhoneAnalyzer:
    """
    ELI5: The master diagnostic tool for reading human connection patterns.
          It doesn't judge — it just measures voltage, current, and resistance
          between every pair of wires.
    """

    # Simple lexicon for sentiment — no cloud APIs needed
    POSITIVE_WORDS = {
        "love", "happy", "laugh", "kind", "care", "support", "safe", "warm",
        "bright", "better", "good", "great", "wonderful", "beautiful",
        "thank", "thanks", "appreciate", "miss", "missed", "hug", "kiss",
        "amazing", "perfect", "comfort", "hold", "together", "home",
        "smile", "joy", "excited", "hope", "trust", "honest", "open",
    }
    NEGATIVE_WORDS = {
        "hate", "angry", "cruel", "hurt", "pain", "cry", "crying", "tears",
        "break", "broken", "damage", "destroy", "regret", "guilty", "guilt",
        "fear", "afraid", "scared", "terrified", "abuse", "abusive",
        "prisoner", "trap", "trapped", "suffocate", "breathe", "exhausted",
        "tired", "drain", "empty", "lonely", "alone", "abandon", "leave",
        "liar", "lie", "cheat", "betray", "knife", "weapon", "destroy",
        "burn", "kill", "die", "dead", "worthless", "useless", "burden",
        "selfish", "terrible", "awful", "disgusting", "ugly", "fat",
        "stupid", "idiot", "moron", "pathetic", "loser", "failure",
    }
    RED_FLAG_PHRASES = [
        (r"nobody else wants", "isolation_tactic"),
        (r"you'll come back", "entrapment"),
        (r"you'll regret", "threat"),
        (r"everyone knows", "social_destruction_threat"),
        (r"i'll make sure", "retaliation_threat"),
        (r"you caused", "blame_shifting"),
        (r"your fault", "blame_shifting"),
        (r"walking on eggshells", "abuse_environment"),
        (r"can't leave", "entrapment"),
        (r"can't breathe", "suffocation"),
        (r"can't just", "guilt_trap"),
        (r"prisoner", "imprisonment_metaphor"),
        (r"terrorize", "abuse_acknowledgment"),
        (r"threw.*(plate|thing)", "property_destruction"),
        (r"through my (laptop|phone)", "privacy_violation"),
        (r"post.*instagram", "reputation_threat"),
        (r"post.*everyone", "reputation_threat"),
        (r"go through", "surveillance"),
        (r"watching.*camera", "surveillance"),
        (r"blocked.*apps", "control"),
        (r"demanding", "control"),
    ]
    INTIMACY_MARKERS = [
        "love you", "miss you", "think about you", "dream", "want you",
        "need you", "can't stop", "feel this", "feelings", "closer",
        "vulnerable", "open up", "secret", "only you", "nobody else",
        "understands", "sees me", "knows me", "complete", "whole",
        "touch", "hold", "kiss", "heart", "soul", "yours", "mine",
    ]

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir or Path("data/phone_simulator")

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------

    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = self.data_dir / filename
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_contacts(self) -> List[Dict[str, Any]]:
        return self._load_json("contacts.json").get("contacts", [])

    def load_threads(self) -> Dict[str, Dict[str, Any]]:
        threads_dir = self.data_dir / "threads"
        result = {}
        for f in sorted(threads_dir.glob("*.json")):
            with open(f, "r", encoding="utf-8") as fp:
                result[f.stem] = json.load(fp)
        return result

    def load_calls(self) -> List[Dict[str, Any]]:
        return self._load_json("call_logs.json").get("calls", [])

    def load_media(self) -> List[Dict[str, Any]]:
        return self._load_json("media.json").get("media", [])

    def load_locations(self) -> List[Dict[str, Any]]:
        return self._load_json("locations.json").get("locations", [])

    # ------------------------------------------------------------------
    # Analysis Engines
    # ------------------------------------------------------------------

    def _sentiment(self, text: str) -> Tuple[float, float, float]:
        """
        ELI5: Hold a thermal camera up to a wire and measure if it's
              running hot (positive), cold (negative), or ambient (neutral).
        """
        words = set(re.findall(r"[a-z']+", text.lower()))
        pos = len(words & self.POSITIVE_WORDS)
        neg = len(words & self.NEGATIVE_WORDS)
        total = max(1, len(words))
        neutral = total - pos - neg
        return pos / total, neg / total, neutral / total

    def _detect_red_flags(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        ELI5: Scan every wire for exposed copper, frayed insulation,
              and crossed circuits that could cause a fire.
        """
        flags: List[str] = []
        seen = set()
        for m in messages:
            text = m.get("text", "").lower()
            for pattern, flag_type in self.RED_FLAG_PHRASES:
                if re.search(pattern, text) and flag_type not in seen:
                    flags.append(f"[{flag_type}] {m['sender']}: '{text[:60]}...'")
                    seen.add(flag_type)
        return flags

    def _intimacy_score(self, messages: List[Dict[str, Any]]) -> float:
        """
        ELI5: Measure how much current is flowing between two wires.
              High current = strong connection. Low current = just a trickle.
        """
        intimacy_hits = 0
        for m in messages:
            text = m.get("text", "").lower()
            for marker in self.INTIMACY_MARKERS:
                if marker in text:
                    intimacy_hits += 1
        return min(1.0, intimacy_hits / max(1, len(messages) * 0.15))

    def _control_score(self, messages: List[Dict[str, Any]]) -> float:
        """
        ELI5: Check if one breaker is constantly tripping the others
              and forcing all the load onto itself.
        """
        control_hits = 0
        for m in messages:
            text = m.get("text", "").lower()
            # Control language patterns
            if any(w in text for w in ["can't", "won't let", "forbid", "not allowed", "block"]):
                control_hits += 1
            if any(w in text for w in ["demand", "expect", "owe", "promised", "duty"]):
                control_hits += 1
            if m.get("read") is False:
                control_hits += 0.5  # unread = deliberate ignoring
        return min(1.0, control_hits / max(1, len(messages) * 0.2))

    def _power_imbalance(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        ELI5: Check if one room is getting all the power while the other
              rooms are left in the dark.
        """
        sender_counts: Dict[str, int] = {}
        sender_lengths: Dict[str, int] = {}
        for m in messages:
            s = m["sender"]
            sender_counts[s] = sender_counts.get(s, 0) + 1
            sender_lengths[s] = sender_lengths.get(s, 0) + len(m.get("text", ""))

        if len(sender_counts) < 2:
            return None

        max_sender = max(sender_counts, key=lambda k: sender_counts[k])
        min_sender = min(sender_counts, key=lambda k: sender_counts[k])
        ratio = sender_counts[max_sender] / max(1, sender_counts[min_sender])

        if ratio > 3:
            return f"{max_sender} dominates conversation ({ratio:.1f}x more messages)"
        if sender_lengths.get(min_sender, 0) < sender_lengths.get(max_sender, 0) * 0.3:
            return f"{min_sender} communicates minimally ({min_sender} may be withdrawn or controlled)"
        return None

    def analyze_thread(self, thread_id: str, thread_data: Dict[str, Any]) -> ThreadAnalysis:
        """
        ELI5: Run the full diagnostic suite on one circuit and print
              the complete work order.
        """
        messages = thread_data.get("messages", [])
        pos, neg, neu = 0.0, 0.0, 0.0
        for m in messages:
            p, n, nt = self._sentiment(m.get("text", ""))
            pos += p
            neg += n
            neu += nt

        total = max(1, len(messages))
        sentiment = SentimentScore(
            positive=round(pos / total, 3),
            negative=round(neg / total, 3),
            neutral=round(neu / total, 3),
        )
        sentiment.dominant = max([("positive", sentiment.positive), ("negative", sentiment.negative), ("neutral", sentiment.neutral)], key=lambda x: x[1])[0]

        red_flags = self._detect_red_flags(messages)
        intimacy = self._intimacy_score(messages)
        control = self._control_score(messages)
        imbalance = self._power_imbalance(messages)

        return ThreadAnalysis(
            thread_id=thread_id,
            participants=thread_data.get("participants", []),
            message_count=len(messages),
            sentiment=sentiment,
            red_flags=red_flags,
            key_phrases=self._extract_key_phrases(messages),
            power_imbalance=imbalance,
            intimacy_score=round(intimacy, 3),
            control_score=round(control, 3),
        )

    def _extract_key_phrases(self, messages: List[Dict[str, Any]]) -> List[str]:
        """ELI5: Highlight the most important wire labels in the whole panel."""
        phrases = []
        for m in messages:
            text = m.get("text", "")
            if any(marker in text.lower() for marker in ["i love you", "i'm leaving", "i'm done", "i'm sorry", "i know", "i can't"]):
                phrases.append(f"[{m['sender']}] {text[:70]}{'...' if len(text) > 70 else ''}")
        # Deduplicate while preserving order
        seen = set()
        result = []
        for p in phrases:
            key = p[:40]
            if key not in seen:
                seen.add(key)
                result.append(p)
        return result[:10]

    def analyze_extraction(self) -> PhoneExtractionReport:
        """
        ELI5: The grand opening of the building — test every floor,
              every outlet, every breaker, and compile the master report.
        """
        contacts = self.load_contacts()
        threads = self.load_threads()
        calls = self.load_calls()
        media = self.load_media()

        thread_analyses = []
        total_messages = 0
        relationship_map: Dict[str, List[str]] = {}

        for tid, tdata in threads.items():
            analysis = self.analyze_thread(tid, tdata)
            thread_analyses.append(analysis)
            total_messages += analysis.message_count
            for p in analysis.participants:
                relationship_map.setdefault(p, []).append(tid)

        # Determine overall risk
        total_flags = sum(len(t.red_flags) for t in thread_analyses)
        max_control = max((t.control_score for t in thread_analyses), default=0)
        max_intimacy = max((t.intimacy_score for t in thread_analyses), default=0)

        risk = "low"
        if total_flags >= 8 or max_control >= 0.6:
            risk = "critical"
        elif total_flags >= 5 or max_control >= 0.4:
            risk = "high"
        elif total_flags >= 2 or max_control >= 0.2:
            risk = "moderate"

        assessment = self._generate_assessment(thread_analyses, risk, max_intimacy)

        return PhoneExtractionReport(
            device_owner="Sarah Reynolds",
            total_messages=total_messages,
            total_calls=len(calls),
            total_media=len(media),
            contact_count=len(contacts),
            thread_analyses=thread_analyses,
            relationship_map=relationship_map,
            overall_assessment=assessment,
            risk_level=risk,
        )

    def _generate_assessment(self, analyses: List[ThreadAnalysis], risk: str, max_intimacy: float) -> str:
        """ELI5: Write the executive summary on the front page of the audit."""
        lines = []

        # Find the most intimate thread
        intimate_threads = [a for a in analyses if a.intimacy_score > 0.3]
        controlling_threads = [a for a in analyses if a.control_score > 0.2]
        flagged_threads = [a for a in analyses if len(a.red_flags) >= 2]

        lines.append(f"OVERALL RISK LEVEL: {risk.upper()}")
        lines.append("")

        if intimate_threads:
            lines.append("EMOTIONAL AFFAIR INDICATORS DETECTED:")
            for t in intimate_threads:
                lines.append(f"  • Thread '{t.thread_id}': intimacy_score={t.intimacy_score} ({', '.join(t.participants)})")
            lines.append("")

        if controlling_threads:
            lines.append("CONTROLLING/ABUSIVE DYNAMICS DETECTED:")
            for t in controlling_threads:
                lines.append(f"  • Thread '{t.thread_id}': control_score={t.control_score}")
                for flag in t.red_flags[:3]:
                    lines.append(f"    - {flag}")
            lines.append("")

        if flagged_threads:
            lines.append(f"RED FLAGS ACROSS {len(flagged_threads)} THREAD(S):")
            for t in flagged_threads:
                lines.append(f"  • {t.thread_id}: {len(t.red_flags)} flag(s)")
            lines.append("")

        lines.append("POWER DYNAMICS:")
        for t in analyses:
            if t.power_imbalance:
                lines.append(f"  • {t.thread_id}: {t.power_imbalance}")

        return "\n".join(lines)

    def print_report(self, report: PhoneExtractionReport) -> None:
        """ELI5: Print the full audit to the terminal so the superintendent can read it."""
        print("=" * 70)
        print(f"PHONE EXTRACTION ANALYSIS REPORT")
        print(f"Device Owner: {report.device_owner}")
        print(f"Risk Level:   {report.risk_level.upper()}")
        print("=" * 70)
        print(f"\nSUMMARY:")
        print(f"  Contacts:      {report.contact_count}")
        print(f"  Messages:      {report.total_messages}")
        print(f"  Calls:         {report.total_calls}")
        print(f"  Media:         {report.total_media}")
        print(f"\n{report.overall_assessment}")

        print("\n" + "-" * 70)
        print("THREAD-BY-THREAD BREAKDOWN:")
        print("-" * 70)
        for t in report.thread_analyses:
            print(f"\n[THREAD] {t.thread_id}")
            print(f"   Participants: {', '.join(t.participants)}")
            print(f"   Messages:     {t.message_count}")
            print(f"   Sentiment:    {t.sentiment.dominant} (pos={t.sentiment.positive}, neg={t.sentiment.negative})")
            print(f"   Intimacy:     {t.intimacy_score}")
            print(f"   Control:      {t.control_score}")
            if t.power_imbalance:
                print(f"   Imbalance:    {t.power_imbalance}")
            if t.red_flags:
                print(f"   [!] Red Flags ({len(t.red_flags)}):")
                for flag in t.red_flags:
                    print(f"      - {flag}")
            if t.key_phrases:
                print(f"   [KEY] Key Phrases:")
                for phrase in t.key_phrases:
                    print(f"      - {phrase}")

        print("\n" + "=" * 70)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    analyzer = PhoneAnalyzer()
    report = analyzer.analyze_extraction()
    analyzer.print_report(report)


if __name__ == "__main__":
    main()
