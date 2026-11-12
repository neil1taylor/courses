"""Voice a module script, one mp3 per distinct sentence.

voice_script returns the timeline: a copy of the script with "dur" (seconds) and "audio"
("audio/<name>.mp3", relative to the module page) on every cue. The name is the first 16 hex
characters of the speaker's cached wav, so equal words share one file and a changed word makes one
new file. prune_audio removes the mp3s no timeline uses any more.
"""
import copy
import hashlib
import json
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
        sys.path.append(scripts)
    import narrate
    import pronunciation
    import settings
    return narrate, pronunciation, settings


def shared_pronunciation() -> dict:
    """The owner's shared pronunciation file: {word: spoken form}."""
    _, pronunciation, _ = _demo_videos()
    return dict(pronunciation.load(pronunciation.file_path()))


class MissingAudio(Exception):
    pass


class _OfflineSpeaker:
    """A speaker that never calls Watson: any call means a cue has no mp3 yet."""

    def __init__(self, voice):
        self.voice = voice

    def wav(self, text):
        raise MissingAudio(f'no cached audio for: "{text[:70]}"')


def voice_name() -> str:
    _, _, settings = _demo_videos()
    return settings.get("DEMO_VOICE", required=True)


def offline_speaker():
    """For --no-voice: a speaker that raises MissingAudio instead of calling Watson."""
    return _OfflineSpeaker(voice_name())


def mp3_name(voice: str, spoken_text: str) -> str:
    """The first 16 hex characters of narrate.Speaker's own wav key, plus .mp3."""
    return hashlib.sha256(f"{voice}|{spoken_text}".encode()).hexdigest()[:16] + ".mp3"


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


def _durations(audio_dir):
    path = Path(audio_dir) / "durations.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _save_durations(audio_dir, durations):
    (Path(audio_dir) / "durations.json").write_text(json.dumps(durations, indent=0, sort_keys=True) + "\n")


def voice_script(script: dict, audio_dir: Path, speaker, shared: dict = None) -> dict:
    """The timeline for script. The script's own pronounce map wins over the shared entries.

    An mp3 that exists with a recorded duration is used as it is: the speaker is not called and
    the file is not touched. The committed mp3s are the persistent audio.
    """
    audio_dir = Path(audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    effective = {**(shared or {}), **script.get("pronounce", {})}
    durations = _durations(audio_dir)
    start = dict(durations)
    timeline = copy.deepcopy(script)
    for step in timeline["steps"]:
        for cue in step["cues"]:
            text = spoken(cue["say"], effective)
            name = mp3_name(getattr(speaker, "voice", ""), text)
            out = audio_dir / name
            if not (out.exists() and name in durations):
                wav = speaker.wav(text)
                if not out.exists():
                    _mp3(wav, out)
                durations[name] = _seconds(wav)
            cue["dur"] = durations[name]
            cue["audio"] = "audio/" + name
    if durations != start:
        _save_durations(audio_dir, durations)
    return timeline


def estimate_script(script: dict, words_per_second: float = 2.5) -> dict:
    """The timeline for script with no audio: each cue lasts as long as its words take to say.

    For the review page, which shows scripts that have not been voiced.
    """
    timeline = copy.deepcopy(script)
    for step in timeline["steps"]:
        for cue in step["cues"]:
            cue["dur"] = round(max(1.0, len(str(cue.get("say", "")).split()) / words_per_second), 2)
            cue["audio"] = ""
    return timeline


def prune_audio(audio_dir: Path, timelines: list) -> list:
    """Delete the mp3s (and their duration entries) in audio_dir that no timeline names; return the paths deleted.

    An empty timelines list deletes every mp3 in the folder.
    """
    used = {Path(c["audio"]).name for t in timelines for s in t["steps"] for c in s["cues"]}
    gone = []
    for mp3 in sorted(Path(audio_dir).glob("*.mp3")):
        if mp3.name not in used:
            mp3.unlink()
            gone.append(mp3)
    durations = _durations(audio_dir)
    kept = {k: d for k, d in durations.items() if k in used}
    if kept != durations:
        _save_durations(audio_dir, kept)
    return gone
