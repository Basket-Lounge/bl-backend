from nba_api.stats.endpoints.scoreboardv2 import ScoreboardV2

def get_today_games():
    today_games = ScoreboardV2(
        game_date="2024-10-22",
        league_id="00",
        day_offset=0
    )

    return today_games.get_dict()
