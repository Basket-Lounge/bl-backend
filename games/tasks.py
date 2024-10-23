from celery import shared_task

from nba_api.live.nba.endpoints.scoreboard import ScoreBoard
from nba_api.live.nba.endpoints.boxscore import BoxScore

from games.models import Game
from games.services import update_live_scores


@shared_task
def update_game_score():
    games = ScoreBoard().games.get_dict()
    
    for each in games:
        boxscore = BoxScore(game_id=each['gameId']).get_dict()['game']

        game = Game.objects.get(game_id=each['gameId'])
        ## if the game is over, skip
        if game.game_status_id == 3:
            continue

        game.game_status_id = boxscore['gameStatus']
        game.game_status_text = boxscore['gameStatusText']
        game.live_period = boxscore['period']
        game.live_pc_time = boxscore['gameClock']

        game.save()

        hometeam_linescore = boxscore['homeTeam']['periods']
        hometeam_players = boxscore['homeTeam']['players']
        hometeam_statistics = boxscore['homeTeam']['statistics']

        awayteam_linescore = boxscore['awayTeam']['periods']
        awayteam_players = boxscore['awayTeam']['players']
        awayteam_statistics = boxscore['awayTeam']['statistics']

        update_live_scores(
            game=game,
            team=game.home_team,
            linescore=hometeam_linescore,
            players=hometeam_players,
            statistics=hometeam_statistics,
        ) 

        update_live_scores(
            game=game,
            team=game.visitor_team,
            linescore=awayteam_linescore,
            players=awayteam_players,
            statistics=awayteam_statistics,
        )