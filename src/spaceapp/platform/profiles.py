"""Runtime profiles and the adapters each one activates (architecture plan, section 12)."""

from dataclasses import dataclass
from enum import StrEnum


class Profile(StrEnum):
    DEV1 = "dev1"
    DEV2 = "dev2"
    JURY = "jury"


@dataclass(frozen=True)
class AdapterSet:
    speech_to_text: str
    knowledge_source: str
    text_composer: str
    autonomous_voice: bool
    sensor_source: str = "simulator"
    ground_link: str = "simulated"


_ADAPTERS = {
    Profile.DEV1: AdapterSet("whisper", "demo_and_rag", "ollama", autonomous_voice=True),
    # Alexa processes voice in the cloud: it is not autonomous and that must be stated.
    Profile.DEV2: AdapterSet("alexa", "demo_and_rag", "ollama", autonomous_voice=False),
    Profile.JURY: AdapterSet(
        "whisper", "rag_fallback_demo", "ollama_fallback_template", autonomous_voice=True
    ),
}


def adapters_for(profile: Profile) -> AdapterSet:
    return _ADAPTERS[profile]
