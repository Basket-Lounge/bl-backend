from celery import shared_task

from nba_api.live.nba.endpoints.scoreboard import ScoreBoard
from nba_api.live.nba.endpoints.boxscore import BoxScore
from nba_api.stats.endpoints.scoreboardv2 import ScoreboardV2

from games.models import Game
from games.services import update_live_scores, update_team_statistics

from django.db import transaction, DatabaseError
import logging


logger = logging.getLogger(__name__)

@shared_task
def update_game_datetime():
    games = ScoreBoard().games.get_dict()

    for game in games:
        try:
            existing_game = Game.objects.get(game_id=game['gameId'])
        except Game.DoesNotExist:
            logger.info("Game not found: ", game['gameId'])
            continue
        
        existing_game.game_date_est = game['gameEt']
        existing_game.save()

@shared_task
def update_game_score():
    games = ScoreBoard().games.get_dict()
    
    for each in games:
        try:
            boxscore = BoxScore(game_id=each['gameId']).get_dict()['game']
        except:
            logger.info("Boxscore not found: ", each['gameId'])
            continue

        with transaction.atomic():
            try:
                game = Game.objects.select_for_update(nowait=True).get(game_id=each['gameId'])
            except Game.DoesNotExist:
                logger.info("Game not found: ", each['gameId'])
                continue
            except DatabaseError:
                logger.info("Database error: ", each['gameId'])
                continue

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


def fix_game_score():
    gameDates = [
        '2025-03-10',
        '2025-03-11',
        '2025-03-12',
        '2025-03-13',
        '2025-03-14',
        '2025-03-15',
        '2025-03-16',
        '2025-03-17',
        '2025-03-18',
        '2025-03-19',
        '2025-03-20',
        '2025-03-21',
        '2025-03-22',
        '2025-03-23',
        '2025-03-24',
    ]

    for gameDate in gameDates:
        scoreboard = ScoreboardV2(
            game_date=gameDate,
            league_id='00',
            day_offset=0
        )

        headers = scoreboard.get_dict()['resultSets'][0]['headers']
        games = scoreboard.get_dict()['resultSets'][0]['rowSet']

        scoreboard_data = [dict(zip(headers, game)) for game in games]

        for game in scoreboard_data:
            with transaction.atomic():
                boxscore = BoxScore(game_id=game['GAME_ID']).get_dict()['game']
                print("Updating game: ", game['GAME_ID'])
                game_obj = Game.objects.get(game_id=game['GAME_ID'])

                game_obj.game_status_id = boxscore['gameStatus']
                game_obj.game_status_text = boxscore['gameStatusText']
                game_obj.live_period = boxscore['period']
                game_obj.live_pc_time = boxscore['gameClock']

                game_obj.save()

                hometeam_linescore = boxscore['homeTeam']['periods']
                hometeam_players = boxscore['homeTeam']['players']
                hometeam_statistics = boxscore['homeTeam']['statistics']

                awayteam_linescore = boxscore['awayTeam']['periods']
                awayteam_players = boxscore['awayTeam']['players']
                awayteam_statistics = boxscore['awayTeam']['statistics']

                update_live_scores(
                    game=game_obj,
                    team=game_obj.home_team,
                    linescore=hometeam_linescore,
                    players=hometeam_players,
                    statistics=hometeam_statistics,
                )

                update_live_scores(
                    game=game_obj,
                    team=game_obj.visitor_team,
                    linescore=awayteam_linescore,
                    players=awayteam_players,
                    statistics=awayteam_statistics,
                )


def fix_team_statistics(game_id):
    boxscore = BoxScore(game_id=game_id).get_dict()['game']

    game_obj = Game.objects.get(game_id=game_id)

    hometeam_statistics = boxscore['homeTeam']['statistics']
    awayteam_statistics = boxscore['awayTeam']['statistics']

    with transaction.atomic():
        update_team_statistics(
            game=game_obj,
            team=game_obj.home_team,
            statistics=hometeam_statistics,
        )

        update_team_statistics(
            game=game_obj,
            team=game_obj.visitor_team,
            statistics=awayteam_statistics,
        )