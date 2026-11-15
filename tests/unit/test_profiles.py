import pytest
from pydantic import ValidationError

from spaceapp.platform.config import Settings
from spaceapp.platform.profiles import Profile, adapters_for


def test_default_profile_is_jury(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SPACEAPP_PROFILE", raising=False)
    assert Settings(_env_file=None).profile is Profile.JURY


@pytest.mark.parametrize("value", ["dev1", "dev2", "jury"])
def test_profile_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch, value: str):
    monkeypatch.setenv("SPACEAPP_PROFILE", value)
    assert Settings(_env_file=None).profile.value == value


def test_unknown_profile_is_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPACEAPP_PROFILE", "produccion")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_dev1_uses_whisper_and_ollama():
    a = adapters_for(Profile.DEV1)
    assert (a.speech_to_text, a.knowledge_source, a.text_composer) == (
        "whisper",
        "demo_and_rag",
        "ollama",
    )


def test_dev2_uses_alexa_for_voice_and_it_is_not_autonomous():
    a = adapters_for(Profile.DEV2)
    assert a.speech_to_text == "alexa"
    assert a.autonomous_voice is False


def test_jury_uses_whisper_and_falls_back_when_something_is_missing():
    a = adapters_for(Profile.JURY)
    assert a.speech_to_text == "whisper"
    assert a.knowledge_source == "rag_fallback_demo"
    assert a.text_composer == "ollama_fallback_template"
    assert a.autonomous_voice is True


def test_every_profile_uses_the_simulators_for_sensors_and_ground_link():
    for p in Profile:
        a = adapters_for(p)
        assert (a.sensor_source, a.ground_link) == ("simulator", "simulated")
