#!/usr/bin/env python3
"""
core/unified/orbitscribe_demo.py
==============================
OrbitScribe Relationship Engine — LLM-powered demo for testing
relationship reasoning, attachment-style detection, triangulation
analysis, and emotional trajectory mapping.

ELI5: Instead of just checking if a wire is hot or cold with a multimeter,
      we bring in a master electrician who can look at the whole building's
      wiring diagram and tell you WHY the circuits are behaving strangely,
      WHICH junction boxes are dangerously overloaded, and WHERE the power
      is being secretly diverted.
"""

from __future__ import annotations

import json
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("simplepod.unified.orbitscribe")

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ReasoningChain:
    """ELI5: The electrician's step-by-step thought process as they trace a circuit."""
    step: int
    observation: str
    inference: str
    confidence: float  # 0.0 - 1.0


@dataclass
class AttachmentAnalysis:
    """ELI5: How two people 'wire' themselves together emotionally."""
    subject: str
    partner: str
    attachment_style: str  # secure, anxious, avoidant, disorganized
    evidence: List[str]
    reasoning: List[ReasoningChain]
    confidence: float


@dataclass
class TriangulationEvent:
    """ELI5: When someone talks about Person A to Person B in a way that creates a secret third circuit."""
    speaker: str
    target: str
    listener: str
    context: str
    manipulative_score: float  # 0-1
    reasoning: List[ReasoningChain]


@dataclass
class EmotionalTrajectory:
    """ELI5: Plotting how the voltage (emotions) changed over time between two wires."""
    thread_id: str
    start_sentiment: str
    end_sentiment: str
    trajectory: str  # improving, declining, volatile, stable
    inflection_points: List[Dict[str, Any]]
    reasoning: List[ReasoningChain]


@dataclass
class RelationshipNode:
    """ELI5: One person in the wiring diagram — how they connect to everyone else."""
    name: str
    role: str
    connections: Dict[str, Dict[str, Any]]
    centrality_score: float
    risk_profile: str  # low, moderate, high, critical


@dataclass
class OrbitScribeReport:
    """ELI5: The complete building wiring analysis with the master electrician's full report."""
    device_owner: str
    analysis_timestamp: str
    attachment_analyses: List[AttachmentAnalysis]
    triangulation_events: List[TriangulationEvent]
    emotional_trajectories: List[EmotionalTrajectory]
    relationship_graph: List[RelationshipNode]
    overall_narrative: str
    llm_reasoning_summary: str
    risk_level: str
    llm_used: bool
    raw_llm_response: str = ""


# ---------------------------------------------------------------------------
# OrbitScribe Engine
# ---------------------------------------------------------------------------

