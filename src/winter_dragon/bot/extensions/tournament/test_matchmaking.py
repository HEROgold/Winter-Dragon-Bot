"""Test and demonstration script for the matchmaking system.

Run this script to test the matchmaking system with example data.
"""

import contextlib

from winter_dragon.bot.extensions.tournament.matchmaking import MatchmakingSystem


def test_matchmaking_system() -> None:
    """Run comprehensive tests of the matchmaking system."""
    # Initialize system
    mm = MatchmakingSystem()

    # Generate example data
    mm.generate_example_data(num_players=12, num_matches=100)

    # Print player statistics
    mm.print_player_stats("League of Legends", limit=12)

    # Print synergy data
    mm.print_synergy_data("League of Legends", limit=15)

    # Print match history
    mm.print_match_history("League of Legends", limit=5)

    # Verify data integrity
    integrity = mm.verify_data_integrity()
    for _key, _value in integrity.items():
        pass

    # Test matchmaking algorithm

    # Test 1: 2v2 matchmaking
    test_players_2v2 = [100001, 100002, 100003, 100004]
    teams_2v2 = mm.create_balanced_teams(
        game_name="League of Legends",
        player_ids=test_players_2v2,
        bracket_format="2v2",
        avoid_synergy=True,
    )

    # Test 2: 3v3 matchmaking
    test_players_3v3 = [100001, 100002, 100003, 100004, 100005, 100006]
    mm.create_balanced_teams(
        game_name="League of Legends",
        player_ids=test_players_3v3,
        bracket_format="3v3",
        avoid_synergy=True,
    )

    # Test 3: 1v1 matchmaking
    test_players_1v1 = [100001, 100002]
    mm.create_balanced_teams(
        game_name="League of Legends",
        player_ids=test_players_1v1,
        bracket_format="1v1",
        avoid_synergy=False,  # Not relevant for 1v1
    )

    # Test 4: Record a new match
    mm.record_match_result(
        game_name="League of Legends",
        teams=teams_2v2,
        winning_team_idx=0,
        bracket_format="2v2",
        individual_scores={
            teams_2v2[0][0]: 300,
            teams_2v2[0][1]: 280,
            teams_2v2[1][0]: 250,
            teams_2v2[1][1]: 240,
        },
        team_scores=[580, 490],
        duration_seconds=1500,
    )

    # Final summary


def test_edge_cases() -> None:
    """Test edge cases and error handling."""
    mm = MatchmakingSystem()

    # Test 1: Invalid bracket format
    with contextlib.suppress(ValueError):
        mm.create_balanced_teams(
            game_name="League of Legends",
            player_ids=[100001, 100002],
            bracket_format="invalid",
        )

    # Test 2: Mismatched player count
    try:
        mm.create_balanced_teams(
            game_name="League of Legends",
            player_ids=[100001, 100002, 100003],  # 3 players for 2v2
            bracket_format="2v2",
        )
    except ValueError:
        pass

    # Test 3: New players (no history)
    try:
        new_player_ids = [999001, 999002, 999003, 999004]

        # Create users
        from winter_dragon.database.tables.user import Users

        for uid in new_player_ids:
            user = mm.session.exec(mm.session.query(Users).where(Users.id == uid)).first()
            if not user:
                user = Users(id=uid)
                user.add(mm.session)
        mm.session.commit()

        mm.create_balanced_teams(
            game_name="League of Legends",
            player_ids=new_player_ids,
            bracket_format="2v2",
        )
    except Exception:
        pass


if __name__ == "__main__":
    # Run main test suite
    test_matchmaking_system()

    # Run edge case tests
    # Uncomment to test edge cases:
    # test_edge_cases()
