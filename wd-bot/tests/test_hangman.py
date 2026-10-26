"""Unit tests: hangman rules, and the /hangman cog's button, modal and message updates (no network)."""

import re
from random import Random
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive, owned_by
from wd_discord.resources.user import User
from wd_discord.testing import user_json
from wd_errors import Refused

from winter_dragon.cogs.hangman import service
from winter_dragon.cogs.hangman.cards import drawing, game_message
from winter_dragon.cogs.hangman.cog import Hangman
from winter_dragon.cogs.hangman.models import (
    MAX_WRONG_GUESSES,
    HangmanGame,
    HangmanParticipant,
    HangmanStatus,
)
from winter_dragon.cogs.hangman.service import Guess


if TYPE_CHECKING:
    from conftest import ComponentInteractionFactory, InteractionFactory, ModalSubmitFactory
    from sqlalchemy import Engine
    from wd_discord.testing import RecordingClient


GUILD_ID = 1
CHANNEL_ID = 20
ALICE, BOB = 3, 4
"""Alice is the default invoking user of the interaction fixtures."""


def _game(session: Session, word: str = "cat", channel_id: int = CHANNEL_ID) -> HangmanGame:
    game = HangmanGame(guild_id=GUILD_ID, channel_id=channel_id, word=word)
    session.add(game)
    session.commit()
    session.refresh(game)
    return game


def _refused(message: str) -> pytest.RaisesExc[Refused]:
    return pytest.raises(Refused, match=re.escape(message))


def _cog(engine: Engine, client: RecordingClient) -> Hangman:
    cog = detached_cog(Hangman, engine=engine, client=client)
    cog.rng = Random(0)
    return cog


def _participants(session: Session, game: HangmanGame) -> list[int]:
    return service.participants_of(session, game)


def test_the_bundled_word_list_has_plain_lowercase_words() -> None:
    words = service.load_words()
    assert len(words) > 100
    assert all(word.isalpha() and word.islower() for word in words)


def test_a_game_is_won_by_guessing_every_letter_and_credits_each_participant(engine: Engine) -> None:
    with Session(engine) as session:
        game = _game(session, "cat")
        assert service.guess(session, game, ALICE, "c") is Guess.CORRECT_LETTER
        assert service.guess(session, game, BOB, "z") is Guess.WRONG_LETTER
        service.guess(session, game, BOB, "a")
        assert game.status is HangmanStatus.ACTIVE
        service.guess(session, game, ALICE, "t")
        session.commit()
        assert game.status is HangmanStatus.WON
        assert game.finished_at is not None
        assert game.wrong_letters == "z"
        assert sorted(_participants(session, game)) == [ALICE, BOB]


def test_a_member_with_only_wrong_guesses_is_not_a_participant(engine: Engine) -> None:
    with Session(engine) as session:
        game = _game(session, "cat")
        service.guess(session, game, BOB, "z")
        service.guess(session, game, ALICE, "cat")
        session.commit()
        assert _participants(session, game) == [ALICE]


def test_a_game_is_won_by_guessing_the_word(engine: Engine) -> None:
    with Session(engine) as session:
        game = _game(session, "cat")
        service.guess(session, game, BOB, "c")
        assert service.guess(session, game, ALICE, " CAT ") is Guess.CORRECT_WORD
        session.commit()
        assert game.status is HangmanStatus.WON
        assert game.masked == "c a t"
        assert sorted(_participants(session, game)) == [ALICE, BOB]


def test_a_wrong_word_costs_one_life_and_is_stored(engine: Engine) -> None:
    with Session(engine) as session:
        game = _game(session, "cat")
        assert service.guess(session, game, ALICE, "dog") is Guess.WRONG_WORD
        assert (game.wrong_count, game.wrong_word_list, game.status) == (1, ["dog"], HangmanStatus.ACTIVE)
        with _refused("already guessed"):
            service.guess(session, game, ALICE, "dog")
        assert game.wrong_count == 1


