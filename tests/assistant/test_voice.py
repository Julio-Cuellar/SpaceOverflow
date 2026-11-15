"""Voice with confirmation: transcribing is not acting. Nothing is asked without confirming."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from spaceapp.modules.assistant.adapters.outbound.audio_store import LocalAudioStore
from spaceapp.modules.assistant.adapters.outbound.memory import (
    InMemoryConversations,
    InMemoryUtterances,
    ListPublisher,
)
from spaceapp.modules.assistant.adapters.outbound.null_llm import NullLlmGateway
from spaceapp.modules.assistant.adapters.outbound.null_stt import NullSpeechToText
from spaceapp.modules.assistant.application.ask import AskAssistant, AskOutcome
from spaceapp.modules.assistant.application.voice import (
    AlreadyConfirmedError,
    ConfirmUtterance,
    SubmitAudio,
    UnknownUtteranceError,
    UnsupportedAudioError,
)
from spaceapp.modules.assistant.domain.voice import (
    InvalidTransitionError,
    Transcript,
    UtteranceStatus,
)
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.facade import KnowledgeQuery

DEMO_CATALOG = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "demo_catalog.json"
CONVERSATION = uuid.uuid4()
AUDIO = b"RIFF....WAVEfake-audio"


class FakeStt:
    available = True

    def __init__(self, text: str = "why do I have a headache", fail: bool = False) -> None:
        self._text = text
        self._fail = fail
        self.calls = 0

    def transcribe(self, audio: bytes, content_type: str) -> Transcript | None:
        self.calls += 1
        if self._fail:
            raise RuntimeError("model down")
        return Transcript(text=self._text, confidence=0.8, language="es")


class Rig:
    def __init__(self, tmp_path: Path, stt: object | None = None) -> None:
        self.conversations = InMemoryConversations()
        self.publisher = ListPublisher()
        self.utterances = InMemoryUtterances()
        self.ask = AskAssistant(
            passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
            llm=NullLlmGateway(),
            conversations=self.conversations,
            alerts=_NoAlerts(),
            publisher=self.publisher,
        )
        self.stt = stt if stt is not None else FakeStt()
        self.submit = SubmitAudio(
            stt=self.stt,  # type: ignore[arg-type]
            store=LocalAudioStore(tmp_path / "audio"),
            utterances=self.utterances,
        )
        self.confirm = ConfirmUtterance(utterances=self.utterances, ask=self.ask)


class _NoAlerts:
    def titles(self) -> list[str]:
        return []


def test_submitting_audio_answers_at_once_without_transcribing_yet(tmp_path: Path) -> None:
    rig = Rig(tmp_path)

    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")

    assert rig.utterances.get(utterance_id).status is UtteranceStatus.RECEIVED
    assert rig.stt.calls == 0  # type: ignore[attr-defined]


def test_the_audio_is_stored_under_the_utterance_id(tmp_path: Path) -> None:
    rig = Rig(tmp_path)

    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/webm")

    stored = rig.utterances.get(utterance_id).audio_path
    assert stored is not None
    assert Path(stored).read_bytes() == AUDIO
    assert Path(stored).name == f"{utterance_id}.webm"


@pytest.mark.parametrize("content_type", ["audio/mpeg", "text/plain", ""])
def test_only_webm_and_wav_are_accepted(tmp_path: Path, content_type: str) -> None:
    with pytest.raises(UnsupportedAudioError):
        Rig(tmp_path).submit.submit(CONVERSATION, AUDIO, content_type)


def test_empty_audio_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedAudioError):
        Rig(tmp_path).submit.submit(CONVERSATION, b"", "audio/wav")


def test_transcribing_leaves_an_editable_text_waiting_for_confirmation(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")

    utterance = rig.submit.transcribe(utterance_id)

    assert utterance.status is UtteranceStatus.TRANSCRIBED
    assert utterance.text == "why do I have a headache"
    assert utterance.confidence == 0.8


@pytest.mark.parametrize("stt", [None, FakeStt(fail=True), NullSpeechToText()])
def test_the_audio_is_deleted_once_it_has_been_transcribed_or_has_failed(
    tmp_path: Path, stt: object | None
) -> None:
    rig = Rig(tmp_path, stt)
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/webm")
    stored = Path(rig.utterances.get(utterance_id).audio_path or "")
    assert stored.exists()

    utterance = rig.submit.transcribe(utterance_id)

    assert (
        not stored.exists()
    )  # these are recordings of people: they are not kept longer than necessary
    assert utterance.audio_path is None
    assert rig.utterances.get(utterance_id).audio_path is None


def test_nothing_is_asked_or_answered_until_the_crew_confirms(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")

    rig.submit.transcribe(utterance_id)

    assert rig.conversations.messages(CONVERSATION) == []
    assert rig.publisher.events == []


def test_confirming_asks_the_assistant_with_the_text_the_crew_edited(tmp_path: Path) -> None:
    rig = Rig(tmp_path, FakeStt(text="por que me duele la caveza"))
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")
    rig.submit.transcribe(utterance_id)

    result = rig.confirm.confirm(utterance_id, "Why do I have a headache?")

    assert result.outcome is AskOutcome.ANSWERED
    [question, _answer] = rig.conversations.messages(CONVERSATION)
    assert question.text == "Why do I have a headache?"
    assert rig.utterances.get(utterance_id).status is UtteranceStatus.ANSWERED


def test_an_utterance_cannot_be_confirmed_twice(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")
    rig.submit.transcribe(utterance_id)
    rig.confirm.confirm(utterance_id, "Why do I have a headache?")

    with pytest.raises(AlreadyConfirmedError):
        rig.confirm.confirm(utterance_id, "Why do I have a headache?")
    assert len(rig.publisher.events) == 1


def test_confirming_an_unknown_utterance_fails(tmp_path: Path) -> None:
    with pytest.raises(UnknownUtteranceError):
        Rig(tmp_path).confirm.confirm(uuid.uuid4(), "hola")


def test_an_empty_confirmation_asks_nothing_and_leaves_it_pending(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")
    rig.submit.transcribe(utterance_id)

    result = rig.confirm.confirm(utterance_id, "   ")

    assert result.outcome is AskOutcome.EMPTY_QUESTION
    assert rig.utterances.get(utterance_id).status is UtteranceStatus.TRANSCRIBED
    assert rig.publisher.events == []


def test_without_a_speech_model_the_crew_can_still_type_the_question(tmp_path: Path) -> None:
    rig = Rig(tmp_path, NullSpeechToText())
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")

    utterance = rig.submit.transcribe(utterance_id)
    result = rig.confirm.confirm(utterance_id, "Why do I have a headache?")

    assert utterance.status is UtteranceStatus.NO_TRANSCRIPT
    assert "text" in (utterance.reason or "")
    assert result.outcome is AskOutcome.ANSWERED


def test_a_failing_speech_model_does_not_break_the_flow(tmp_path: Path) -> None:
    rig = Rig(tmp_path, FakeStt(fail=True))
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")

    utterance = rig.submit.transcribe(utterance_id)

    assert utterance.status is UtteranceStatus.NO_TRANSCRIPT
    assert utterance.text == ""


def test_audio_without_speech_gives_no_transcript(tmp_path: Path) -> None:
    rig = Rig(tmp_path, FakeStt(text="   "))
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")

    utterance = rig.submit.transcribe(utterance_id)

    assert utterance.status is UtteranceStatus.NO_TRANSCRIPT


def test_a_question_without_a_passage_closes_the_turn_as_no_info(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")
    rig.submit.transcribe(utterance_id)

    result = rig.confirm.confirm(utterance_id, "What is the capital of France?")

    assert result.outcome is AskOutcome.NO_INFO
    assert rig.utterances.get(utterance_id).status is UtteranceStatus.NO_INFO


def test_a_typed_question_goes_through_the_same_state_machine(tmp_path: Path) -> None:
    rig = Rig(tmp_path)

    result = rig.confirm.confirm_text(CONVERSATION, "Why do I have a headache?")

    assert result.outcome is AskOutcome.ANSWERED
    [only] = rig.utterances.all()
    assert only.status is UtteranceStatus.ANSWERED
    assert only.text == "Why do I have a headache?"


def test_an_empty_typed_question_creates_no_turn(tmp_path: Path) -> None:
    rig = Rig(tmp_path)

    result = rig.confirm.confirm_text(CONVERSATION, "   ")

    assert result.outcome is AskOutcome.EMPTY_QUESTION
    assert rig.utterances.all() == []


def test_the_crew_can_discard_a_transcript_and_then_cannot_confirm_it(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")
    rig.submit.transcribe(utterance_id)

    rig.confirm.discard(utterance_id)

    assert rig.utterances.get(utterance_id).status is UtteranceStatus.DISCARDED
    with pytest.raises(InvalidTransitionError):
        rig.confirm.confirm(utterance_id, "Why do I have a headache?")
    assert rig.publisher.events == []


def test_an_answered_turn_cannot_be_discarded(tmp_path: Path) -> None:
    rig = Rig(tmp_path)
    utterance_id = rig.submit.submit(CONVERSATION, AUDIO, "audio/wav")
    rig.submit.transcribe(utterance_id)
    rig.confirm.confirm(utterance_id, "Why do I have a headache?")

    with pytest.raises(InvalidTransitionError):
        rig.confirm.discard(utterance_id)


def _rig_with_orchestrator(tmp_path: Path, *, fail: bool, search: bool = True):  # type: ignore[no-untyped-def]
    from test_ask_with_orchestrator import FakeAgent, FakeAlerts

    from spaceapp.modules.assistant.application.retrieval_log import RetrievalLog

    rig = Rig(tmp_path)
    log = RetrievalLog()
    rig.ask = AskAssistant(
        passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
        llm=NullLlmGateway(),
        conversations=rig.conversations,
        alerts=FakeAlerts(),
        publisher=rig.publisher,
        orchestrator=FakeAgent(log, fail=fail, search=search),
        retrievals=log,
    )
    rig.confirm = ConfirmUtterance(utterances=rig.utterances, ask=rig.ask)
    return rig


def test_an_answer_by_the_orchestrator_closes_the_turn_as_answered(tmp_path: Path) -> None:
    rig = _rig_with_orchestrator(tmp_path, fail=False)

    rig.confirm.confirm_text(CONVERSATION, "Why do I have a headache?")

    [turn] = rig.utterances.all()
    assert turn.status is UtteranceStatus.ANSWERED


def test_a_failing_orchestrator_closes_the_turn_as_a_template_answer(tmp_path: Path) -> None:
    rig = _rig_with_orchestrator(tmp_path, fail=True)

    result = rig.confirm.confirm_text(CONVERSATION, "Why do I have a headache?")

    assert result.outcome is AskOutcome.ANSWERED
    [turn] = rig.utterances.all()
    assert turn.status is UtteranceStatus.TEMPLATE_ANSWER


def test_an_error_while_consulting_leaves_the_turn_failed_and_is_not_hidden(tmp_path: Path) -> None:
    rig = Rig(tmp_path)

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("the index is missing")

    rig.ask = boom  # type: ignore[assignment]
    rig.confirm = ConfirmUtterance(utterances=rig.utterances, ask=rig.ask)

    with pytest.raises(RuntimeError, match="the index is missing"):
        rig.confirm.confirm_text(CONVERSATION, "Why do I have a headache?")

    [turn] = rig.utterances.all()
    assert turn.status is UtteranceStatus.FAILED
