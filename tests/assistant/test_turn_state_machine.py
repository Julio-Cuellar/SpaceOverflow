"""Máquina de estados de la intervención (voz o texto): de lo recibido a la respuesta.

Las propiedades importan más que los ejemplos: nada llega a n8n sin confirmar, los estados
terminales no cambian y ningún estado se queda colgado.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from spaceapp.modules.assistant.domain.voice import (
    INITIAL_STATES,
    TERMINAL_STATES,
    TRANSITIONS,
    InvalidTransitionError,
    TurnEvent,
    UtteranceStatus,
    transition,
)

S = UtteranceStatus
E = TurnEvent

HAPPY_PATH_BY_VOICE = [
    (S.RECEIVED, E.TRANSCRIBE, S.TRANSCRIBING),
    (S.TRANSCRIBING, E.TRANSCRIPT_READY, S.TRANSCRIBED),
    (S.TRANSCRIBED, E.CONFIRM, S.CONFIRMED),
    (S.CONFIRMED, E.CONSULT, S.CONSULTING),
    (S.CONSULTING, E.ANSWERED, S.ANSWERED),
]


@pytest.mark.parametrize(("state", "event", "expected"), HAPPY_PATH_BY_VOICE)
def test_the_voice_path_goes_from_received_to_answered(state: S, event: E, expected: S) -> None:
    assert transition(state, event) is expected


def test_the_text_path_skips_the_transcription() -> None:
    assert transition(S.TYPED, E.CONFIRM) is S.CONFIRMED


@pytest.mark.parametrize(
    ("state", "event", "expected"),
    [
        (S.TRANSCRIBING, E.TRANSCRIPT_FAILED, S.NO_TRANSCRIPT),
        (S.NO_TRANSCRIPT, E.CONFIRM, S.CONFIRMED),  # la tripulación escribe lo que quiere preguntar
        (S.TYPED, E.DISCARD, S.DISCARDED),
        (S.TRANSCRIBED, E.DISCARD, S.DISCARDED),
        (S.NO_TRANSCRIPT, E.DISCARD, S.DISCARDED),
        (S.CONSULTING, E.NO_INFO, S.NO_INFO),
        (S.CONSULTING, E.FALLBACK_ANSWERED, S.TEMPLATE_ANSWER),
        (S.CONSULTING, E.FAILED, S.FAILED),
    ],
)
def test_the_branches_for_failure_discard_and_fallback(state: S, event: E, expected: S) -> None:
    assert transition(state, event) is expected


def test_every_pair_not_in_the_table_is_rejected() -> None:
    for state in S:
        for event in E:
            if (state, event) in TRANSITIONS:
                continue
            with pytest.raises(InvalidTransitionError):
                transition(state, event)


def test_terminal_states_accept_no_event_at_all() -> None:
    for state in TERMINAL_STATES:
        for event in E:
            with pytest.raises(InvalidTransitionError):
                transition(state, event)


def test_the_terminal_states_are_exactly_the_five_that_close_a_turn() -> None:
    assert {
        S.ANSWERED,
        S.NO_INFO,
        S.TEMPLATE_ANSWER,
        S.FAILED,
        S.DISCARDED,
    } == TERMINAL_STATES


def test_only_a_confirmed_turn_can_start_the_consultation() -> None:
    sources = {src for (src, event), dst in TRANSITIONS.items() if dst is S.CONSULTING}

    assert sources == {S.CONFIRMED}


def test_only_the_crew_can_confirm_and_only_from_a_text_that_is_ready() -> None:
    sources = {src for (src, event), dst in TRANSITIONS.items() if dst is S.CONFIRMED}

    assert sources == {S.TYPED, S.TRANSCRIBED, S.NO_TRANSCRIPT}
    assert {event for (_, event), dst in TRANSITIONS.items() if dst is S.CONFIRMED} == {E.CONFIRM}


def test_a_turn_starts_as_received_audio_or_typed_text() -> None:
    assert {S.RECEIVED, S.TYPED} == INITIAL_STATES


def test_no_state_is_a_dead_end_and_every_state_can_reach_a_terminal_one() -> None:
    def reachable(start: S) -> set[S]:
        seen = {start}
        frontier = [start]
        while frontier:
            current = frontier.pop()
            for (src, _), dst in TRANSITIONS.items():
                if src is current and dst not in seen:
                    seen.add(dst)
                    frontier.append(dst)
        return seen

    for state in S:
        assert reachable(state) & TERMINAL_STATES or state in TERMINAL_STATES, state


def test_every_state_is_reachable_from_a_starting_state() -> None:
    seen = set(INITIAL_STATES)
    frontier = list(INITIAL_STATES)
    while frontier:
        current = frontier.pop()
        for (src, _), dst in TRANSITIONS.items():
            if src is current and dst not in seen:
                seen.add(dst)
                frontier.append(dst)

    assert seen == set(S)


@given(st.lists(st.sampled_from(list(E)), max_size=30), st.sampled_from(sorted(INITIAL_STATES)))
def test_a_random_sequence_of_events_never_breaks_the_rules(events: list[E], start: S) -> None:
    state = start
    history = [state]
    for event in events:
        try:
            state = transition(state, event)
        except InvalidTransitionError:
            # Rechazar un evento deja el estado como estaba: nunca se salta un paso.
            assert (state, event) not in TRANSITIONS
            continue
        history.append(state)

    # Nunca se consulta sin haber confirmado antes.
    if S.CONSULTING in history:
        assert S.CONFIRMED in history[: history.index(S.CONSULTING)]
    # Un estado terminal, una vez alcanzado, es el último.
    for index, past in enumerate(history):
        if past in TERMINAL_STATES:
            assert index == len(history) - 1
