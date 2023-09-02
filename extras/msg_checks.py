
import re
from textwrap import dedent


def is_tic_tac_toe(msg: str) -> bool:
    """Checks if the message contains a tic-tac-toe game (that hasn't ended)"""
    # TODO: figure out which mention_regex to use in dragon-log
    # mention_regex = r"<@!*&*[0-9]+>"
    mention_regex = r"\@[a-zA-Z0-9_ ]+"
    user_regex = rf"(X|O|{mention_regex})"
    to_find = dedent(fr"""
        It is now {user_regex}'s turn
        It's a tie!
        {user_regex} won!
        {user_regex}'s turn
        Game has started!, It is {user_regex}'s Turn
        Lobby created!\nJoin here to start playing!
        {user_regex} challenged {user_regex} in tic tac toe!
    """).splitlines()

    regex = "".join(f"({line}|)" for line in to_find)

    find_all = re.findall(regex, msg)
    print(regex)
    print(find_all)

    # filter out empty matches
    total = [
        j for i in find_all 
        for j in i
        if j
    ]

    print(total)
    return len(total) > 0


def main() -> None:
    test_ttt()


def test_ttt() -> None:
    assert True == is_tic_tac_toe("It is now @winter dragon's turn")
    assert True == is_tic_tac_toe("It's a tie!")
    assert True == is_tic_tac_toe("@winter dragon won!")
    assert True == is_tic_tac_toe("@winter dragon's turn")
    assert True == is_tic_tac_toe("Game has started!, It is @winter dragon's Turn")
    assert True == is_tic_tac_toe("Lobby created!\nJoin here to start playing!")
    assert True == is_tic_tac_toe("@winter dragon challenged @winter dragon in tic tac toe!")
    assert False == is_tic_tac_toe("@winter dragon how's your day!?")
    assert False == is_tic_tac_toe("@winter dragon @herogold @winter dragon")


if __name__ == "__main__":
    main()