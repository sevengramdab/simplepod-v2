#!/usr/bin/env python3
"""
cleanup_engine.py
=================
First-class disk cleanup agent for SimplePod Swarm nodes.

ELI5: Think of this like a panel schedule audit before a load calculation.
      The electrician walks every circuit, reads every breaker label,
      checks the wire gauge, and flags anything that looks overloaded
      or unsafe to touch. Only after the audit do you flip breakers.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class DiskInfo:
    drive: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent_free: float
    is_critical: bool


@dataclass
class GameItem:
    name: str
    platform: str
    size_gb: float
    path: str


@dataclass
class FileSafetyReport:
    path: str
    size_mb: float
    safety_score: int  # 0-100, higher = safer to delete
    safety_reason: str
    category: str  # temp, cache, log, download, game, system, user_data, etc.
    last_modified_days: int
    is_directory: bool


@dataclass
class CleanupResult:
    success: bool
    freed_gb: float
    deleted: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    message: str = ""


# ---------------------------------------------------------------------------
# Safety scoring engine
# ---------------------------------------------------------------------------
SAFE_PATTERNS: List[Tuple[List[str], str, int, str]] = [
    # (path_substrings, category, score, reason)
    (["temp", "tmp"], "temp", 95, "Temporary file — safe to remove"),
    (["cache", "cached"], "cache", 90, "Cache — will be rebuilt automatically"),
    (["logs", ".log", "logfile"], "log", 85, "Log file — old logs are usually safe"),
    (["download"], "download", 80, "Download — user can re-download"),
    (["recycle.bin", "trash"], "recycle", 95, "Recycle bin — already marked for deletion"),
    (["installer", "setup.exe", "install.exe"], "installer", 75, "Installer — can re-download if needed"),
    (["crashdump", "minidump", "dmp"], "crashdump", 90, "Crash dump — diagnostic data, safe to clear"),
    (["thumbnail", "thumbcache"], "thumbnail", 95, "Thumbnail cache — regenerates automatically"),
    (["windows\\prefetch"], "prefetch", 70, "Windows prefetch — safe but may slow startup slightly"),
    (["windows\\softwaredistribution\\download"], "windows_update", 85, "Windows Update download cache — safe to clear"),
    ([".old", "backup.old"], "old_backup", 60, "Old backup — verify before deleting"),
]

DANGEROUS_PATTERNS: List[Tuple[List[str], str, int, str]] = [
    (["windows\\system32", "windows\\syswow64"], "system", 0, "CRITICAL: Windows system file"),
    (["program files", "program files (x86)"], "program", 10, "Installed application — use uninstaller"),
    (["users\\", "home\\"], "user_home", 40, "User home directory — contains personal data"),
    (["boot", "efi"], "boot", 0, "CRITICAL: Boot partition file"),
    (["registry", "regedit"], "registry", 0, "CRITICAL: Windows registry"),
    (["drivers"], "driver", 5, "System driver — may break hardware"),
    (["config.sys", "autoexec.bat", "boot.ini"], "boot_config", 0, "CRITICAL: Boot configuration"),
]


def _path_lower(path: str) -> str:
    return path.lower().replace("/", "\\")


def analyze_file_safety(path: str, size_bytes: int) -> FileSafetyReport:
    """
    ELI5: Like reading the wire label on every conductor before you cut it.
          Red tag = live 480V (system file). Green tag = low-voltage control
          wire (temp file). You only cut the green ones.
    """
    p = Path(path)
    is_dir = p.is_dir()
    size_mb = round(size_bytes / (1024 * 1024), 2)
    path_lower = _path_lower(str(path))

    # Last modified
    try:
        mtime = p.stat().st_mtime
        last_modified_days = int((time.time() - mtime) / 86400)
    except Exception:
        last_modified_days = 999

    # Check known patterns
    for substrings, category, score, reason in SAFE_PATTERNS:
        if any(s in path_lower for s in substrings):
            # Age penalty for logs (reduce score if recent)
            if category == "log" and last_modified_days < 7:
                score = max(30, score - 40)
                reason = "Recent log file (< 7 days) — may be needed for debugging"
            return FileSafetyReport(
                path=path, size_mb=size_mb, safety_score=score,
                safety_reason=reason, category=category,
                last_modified_days=last_modified_days, is_directory=is_dir
            )

    for substrings, category, score, reason in DANGEROUS_PATTERNS:
        if any(s in path_lower for s in substrings):
            return FileSafetyReport(
                path=path, size_mb=size_mb, safety_score=score,
                safety_reason=reason, category=category,
                last_modified_days=last_modified_days, is_directory=is_dir
            )

    # Default heuristics
    ext = p.suffix.lower()
    if ext in {".tmp", ".temp", ".cache", ".old", ".bak", ".dmp", ".log"}:
        score = 85
        category = "temp"
        reason = f"Known temporary extension ({ext}) — likely safe"
        if ext == ".log" and last_modified_days < 7:
            score = 45
            reason = "Recent log file — may be needed for debugging"
        return FileSafetyReport(
            path=path, size_mb=size_mb, safety_score=score,
            safety_reason=reason, category=category,
            last_modified_days=last_modified_days, is_directory=is_dir
        )

    # Large files in user downloads
    if "downloads" in path_lower:
        return FileSafetyReport(
            path=path, size_mb=size_mb, safety_score=70,
            safety_reason="Download folder — usually safe if not recently downloaded",
            category="download", last_modified_days=last_modified_days, is_directory=is_dir
        )

    # Unknown files — conservative score
    return FileSafetyReport(
        path=path, size_mb=size_mb, safety_score=30,
        safety_reason="Unknown file type — manual review recommended",
        category="unknown", last_modified_days=last_modified_days, is_directory=is_dir
    )


# ---------------------------------------------------------------------------
# Game discovery
# ---------------------------------------------------------------------------
GAME_PATHS: Dict[str, List[str]] = {
    "steam": [
        "C:/Program Files (x86)/Steam/steamapps/common",
        "C:/Program Files/Steam/steamapps/common",
    ],
    "epic": [
        "C:/Program Files/Epic Games",
    ],
    "ea": [
        "C:/Program Files/EA Games",
        "C:/Program Files (x86)/EA Games",
        "C:/Program Files/Origin Games",
        "C:/Program Files (x86)/Origin Games",
    ],
    "battlenet": [
        "C:/Program Files (x86)/Battle.net",
        "C:/Program Files/Battle.net",
    ],
    "ubisoft": [
        "C:/Program Files (x86)/Ubisoft/Ubisoft Game Launcher/games",
        "C:/Program Files/Ubisoft/Ubisoft Game Launcher/games",
    ],
    "xbox": [
        "C:/XboxGames",
    ],
    "ableton": [
        "C:/ProgramData/Ableton",
        "C:/Program Files/Ableton",
        "C:/Program Files (x86)/Ableton",
    ],
}


def _folder_size(path: Path) -> float:
    """Return folder size in GB."""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                try:
                    total += entry.stat(follow_symlinks=False).st_size
                except Exception:
                    pass
            elif entry.is_dir(follow_symlinks=False):
                total += _folder_size(entry.path) * (1024 * 1024 * 1024)
    except Exception:
        pass
    return round(total / (1024 * 1024 * 1024), 2)


def _folder_size_fast(path: Path) -> float:
    """Fast folder size using du on Unix, fallback to Python walk."""
    system = platform.system().lower()
    if system != "windows":
        try:
            out = subprocess.check_output(
                ["du", "-sb", str(path)],
                stderr=subprocess.DEVNULL, text=True, timeout=10
            )
            bytes_size = int(out.split()[0])
            return round(bytes_size / (1024 * 1024 * 1024), 2)
        except Exception:
            pass
    return _folder_size(path)


def find_games(drive: str = "C:/") -> List[GameItem]:
    """
    ELI5: Like walking the basement and attic looking for every appliance
          that's plugged in and drawing power. You want to know which ones
          are the big energy hogs before you decide what to unplug.
    """
    games: List[GameItem] = []
    for platform_name, paths in GAME_PATHS.items():
        for raw in paths:
            p = Path(raw)
            if not p.exists():
                continue
            try:
                for child in p.iterdir():
                    if not child.is_dir():
                        continue
                    # Skip launcher folders for Battle.net
                    if platform_name == "battlenet" and "launcher" in child.name.lower():
                        continue
                    sz = _folder_size_fast(child)
                    if sz < 0.1:
                        continue
                    games.append(GameItem(
                        name=child.name,
                        platform=platform_name,
                        size_gb=sz,
                        path=str(child)
                    ))
            except Exception:
                pass

        # Ableton — also check for "Ableton Live*" folders in Program Files
        if platform_name == "ableton":
            for pf in ["C:/Program Files", "C:/Program Files (x86)"]:
                pf_path = Path(pf)
                if not pf_path.exists():
                    continue
                try:
                    for child in pf_path.iterdir():
                        if child.is_dir() and child.name.lower().startswith("ableton live"):
                            sz = _folder_size_fast(child)
                            if sz < 0.1:
                                continue
                            games.append(GameItem(
                                name=child.name,
                                platform="ableton",
                                size_gb=sz,
                                path=str(child)
                            ))
                except Exception:
                    pass

    return sorted(games, key=lambda g: g.size_gb, reverse=True)


# ---------------------------------------------------------------------------
# Disk analysis
# ---------------------------------------------------------------------------
def get_disk_info(drive: str = "C:/") -> DiskInfo:
    """
    ELI5: Like reading the main demand meter on the service entrance.
          It tells you total capacity, current draw, and remaining headroom.
    """
    system = platform.system().lower()
    if system == "windows":
        drive = drive.replace("/", "\\")
        try:
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            total_free = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(drive),
                ctypes.pointer(free_bytes),
                ctypes.pointer(total_bytes),
                ctypes.pointer(total_free),
            )
            total_gb = round(total_bytes.value / (1024 ** 3), 2)
            free_gb = round(free_bytes.value / (1024 ** 3), 2)
            used_gb = round(total_gb - free_gb, 2)
            pct_free = round((free_gb / total_gb) * 100, 1) if total_gb > 0 else 0
            return DiskInfo(
                drive=drive, total_gb=total_gb, used_gb=used_gb,
                free_gb=free_gb, percent_free=pct_free,
                is_critical=pct_free < 10
            )
        except Exception:
            pass
    else:
        try:
            st = os.statvfs(drive)
            total_gb = round((st.f_blocks * st.f_frsize) / (1024 ** 3), 2)
            free_gb = round((st.f_bavail * st.f_frsize) / (1024 ** 3), 2)
            used_gb = round(total_gb - free_gb, 2)
            pct_free = round((free_gb / total_gb) * 100, 1) if total_gb > 0 else 0
            return DiskInfo(
                drive=drive, total_gb=total_gb, used_gb=used_gb,
                free_gb=free_gb, percent_free=pct_free,
                is_critical=pct_free < 10
            )
        except Exception:
            pass

    return DiskInfo(drive=drive, total_gb=0, used_gb=0, free_gb=0, percent_free=0, is_critical=True)


# ---------------------------------------------------------------------------
# Large file scanner
# ---------------------------------------------------------------------------
def find_large_files(
    root: str = "C:/",
    min_size_mb: float = 100,
    max_files: int = 200,
    exclude_system: bool = True,
) -> List[FileSafetyReport]:
    """
    ELI5: Like using a thermal camera to find the hottest spots in a panel.
          Big files = high heat. The safety score tells you if that heat
          is normal (a running motor) or dangerous (a loose connection).
    """
    reports: List[FileSafetyReport] = []
    root_path = Path(root)
    system = platform.system().lower()

    # Exclude paths that are too dangerous or slow to scan
    skip_paths: set = set()
    if system == "windows":
        skip_prefixes = [
            "windows\\system32", "windows\\syswow64", "windows\\winsxs",
            "programdata\\microsoft", "$recycle.bin", "program files\\windowsapps",
        ]
    else:
        skip_prefixes = ["/bin", "/sbin", "/lib", "/lib64", "/usr/lib", "/dev", "/proc", "/sys"]

    def _should_skip(p: Path) -> bool:
        pl = _path_lower(str(p))
        for sp in skip_prefixes:
            if sp in pl:
                return True
        return False

    scanned = 0
    try:
        for entry in os.scandir(root_path):
            if entry.is_symlink():
                continue
            if _should_skip(Path(entry.path)):
                continue

            if entry.is_file(follow_symlinks=False):
                try:
                    st = entry.stat(follow_symlinks=False)
                    size_mb = st.st_size / (1024 * 1024)
                    if size_mb >= min_size_mb:
                        report = analyze_file_safety(entry.path, st.st_size)
                        if exclude_system and report.safety_score < 20:
                            continue
                        reports.append(report)
                        scanned += 1
                        if scanned >= max_files:
                            break
                except Exception:
                    pass
            elif entry.is_dir(follow_symlinks=False):
                # Walk subdirectories
                try:
                    for dirpath, dirnames, filenames in os.walk(entry.path):
                        # Filter out skip paths
                        dirnames[:] = [
                            d for d in dirnames
                            if not _should_skip(Path(os.path.join(dirpath, d)))
                        ]
                        for fname in filenames:
                            fpath = os.path.join(dirpath, fname)
                            try:
                                st = os.stat(fpath, follow_symlinks=False)
                                size_mb = st.st_size / (1024 * 1024)
                                if size_mb >= min_size_mb:
                                    report = analyze_file_safety(fpath, st.st_size)
                                    if exclude_system and report.safety_score < 20:
                                        continue
                                    reports.append(report)
                                    scanned += 1
                                    if scanned >= max_files:
                                        raise StopIteration
                            except Exception:
                                pass
                except StopIteration:
                    break
                except Exception:
                    pass
    except Exception:
        pass

    return sorted(reports, key=lambda r: r.size_mb, reverse=True)


# ---------------------------------------------------------------------------
# Cleanup execution
# ---------------------------------------------------------------------------
def execute_cleanup(targets: List[Dict[str, Any]]) -> CleanupResult:
    """
    ELI5: Like tripping breakers after the audit is complete.
          You ONLY touch the ones marked green (safe).
          If a breaker is red-tagged (system file), you skip it.
    """
    deleted: List[str] = []
    failed: List[str] = []
    freed_bytes = 0

    for target in targets:
        path = target.get("path", "")
        force = target.get("force", False)
        if not path or not os.path.exists(path):
            failed.append(path)
            continue

        # Re-evaluate safety unless forced
        if not force:
            report = analyze_file_safety(path, os.path.getsize(path) if os.path.isfile(path) else 0)
            if report.safety_score < 50:
                failed.append(path)
                continue

        try:
            p = Path(path)
            if p.is_dir():
                # Calculate size before delete for reporting
                freed_bytes += _folder_size(p) * (1024 * 1024 * 1024)
                shutil.rmtree(path, ignore_errors=True)
            else:
                freed_bytes += os.path.getsize(path)
                os.remove(path)
            deleted.append(path)
        except Exception:
            failed.append(path)

    freed_gb = round(freed_bytes / (1024 * 1024 * 1024), 2)
    return CleanupResult(
        success=len(deleted) > 0,
        freed_gb=freed_gb,
        deleted=deleted,
        failed=failed,
        message=f"Deleted {len(deleted)} items, freed {freed_gb} GB"
    )


# ---------------------------------------------------------------------------
# CleanupEngine class (swarm-agent interface)
# ---------------------------------------------------------------------------
class CleanupEngine:
    """
    ELI5: The cleanup crew foreman. They carry the clipboard with the
          panel schedule, direct the crew to each breaker, and make sure
          no one touches the main bus bars without a lockout tag.
    """

    def __init__(self, default_drive: str = "C:/"):
        self.default_drive = default_drive

    def analyze(self) -> Dict[str, Any]:
        disk = get_disk_info(self.default_drive)
        games = find_games(self.default_drive)
        return {
            "disk": {
                "drive": disk.drive,
                "total_gb": disk.total_gb,
                "used_gb": disk.used_gb,
                "free_gb": disk.free_gb,
                "percent_free": disk.percent_free,
                "is_critical": disk.is_critical,
            },
            "games": [
                {"name": g.name, "platform": g.platform, "size_gb": g.size_gb, "path": g.path}
                for g in games
            ],
            "game_total_gb": round(sum(g.size_gb for g in games), 2),
            "timestamp": time.time(),
        }

    def scan_large_files(self, min_size_mb: float = 100, max_files: int = 200) -> Dict[str, Any]:
        reports = find_large_files(self.default_drive, min_size_mb, max_files)
        return {
            "files": [
                {
                    "path": r.path,
                    "size_mb": r.size_mb,
                    "safety_score": r.safety_score,
                    "safety_reason": r.safety_reason,
                    "category": r.category,
                    "last_modified_days": r.last_modified_days,
                    "is_directory": r.is_directory,
                }
                for r in reports
            ],
            "total_scanned_mb": round(sum(r.size_mb for r in reports), 2),
            "safe_to_delete_mb": round(sum(r.size_mb for r in reports if r.safety_score >= 70), 2),
            "timestamp": time.time(),
        }

    def run(self, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        result = execute_cleanup(targets)
        return {
            "success": result.success,
            "freed_gb": result.freed_gb,
            "deleted": result.deleted,
            "failed": result.failed,
            "message": result.message,
        }


def analyze_disk_safety(drive: str = "C:/") -> Dict[str, Any]:
    """Convenience wrapper — full safety audit of a drive."""
    engine = CleanupEngine(drive)
    analysis = engine.analyze()
    large_files = engine.scan_large_files()
    return {
        "analysis": analysis,
        "large_files": large_files,
        "recommendations": _generate_recommendations(analysis, large_files),
    }


def _generate_recommendations(analysis: Dict[str, Any], large_files: Dict[str, Any]) -> List[str]:
    """Generate human-readable cleanup recommendations."""
    recs: List[str] = []
    disk = analysis.get("disk", {})
    if disk.get("is_critical"):
        recs.append(f"CRITICAL: Drive {disk.get('drive')} has only {disk.get('percent_free')}% free ({disk.get('free_gb')} GB remaining). Immediate cleanup recommended.")
    elif disk.get("percent_free", 100) < 20:
        recs.append(f"WARNING: Drive {disk.get('drive')} is below 20% free ({disk.get('percent_free')}%). Cleanup advised.")

    games = analysis.get("games", [])
    if games:
        total = analysis.get("game_total_gb", 0)
        recs.append(f"Found {len(games)} game installations using {total} GB. Largest: {games[0]['name']} ({games[0]['size_gb']} GB).")

    safe_mb = large_files.get("safe_to_delete_mb", 0)
    if safe_mb > 100:
        recs.append(f"Identified {round(safe_mb / 1024, 2)} GB of large files with safety score >= 70 (likely safe to delete).")

    if not recs:
        recs.append("Drive looks healthy. No immediate action required.")

    return recs