class OrbitScribeEngine:
    """
    ELI5: The master electrician's diagnostic kit.
          Mode 1: Call the real expert (LLM) for deep reasoning.
          Mode 2: Use the apprentice's trained eye for instant results.
    """

    # Resolve data dir relative to project root (works regardless of CWD)
    DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "phone_simulator"

    def __init__(self, data_dir: Optional[Path] = None, use_llm: bool = True):
        self.data_dir = data_dir or self.DATA_DIR
        self.use_llm = use_llm
        self._contacts: List[Dict] = []
        self._threads: Dict[str, Dict] = {}
        self._calls: List[Dict] = []
        self._media: List[Dict] = []
        self._locations: List[Dict] = []
        self._load_data()

    def _load_data(self) -> None:
        """ELI5: Pull out all the blueprints, call logs, and maintenance records."""
        contacts_path = self.data_dir / "contacts.json"
        if contacts_path.exists():
            with open(contacts_path, "r", encoding="utf-8") as f:
                self._contacts = json.load(f)

        threads_dir = self.data_dir / "threads"
        if threads_dir.exists():
            for tf in sorted(threads_dir.glob("*.json")):
                with open(tf, "r", encoding="utf-8") as f:
                    self._threads[tf.stem] = json.load(f)

        calls_path = self.data_dir / "call_logs.json"
        if calls_path.exists():
            with open(calls_path, "r", encoding="utf-8") as f:
                self._calls = json.load(f)

        media_path = self.data_dir / "media.json"
        if media_path.exists():
            with open(media_path, "r", encoding="utf-8") as f:
                self._media = json.load(f)

        locs_path = self.data_dir / "locations.json"
        if locs_path.exists():
            with open(locs_path, "r", encoding="utf-8") as f:
                self._locations = json.load(f)

    # -----------------------------------------------------------------------
    # LLM Interface
    # -----------------------------------------------------------------------

    def _query_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """ELI5: Call the master electrician on the radio for their expert opinion."""
        if not self.use_llm:
            return ""
        from core.unified.llm_fallback import query_llm_with_fallback
        return query_llm_with_fallback(prompt, system_prompt=system_prompt, timeout=90)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """ELI5: Sometimes the electrician mumbles. Extract the structured report from their rambling."""
        text = text.strip()
        if "```json" in text:
            json_part = text.split("```json")[1].split("```")[0].strip()
            try:
                return json.loads(json_part)
            except json.JSONDecodeError:
                pass
        if "```" in text:
            parts = text.split("```")
            for p in parts[1:]:
                p = p.strip()
                if p.startswith("{") or p.startswith("["):
                    try:
                        return json.loads(p)
                    except json.JSONDecodeError:
                        pass
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        return {"raw_response": text, "parsed": False}

    # -----------------------------------------------------------------------
    # Compact Context Builder (key messages only, not full dump)
    # -----------------------------------------------------------------------

    def _build_compact_context(self) -> str:
        """ELI5: Give the electrician only the most important pages, not the whole filing cabinet."""
        lines = ["RELATIONSHIP DATA SUMMARY\n"]
        lines.append("CONTACTS:")
        for c in self._contacts:
            rel = c.get("relationship", "unknown")
            notes = c.get("notes", "")
            lines.append(f"- {c['name']} ({rel}): {notes}")

        lines.append("\nKEY THREADS (first 5 messages each):")
        for tid, thread in self._threads.items():
            parts = thread.get("participants", [])
            msgs = thread.get("messages", [])
            lines.append(f"\nThread: {tid} | Participants: {', '.join(parts)} | Total: {len(msgs)} msgs")
            # Pick first 3 and last 2 messages for trajectory
            selected = msgs[:3]
            if len(msgs) > 5:
                selected.extend(msgs[-2:])
            for m in selected:
                ts = m.get("timestamp", "")[:10]
                sender = m.get("sender", "?")
                text = m.get("text", "")[:100]
                lines.append(f"  [{ts}] {sender}: {text}")

        lines.append("\nCALL LOGS:")
        for call in self._calls[:8]:
            lines.append(f"- {call.get('contact','?')}: {call.get('direction','?')} {call.get('duration',0)}s")

        lines.append("\nLOCATIONS:")
        for loc in self._locations[:4]:
            lines.append(f"- {loc.get('name','?')} @ {loc.get('timestamp','')}")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Core Analyses (parallel-ready)
    # -----------------------------------------------------------------------

    def analyze_attachments(self) -> List[AttachmentAnalysis]:
        context = self._build_compact_context()
        prompt = f"""You are a relationship psychology expert.

{context}

Analyze ATTACHMENT STYLES between Sarah Reynolds and each significant contact.
Return ONLY valid JSON:
{{"analyses":[{{"subject":"Sarah Reynolds","partner":"name","attachment_style":"anxious","evidence":["quote"],"reasoning":[{{"step":1,"observation":"...","inference":"...","confidence":0.85}}],"confidence":0.82}}]}}
"""
        system = "You are a clinical psychologist. Be precise, evidence-based, return only valid JSON."
        raw = self._query_llm(prompt, system_prompt=system)
        parsed = self._parse_json_response(raw)

        results = []
        for item in parsed.get("analyses", []):
            reasoning = [
                ReasoningChain(
                    step=r.get("step", i + 1),
                    observation=r.get("observation", ""),
                    inference=r.get("inference", ""),
                    confidence=r.get("confidence", 0.5),
                )
                for i, r in enumerate(item.get("reasoning", []))
            ]
            results.append(AttachmentAnalysis(
                subject=item.get("subject", "Sarah Reynolds"),
                partner=item.get("partner", ""),
                attachment_style=item.get("attachment_style", "unknown"),
                evidence=item.get("evidence", []),
                reasoning=reasoning,
                confidence=item.get("confidence", 0.5),
            ))
        return results

    def analyze_triangulation(self) -> List[TriangulationEvent]:
        context = self._build_compact_context()
        prompt = f"""You are a forensic communication analyst.

{context}

Find TRIANGULATION events — when someone discusses a third person to manipulate perceptions.
Return ONLY valid JSON:
{{"events":[{{"speaker":"...","target":"...","listener":"...","context":"...","manipulative_score":0.75,"reasoning":[{{"step":1,"observation":"...","inference":"...","confidence":0.8}}]}}]}}
"""
        system = "You are an expert in triangulation and emotional manipulation. Return only valid JSON."
        raw = self._query_llm(prompt, system_prompt=system)
        parsed = self._parse_json_response(raw)

        results = []
        for item in parsed.get("events", []):
            reasoning = [
                ReasoningChain(
                    step=r.get("step", i + 1),
                    observation=r.get("observation", ""),
                    inference=r.get("inference", ""),
                    confidence=r.get("confidence", 0.5),
                )
                for i, r in enumerate(item.get("reasoning", []))
            ]
            results.append(TriangulationEvent(
                speaker=item.get("speaker", ""),
                target=item.get("target", ""),
                listener=item.get("listener", ""),
                context=item.get("context", ""),
                manipulative_score=item.get("manipulative_score", 0.0),
                reasoning=reasoning,
            ))
        return results

    def analyze_emotional_trajectories(self) -> List[EmotionalTrajectory]:
        context = self._build_compact_context()
        prompt = f"""You are a sentiment trajectory analyst.

{context}

For each thread, analyze EMOTIONAL TRAJECTORY over time.
Return ONLY valid JSON:
{{"trajectories":[{{"thread_id":"...","start_sentiment":"positive","end_sentiment":"negative","trajectory":"declining","inflection_points":[{{"date":"2026-03-05","event":"...","sentiment_shift":"positive to negative"}}],"reasoning":[{{"step":1,"observation":"...","inference":"...","confidence":0.85}}]}}]}}
"""
        system = "You are an expert in longitudinal emotional analysis. Return only valid JSON."
        raw = self._query_llm(prompt, system_prompt=system)
        parsed = self._parse_json_response(raw)

        results = []
        for item in parsed.get("trajectories", []):
            reasoning = [
                ReasoningChain(
                    step=r.get("step", i + 1),
                    observation=r.get("observation", ""),
                    inference=r.get("inference", ""),
                    confidence=r.get("confidence", 0.5),
                )
                for i, r in enumerate(item.get("reasoning", []))
            ]
            results.append(EmotionalTrajectory(
                thread_id=item.get("thread_id", ""),
                start_sentiment=item.get("start_sentiment", ""),
                end_sentiment=item.get("end_sentiment", ""),
                trajectory=item.get("trajectory", ""),
                inflection_points=item.get("inflection_points", []),
                reasoning=reasoning,
            ))
        return results

    def build_relationship_graph(self) -> List[RelationshipNode]:
        context = self._build_compact_context()
        prompt = f"""You are a network analyst mapping a social relationship graph.

{context}

Build a RELATIONSHIP GRAPH.
Return ONLY valid JSON:
{{"nodes":[{{"name":"Sarah Reynolds","role":"device_owner","connections":{{"Derek":{{"strength":0.8,"type":"romantic","risk":0.7}}}},"centrality_score":0.95,"risk_profile":"high"}}]}}
"""
        system = "You are a social network analyst. Return only valid JSON."
        raw = self._query_llm(prompt, system_prompt=system)
        parsed = self._parse_json_response(raw)

        results = []
        for item in parsed.get("nodes", []):
            results.append(RelationshipNode(
                name=item.get("name", ""),
                role=item.get("role", "other"),
                connections=item.get("connections", {}),
                centrality_score=item.get("centrality_score", 0.0),
                risk_profile=item.get("risk_profile", "low"),
            ))
        return results

    def generate_narrative(self) -> str:
        context = self._build_compact_context()
        prompt = f"""You are a forensic narrative analyst.

{context}

Write a compelling 3-paragraph narrative summary:
P1: Setup — who are these people and what do they mean to each other.
P2: Conflict — what tensions, secrets, or unhealthy dynamics are emerging.
P3: Prognosis — where is this heading if nothing changes.

Clinical but empathetic tone. Use specific names and evidence. Max 300 words.
"""
        system = "You are an expert forensic narrative writer. Write a concise, evidence-based story."
        return self._query_llm(prompt, system_prompt=system)

    # -----------------------------------------------------------------------
    # Synthetic Fallback — instant demo when LLM is unavailable
    # -----------------------------------------------------------------------

    def _synthetic_attachments(self) -> List[AttachmentAnalysis]:
        """ELI5: The apprentice electrician fills in the report based on what they can see with their own eyes."""
        return [
            AttachmentAnalysis(
                subject="Sarah Reynolds",
                partner="Derek Holloway",
                attachment_style="anxious",
                evidence=[
                    "'I know you're stressed but please answer'",
                    "'I just need to know you're okay'",
                    "Multiple unread messages with escalating urgency",
                ],
                reasoning=[
                    ReasoningChain(1, "Sarah sends 4 messages before Derek responds once", "High anxiety about responsiveness", 0.85),
                    ReasoningChain(2, "Messages contain pleading and reassurance-seeking language", "Anxious attachment pattern", 0.80),
                    ReasoningChain(3, "Derek's responses are shorter and less frequent over time", "Avoidant counter-pattern creating pursuit-distance dynamic", 0.75),
                ],
                confidence=0.82,
            ),
            AttachmentAnalysis(
                subject="Sarah Reynolds",
                partner="Marcus Chen",
                attachment_style="secure",
                evidence=[
                    "'I really enjoyed our conversation yesterday'",
                    "Balanced message lengths and response times",
                    "Mutual humor and professional respect",
                ],
                reasoning=[
                    ReasoningChain(1, "Messages show reciprocal communication with equal initiation", "Balanced give-and-take", 0.80),
                    ReasoningChain(2, "Content is warm but not desperate or controlling", "Healthy boundary maintenance", 0.85),
                    ReasoningChain(3, "No excessive apology or reassurance seeking", "Secure self-image in relationship", 0.78),
                ],
                confidence=0.78,
            ),
            AttachmentAnalysis(
                subject="Sarah Reynolds",
                partner="Jessica Park",
                attachment_style="secure",
                evidence=[
                    "'Thanks for always being there for me'",
                    "Confidential legal advice requests",
                    "Consistent supportive responses",
                ],
                reasoning=[
                    ReasoningChain(1, "Sarah trusts Jessica with sensitive legal matters", "High trust, secure friendship", 0.85),
                    ReasoningChain(2, "Jessica provides boundary-respecting support", "Mutual respect and autonomy", 0.82),
                ],
                confidence=0.80,
            ),
        ]

    def _synthetic_triangulations(self) -> List[TriangulationEvent]:
        return [
            TriangulationEvent(
                speaker="Sarah Reynolds",
                target="Derek Holloway",
                listener="Jessica Park",
                context="Sarah tells Jessica that Derek is 'becoming impossible to deal with' and asks for legal advice about disability accommodations while simultaneously discussing relationship exit strategies.",
                manipulative_score=0.45,
                reasoning=[
                    ReasoningChain(1, "Sarah uses Jessica's professional role to process relationship dissatisfaction", "Creating an alliance against Derek", 0.70),
                    ReasoningChain(2, "Legal advice is legitimate but emotional content suggests venting, not just planning", "Mixed motives — practical help + emotional alliance", 0.65),
                ],
            ),
            TriangulationEvent(
                speaker="Derek Holloway",
                target="Sarah Reynolds",
                listener="Marcus Chen",
                context="Derek messages Marcus through a fake account warning him to 'stay away from Sarah' and implying he knows about their meetings.",
                manipulative_score=0.92,
                reasoning=[
                    ReasoningChain(1, "Derek uses a third party to intimidate without direct confrontation", "Proxy threat strategy", 0.90),
                    ReasoningChain(2, "Implication of surveillance ('I know about your meetings') creates fear", "Coercive control through information dominance", 0.88),
                    ReasoningChain(3, "Message sent through fake account indicates awareness of wrongdoing", "Premeditated manipulation", 0.85),
                ],
            ),
        ]

    def _synthetic_trajectories(self) -> List[EmotionalTrajectory]:
        return [
            EmotionalTrajectory(
                thread_id="sarah_derek",
                start_sentiment="positive",
                end_sentiment="negative",
                trajectory="declining",
                inflection_points=[
                    {"date": "2026-03-05", "event": "Derek accuses Sarah of hiding phone", "sentiment_shift": "neutral to negative"},
                    {"date": "2026-03-10", "event": "Sarah starts deleting messages before Derek sees them", "sentiment_shift": "negative to hostile"},
                    {"date": "2026-03-15", "event": "Derek threatens to expose Sarah to family", "sentiment_shift": "hostile to fearful"},
                ],
                reasoning=[
                    ReasoningChain(1, "Early messages show affection and care for Derek's disability", "Baseline positive relationship", 0.85),
                    ReasoningChain(2, "Mid-thread introduces surveillance and accusation language", "Trust erosion begins", 0.80),
                    ReasoningChain(3, "Late thread shows threat escalation and Sarah's defensive responses", "Relationship entering crisis phase", 0.88),
                ],
            ),
            EmotionalTrajectory(
                thread_id="sarah_marcus",
                start_sentiment="positive",
                end_sentiment="positive",
                trajectory="improving",
                inflection_points=[
                    {"date": "2026-03-03", "event": "First personal conversation beyond work", "sentiment_shift": "professional to warm"},
                    {"date": "2026-03-12", "event": "Shared inside jokes and emotional support", "sentiment_shift": "warm to intimate"},
                ],
                reasoning=[
                    ReasoningChain(1, "Conversation begins professionally but quickly becomes personal", "Emotional affair developing", 0.80),
                    ReasoningChain(2, "Mutual disclosure increases over time without conflict", "Safe emotional space forming", 0.82),
                ],
            ),
        ]

    def _synthetic_graph(self) -> List[RelationshipNode]:
        return [
            RelationshipNode(
                name="Sarah Reynolds",
                role="device_owner",
                connections={
                    "Derek Holloway": {"strength": 0.85, "type": "romantic", "risk": 0.80},
                    "Marcus Chen": {"strength": 0.65, "type": "affair", "risk": 0.55},
                    "Jessica Park": {"strength": 0.70, "type": "friend", "risk": 0.15},
                    "Mom": {"strength": 0.40, "type": "family", "risk": 0.35},
                },
                centrality_score=0.95,
                risk_profile="high",
            ),
            RelationshipNode(
                name="Derek Holloway",
                role="partner",
                connections={
                    "Sarah Reynolds": {"strength": 0.90, "type": "romantic", "risk": 0.85},
                },
                centrality_score=0.60,
                risk_profile="critical",
            ),
            RelationshipNode(
                name="Marcus Chen",
                role="coworker",
                connections={
                    "Sarah Reynolds": {"strength": 0.65, "type": "affair", "risk": 0.50},
                },
                centrality_score=0.45,
                risk_profile="moderate",
            ),
            RelationshipNode(
                name="Jessica Park",
                role="friend",
                connections={
                    "Sarah Reynolds": {"strength": 0.70, "type": "friend", "risk": 0.10},
                },
                centrality_score=0.40,
                risk_profile="low",
            ),
        ]

    def _synthetic_narrative(self) -> str:
        return (
            "Sarah Reynolds is caught in a deteriorating relationship with Derek Holloway, her boyfriend of two years. "
            "Derek, who recently became disabled, has shifted from a supportive partner to a controlling and surveillance-oriented figure. "
            "He goes through her phone, tracks her location, and threatens social destruction if she leaves.\n\n"
            "At the same time, Sarah has developed an emotional affair with Marcus Chen, a coworker. Their relationship provides the warmth, "
            "respect, and emotional safety that Derek's relationship now lacks. Sarah confides in her best friend Jessica Park, a lawyer, "
            "about both her legal concerns and her emotional distress.\n\n"
            "Without intervention, this trajectory leads toward either a violent escalation from Derek or Sarah making a secret exit. "
            "The control dynamics, combined with Derek's threats and Sarah's growing independence, create a high-risk powder keg situation."
        )

    # -----------------------------------------------------------------------
    # Full Report Generation
    # -----------------------------------------------------------------------

    def generate_full_report(self) -> OrbitScribeReport:
        """ELI5: Run the complete master electrician inspection and compile the full report."""
        logger.info("OrbitScribe: starting full relationship analysis (llm=%s)...", self.use_llm)

        if self.use_llm:
            # Try LLM-powered analysis
            try:
                # Run analyses in parallel using thread pool
                with ThreadPoolExecutor(max_workers=5) as pool:
                    future_attachments = pool.submit(self.analyze_attachments)
                    future_triangulations = pool.submit(self.analyze_triangulation)
                    future_trajectories = pool.submit(self.analyze_emotional_trajectories)
                    future_graph = pool.submit(self.build_relationship_graph)
                    future_narrative = pool.submit(self.generate_narrative)

                    attachments = future_attachments.result(timeout=120)
                    triangulations = future_triangulations.result(timeout=120)
                    trajectories = future_trajectories.result(timeout=120)
                    graph = future_graph.result(timeout=120)
                    narrative = future_narrative.result(timeout=120)

                # Check if we got meaningful data
                if any([attachments, triangulations, trajectories, graph]) and narrative.strip():
                    llm_used = True
                else:
                    logger.warning("OrbitScribe: LLM returned empty data, falling back to synthetic")
                    llm_used = False
                    attachments = self._synthetic_attachments()
                    triangulations = self._synthetic_triangulations()
                    trajectories = self._synthetic_trajectories()
                    graph = self._synthetic_graph()
                    narrative = self._synthetic_narrative()
            except Exception as exc:
                logger.warning("OrbitScribe: LLM analysis failed (%s), using synthetic fallback", exc)
                llm_used = False
                attachments = self._synthetic_attachments()
                triangulations = self._synthetic_triangulations()
                trajectories = self._synthetic_trajectories()
                graph = self._synthetic_graph()
                narrative = self._synthetic_narrative()
        else:
            llm_used = False
            attachments = self._synthetic_attachments()
            triangulations = self._synthetic_triangulations()
            trajectories = self._synthetic_trajectories()
            graph = self._synthetic_graph()
            narrative = self._synthetic_narrative()

        # Determine overall risk
        risk_scores = []
        for node in graph:
            risk_map = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
            risk_scores.append(risk_map.get(node.risk_profile, 1))
        avg_risk = sum(risk_scores) / max(len(risk_scores), 1)
        risk_level = "low"
        if avg_risk >= 3.5:
            risk_level = "critical"
        elif avg_risk >= 2.5:
            risk_level = "high"
        elif avg_risk >= 1.5:
            risk_level = "moderate"

        reasoning_summary = (
            f"OrbitScribe analyzed {len(self._threads)} conversation threads, "
            f"{len(self._calls)} calls, and {len(self._contacts)} contacts.\n"
            f"Attachment analyses: {len(attachments)} relationships mapped.\n"
            f"Triangulation events: {len(triangulations)} instances of third-party manipulation detected.\n"
            f"Emotional trajectories: {len(trajectories)} thread timelines analyzed.\n"
            f"Relationship graph: {len(graph)} nodes with cross-connection risk assessment.\n"
            f"LLM reasoning: {'USED' if llm_used else 'SYNTHETIC DEMO MODE'}"
        )

        return OrbitScribeReport(
            device_owner="Sarah Reynolds",
            analysis_timestamp=datetime.now().isoformat(),
            attachment_analyses=attachments,
            triangulation_events=triangulations,
            emotional_trajectories=trajectories,
            relationship_graph=graph,
            overall_narrative=narrative,
            llm_reasoning_summary=reasoning_summary,
            risk_level=risk_level,
            llm_used=llm_used,
        )
