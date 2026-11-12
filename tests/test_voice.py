import copy
import hashlib
import pytest
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "video"))

import voice  # noqa: E402


class FakeSpeaker:
    """Like narrate.Speaker: a wav cached by its text, a call counted only on a miss."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.calls = 0
        self.texts = []

    def wav(self, text):
        path = self.folder / (hashlib.sha256(text.encode()).hexdigest() + ".wav")
        if not path.exists():
            self.calls += 1
            self.texts.append(text)
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(b"\0\0" * 24000)
        return str(path)


def make(says, pronounce=None):
    s = {"steps": [{"cues": [{"say": t} for t in says]}]}
    if pronounce:
        s["pronounce"] = pronounce
    return s


def setup(tmp_path):
    wavs = tmp_path / "wavs"
    wavs.mkdir()
    audio = tmp_path / "audio"
    return FakeSpeaker(wavs), audio


def cues(tl):
    return [c for st in tl["steps"] for c in st["cues"]]


def test_same_words_one_call_one_mp3(tmp_path):
    sp, audio = setup(tmp_path)
    tl = voice.voice_script(make(["Hello there.", "Hello there.", "Other words."]), audio, sp, {})
    assert sp.calls == 2
    a, b, c = cues(tl)
    assert a["audio"] == b["audio"] != c["audio"]
    assert len(list(audio.glob("*.mp3"))) == 2
    assert a["dur"] == 1.0
    assert a["audio"].startswith("audio/") and a["audio"].endswith(".mp3")
    assert len(Path(a["audio"]).stem) == 16


def test_one_changed_cue_one_new_call(tmp_path):
    sp, audio = setup(tmp_path)
    s = make(["One.", "Two.", "Three."])
    first = voice.voice_script(s, audio, sp, {})
    assert sp.calls == 3
    s2 = copy.deepcopy(s)
    s2["steps"][0]["cues"][1]["say"] = "Twp."
    second = voice.voice_script(s2, audio, sp, {})
    assert sp.calls == 4
    f, g = cues(first), cues(second)
    assert [f[0]["audio"], f[2]["audio"]] == [g[0]["audio"], g[2]["audio"]]
    assert f[1]["audio"] != g[1]["audio"]
    assert s["steps"][0]["cues"][0].get("audio") is None  # the input is not changed


def test_mp3_is_48k_mono(tmp_path):
    sp, audio = setup(tmp_path)
    tl = voice.voice_script(make(["Hello."]), audio, sp, {})
    mp3 = audio / Path(cues(tl)[0]["audio"]).name
    out = subprocess.run(["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "stream=bit_rate,channels",
                          "-of", "default=nw=1", str(mp3)], capture_output=True, text=True, check=True).stdout
    assert "bit_rate=48000" in out and "channels=1" in out


def test_script_pronounce_wins_over_shared(tmp_path):
    sp, audio = setup(tmp_path)
    voice.voice_script(make(["We read the COS bucket."], {"read": "reed"}), audio, sp, {"COS": "C O S", "read": "red"})
    assert sp.texts == ["We reed the C O S bucket."]


def test_prune_deletes_unused_only(tmp_path):
    sp, audio = setup(tmp_path)
    tl = voice.voice_script(make(["Keep me.", "Drop me."]), audio, sp, {})
    tl2 = voice.voice_script(make(["Keep me."]), audio, sp, {})
    gone = voice.prune_audio(audio, [tl2])
    kept = cues(tl2)[0]["audio"]
    dropped = cues(tl)[1]["audio"]
    assert [p.name for p in gone] == [Path(dropped).name]
    assert sorted(p.name for p in audio.glob("*.mp3")) == [Path(kept).name]


def test_mp3_name_is_the_speakers_wav_key(tmp_path, monkeypatch):
    import os
    narrate, _, _ = voice._demo_videos()
    monkeypatch.setattr(narrate, "CACHE", str(tmp_path / "cache"))
    os.makedirs(narrate.CACHE)
    text = "Hello there."
    key = hashlib.sha256(f"en-GB_Test|{text}".encode()).hexdigest()
    Path(narrate.CACHE, key + ".wav").write_bytes(b"")
    real_wav = narrate.Speaker("en-GB_Test").wav(text)
    assert voice.mp3_name("en-GB_Test", text) == Path(real_wav).name[:16] + ".mp3"


class NoCalls:
    voice = ""

    def wav(self, text):
        raise AssertionError("the speaker was called")


def test_existing_mp3_and_duration_are_never_redone(tmp_path):
    sp, audio = setup(tmp_path)
    tl = voice.voice_script(make(["Keep."]), audio, sp, {})
    mp3 = audio / Path(cues(tl)[0]["audio"]).name
    mp3.write_bytes(b"changed")
    again = voice.voice_script(make(["Keep."]), audio, NoCalls(), {})
    assert mp3.read_bytes() == b"changed"
    assert cues(again)[0]["dur"] == 1.0
    assert (audio / "durations.json").is_file()


def test_prune_drops_stale_duration_entries(tmp_path):
    import json
    sp, audio = setup(tmp_path)
    tl = voice.voice_script(make(["Keep me.", "Drop me."]), audio, sp, {})
    tl2 = voice.voice_script(make(["Keep me."]), audio, NoCalls(), {})
    voice.prune_audio(audio, [tl2])
    kept = Path(cues(tl2)[0]["audio"]).name
    assert list(json.loads((audio / "durations.json").read_text())) == [kept]


def test_offline_speaker_names_the_missing_cue(monkeypatch):
    monkeypatch.setattr(voice, "voice_name", lambda: "v")
    with pytest.raises(voice.MissingAudio) as e:
        voice.offline_speaker().wav("Some words")
    assert "Some words" in str(e.value)


def test_voice_script_leaves_the_input_script_unchanged(tmp_path):
    speaker, audio = setup(tmp_path)
    script = make(["One two.", "Three."], pronounce={"x": "y"})
    script["extra"] = {"nested": [1, 2]}
    before = copy.deepcopy(script)
    voice.voice_script(script, audio, speaker)
    assert script == before


def test_ffmpeg_failure_raises(tmp_path, monkeypatch):
    speaker, audio = setup(tmp_path)
    monkeypatch.setattr(voice, "FFMPEG", "false")
    with pytest.raises(subprocess.CalledProcessError):
        voice.voice_script(make(["One."]), audio, speaker)