def test_a_game_is_lost_after_the_allowed_wrong_guesses(engine: Engine) -> None:
    wrong = list("zxqjkvwyfb")
    assert len(wrong) == MAX_WRONG_GUESSES
    with Session(engine) as session:
        game = _game(session, "cat")
        for letter in wrong[:-1]:
            service.guess(session, game, ALICE, letter)
        assert game.status is HangmanStatus.ACTIVE
        service.guess(session, game, BOB, wrong[-1])
        session.commit()
        assert game.status is HangmanStatus.LOST
        assert game.wrong_letters == "".join(wrong)
        assert _participants(session, game) == []
        with _refused("over"):
            service.guess(session, game, ALICE, "c")


def test_a_repeated_letter_refuses_and_costs_no_life(engine: Engine) -> None:
    with Session(engine) as session:
        game = _game(session, "cat")
        service.guess(session, game, ALICE, "z")
        with _refused("already guessed"):
            service.guess(session, game, BOB, "z")
        service.guess(session, game, ALICE, "c")
        with _refused("already guessed"):
            service.guess(session, game, BOB, "C")
        assert game.wrong_count == 1


@pytest.mark.parametrize("text", ["", "   ", "3", "c4t", "two words", "!"])
def test_anything_but_a_letter_or_a_word_is_refused(engine: Engine, text: str) -> None:
    with Session(engine) as session:
        game = _game(session)
        with _refused("Guess one letter, or the whole word"):
            service.guess(session, game, ALICE, text)
        assert game.letters == ""


def test_the_message_shows_the_state_and_the_final_result(engine: Engine) -> None:
    with Session(engine) as session:
        game = _game(session, "cat")
        service.guess(session, game, ALICE, "c")
        service.guess(session, game, ALICE, "z")
        text = game_message(game)
        assert "`c _ _`" in text
        assert "Wrong: z" in text
        assert "Lives left: 9" in text
        service.guess(session, game, ALICE, "cat")
        assert "**You won!**" in game_message(game, [ALICE])
        assert "<@3>" in game_message(game, [ALICE])
    assert drawing(0) != drawing(10)


