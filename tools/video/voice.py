"""Voice a module script, one mp3 per distinct sentence.

voice_script returns the timeline: a copy of the script with "dur" (seconds) and "audio"
("audio/<name>.mp3", relative to the module page) on every cue. The name is the first 16 hex
characters of the speaker's cached wav, so equal words share one file and a changed word makes one
new file. prune_audio removes the mp3s no timeline uses any more.
"""
import copy
import os
import subprocess
import sys
import wave
from pathlib import Path

DEMO_VIDEOS = Path.home() / "Projects" / "demo_videos"
FFMPEG = "/opt/homebrew/bin/ffmpeg"


def _demo_videos():
    """Import demo_videos' narration modules; settings.env resolves from its root."""
    scripts = str(DEMO_VIDEOS / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    here = os.getcwd()
    os.chdir(DEMO_VIDEOS)
    try:
        import narrate
        import pronunciation
        import settings
    finally:
        os.chdir(here)
    return narrate, pronunciation, settings


def shared_pronunciation() -> dict:
    """The owner's shared pronunciation file: {word: spoken form}."""
    _, pronunciation, _ = _demo_videos()
    entries = pronunciation.load(pronunciation.file_path())
    return dict(entries[0] if isinstance(entries, tuple) else entries)


def new_speaker():
    """A Watson speaker with the owner's voice."""
    narrate, _, settings = _demo_videos()
    return narrate.Speaker(settings.get("DEMO_VOICE", required=True))


def spoken(text, say):
    narrate, _, _ = _demo_videos()
    return narrate.spoken(text, say)


def _seconds(wav):
    with wave.open(wav) as w:
        return round(w.getnframes() / w.getframerate(), 2)


def _mp3(wav, out):
    tmp = out.with_suffix(".part.mp3")
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", wav, "-ac", "1", "-b:a", "48k", str(tmp)], check=True)
    tmp.replace(out)


def voice_script(script: dict, audio_dir: Path, speaker, shared: dict = None) -> dict:
    """The timeline for script. The script's own pronounce map wins over the shared entries."""
    audio_dir = Path(audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    effective = {**(shared or {}), **script.get("pronounce", {})}
    timeline = copy.deepcopy(script)
    for step in timeline["steps"]:
        for cue in step["cues"]:
            wav = speaker.wav(spoken(cue["say"], effective))
            name = Path(wav).name[:16] + ".mp3"
            out = audio_dir / name
            if not out.exists():
                _mp3(wav, out)
            cue["dur"] = _seconds(wav)
            cue["audio"] = "audio/" + name
    return timeline


def prune_audio(audio_dir: Path, timelines: list) -> list:
    """Delete the mp3s in audio_dir that no timeline names; return the paths deleted."""
    used = {Path(c["audio"]).name for t in timelines for s in t["steps"] for c in s["cues"]}
    gone = []
    for mp3 in sorted(Path(audio_dir).glob("*.mp3")):
        if mp3.name not in used:
            mp3.unlink()
            gone.append(mp3)
    return gone