async def test_the_command_stores_a_game_and_posts_it_with_a_guess_button(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    await Hangman.hangman.invoke(
        _cog(engine, discord_client),
        make_interaction("hangman", guild_id=GUILD_ID, channel_id=CHANNEL_ID),
        [],
    )

    with Session(engine) as session:
        game = session.exec(alive(HangmanGame)).one()
    assert (game.guild_id, game.channel_id, game.status) == (GUILD_ID, CHANNEL_ID, HangmanStatus.ACTIVE)
    data = discord_client.interaction_responses()[0]["data"]
    assert f"`{' '.join('_' * len(game.word))}`" in data["content"]
    (button,) = data["components"][0]["components"]
    assert button["custom_id"] == f"hangman-guess:{game.id}"


async def test_the_guess_button_opens_the_modal(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        game_id = _game(session).id

    await Hangman.guess_button.invoke(
        _cog(engine, discord_client),
        make_component_interaction(f"hangman-guess:{game_id}", guild_id=GUILD_ID),
        [str(game_id)],
    )

    response = discord_client.interaction_responses()[0]
    assert response["type"] == 9
    assert response["data"]["custom_id"] == f"hangman-guess:{game_id}"
    assert response["data"]["components"][0]["component"]["custom_id"] == "guess"


async def test_a_submitted_letter_updates_the_message(
    engine: Engine,
    make_modal_submit: ModalSubmitFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        game_id = _game(session, "cat").id

    submit = make_modal_submit(f"hangman-guess:{game_id}", {"guess": "c"}, guild_id=GUILD_ID)
    await Hangman.guess_modal.invoke(_cog(engine, discord_client), submit, [str(game_id)])

    response = discord_client.interaction_responses()[0]
    assert response["type"] == 7
    assert "`c _ _`" in response["data"]["content"]
    with Session(engine) as session:
        assert session.exec(alive(HangmanParticipant)).one().user_id == ALICE


async def test_a_refused_guess_changes_nothing(
    engine: Engine,
    make_modal_submit: ModalSubmitFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        game_id = _game(session, "cat").id

    submit = make_modal_submit(f"hangman-guess:{game_id}", {"guess": "4"}, guild_id=GUILD_ID)
    handled = await Hangman.guess_modal.invoke(_cog(engine, discord_client), submit, [str(game_id)])

    assert handled
    response = discord_client.interaction_responses()[0]
    assert response["data"]["flags"] == 64
    assert "Use letters only" in response["data"]["content"]
    with Session(engine) as session:
        assert session.get(HangmanGame, game_id).letters == ""  # pyright: ignore[reportOptionalMemberAccess]


async def test_the_final_guess_ends_the_game_and_removes_the_button(
    engine: Engine,
    make_modal_submit: ModalSubmitFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        game_id = _game(session, "cat").id

    submit = make_modal_submit(f"hangman-guess:{game_id}", {"guess": "cat"}, guild_id=GUILD_ID)
    await Hangman.guess_modal.invoke(_cog(engine, discord_client), submit, [str(game_id)])

    data = discord_client.interaction_responses()[0]["data"]
    assert "**You won!**" in data["content"]
    assert data["components"] == []
    with Session(engine) as session:
        assert session.get(HangmanGame, game_id).status is HangmanStatus.WON  # pyright: ignore[reportOptionalMemberAccess]


async def test_games_in_one_channel_do_not_interfere(
    engine: Engine,
    make_modal_submit: ModalSubmitFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        first, second = _game(session, "cat").id, _game(session, "dog").id
    cog = _cog(engine, discord_client)
    bob = User.model_validate(user_json(id="4", username="bob"))

    for game_id, guess, user in ((first, "c", None), (second, "z", bob), (first, "q", bob), (second, "dog", None)):
        kwargs = {} if user is None else {"user": user}
        submit = make_modal_submit(f"hangman-guess:{game_id}", {"guess": guess}, guild_id=GUILD_ID, **kwargs)
        await Hangman.guess_modal.invoke(cog, submit, [str(game_id)])

    with Session(engine) as session:
        one, two = session.get(HangmanGame, first), session.get(HangmanGame, second)
        assert one is not None
        assert two is not None
        assert (one.letters, one.status, one.wrong_letters) == ("cq", HangmanStatus.ACTIVE, "q")
        assert (two.letters, two.status, two.wrong_letters) == ("zdog", HangmanStatus.WON, "z")
        assert _participants(session, one) == [ALICE]
        assert _participants(session, two) == [ALICE]


async def test_a_game_that_is_over_cannot_be_guessed_at(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        game = _game(session)
        game.status = HangmanStatus.LOST
        session.add(game)
        session.commit()
        game_id = game.id

    await Hangman.guess_button.invoke(
        _cog(engine, discord_client),
        make_component_interaction(f"hangman-guess:{game_id}", guild_id=GUILD_ID),
        [str(game_id)],
    )

    assert "over" in discord_client.interaction_responses()[0]["data"]["content"]


def test_participants_are_owned_by_their_member(engine: Engine) -> None:
    with Session(engine) as session:
        game = _game(session, "cat")
        service.guess(session, game, ALICE, "c")
        service.guess(session, game, BOB, "a")
        session.commit()
        assert [row.user_id for row in session.exec(owned_by(HangmanParticipant, member=ALICE))] == [ALICE]
        assert len(session.exec(owned_by(HangmanParticipant, guild=GUILD_ID)).all()) == 2


def test_a_participants_games_show_on_their_data_page(engine: Engine) -> None:
    from winter_dragon.web.records import member_records  # noqa: PLC0415

    with Session(engine) as session:
        game = _game(session, "cat")
        service.guess(session, game, ALICE, "c")
        service.guess(session, game, BOB, "z")
        session.commit()

    assert [(record.model, record.count) for record in member_records(engine, ALICE)] == [(HangmanParticipant, 1)]
    assert list(member_records(engine, BOB)) == []
