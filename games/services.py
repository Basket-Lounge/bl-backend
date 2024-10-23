from datetime import datetime
import pytz

from games.models import Game, LineScore, TeamStatistics

from django.db.models import Prefetch

from players.models import Player, PlayerStatistics
from teams.models import TeamName


def get_today_games():
    ## get today's date in UTC and then convert back to EST
    date : datetime = datetime.now(pytz.utc)

    games = Game.objects.filter(
        game_date_est__month=date.month, 
        game_date_est__day__in=[date.day - 2, date.day - 1, date.day, date.day + 1, date.day + 2]
    ).select_related(
        'home_team', 
        'visitor_team'
    ).prefetch_related(
        Prefetch(
            'home_team__teamname_set',
            queryset=TeamName.objects.select_related('language').all()
        ),
        Prefetch(
            'visitor_team__teamname_set',
            queryset=TeamName.objects.select_related('language').all()
        ),
    ).order_by(
        'game_sequence'
    )

    linescores = LineScore.objects.filter(
        game__in=games
    ).select_related(
        'game',
        'team'
    ).order_by(
        'game__game_date_est',
        'game__game_sequence'
    )

    return games, linescores

def combine_games_and_linescores(games, linescores):
    ## create a dictionary of games with linescores
    for linescore in linescores:
        for game in games:
            if game['game_id'] == linescore['game']['game_id']:
                linescore_copy = linescore.copy()
                linescore_copy.pop('game')
                linescore_copy.pop('team')

                if linescore['team']['id'] == game['home_team']['id']:
                    game['home_team']['linescore'] = linescore_copy
                else:
                    game['visitor_team']['linescore'] = linescore_copy

    return games

def combine_game_and_linescores(game, linescores):
    ## create a dictionary of games with linescores
    for linescore in linescores:
        if game['game_id'] == linescore['game']['game_id']:
            linescore_copy = linescore.copy()
            linescore_copy.pop('game')
            linescore_copy.pop('team')

            if linescore['team']['id'] == game['home_team']['id']:
                game['home_team']['linescore'] = linescore_copy
            else:
                game['visitor_team']['linescore'] = linescore_copy

    return game

def update_live_scores(
    game,
    team,
    linescore,
    players,
    statistics
):
    team_linescore = LineScore.objects.get(game=game, team=team)
    for index in range(len(linescore)):
        if index == 0:
            team_linescore.pts_qtr1 = linescore[index]['score']
        elif index == 1:
            team_linescore.pts_qtr2 = linescore[index]['score']
        elif index == 2:
            team_linescore.pts_qtr3 = linescore[index]['score']
        elif index == 3:
            team_linescore.pts_qtr4 = linescore[index]['score']
        elif index == 4:
            team_linescore.pts_ot1 = linescore[index]['score']
        elif index == 5:
            team_linescore.pts_ot2 = linescore[index]['score']
        elif index == 6:
            team_linescore.pts_ot3 = linescore[index]['score']
        elif index == 7:
            team_linescore.pts_ot4 = linescore[index]['score']
        elif index == 8:
            team_linescore.pts_ot5 = linescore[index]['score']
        elif index == 9:
            team_linescore.pts_ot6 = linescore[index]['score']
        elif index == 10:
            team_linescore.pts_ot7 = linescore[index]['score']
        elif index == 11:
            team_linescore.pts_ot8 = linescore[index]['score']
        elif index == 12:
            team_linescore.pts_ot9 = linescore[index]['score']
        elif index == 13:
            team_linescore.pts_ot10 = linescore[index]['score']
    
    team_linescore.save()

    team_statistics, created = TeamStatistics.objects.update_or_create(
        team=team,
        game=game,
        defaults={
            'assists': statistics['assists'],
            'assists_turnover_ratio': statistics['assistsTurnoverRatio'],
            'bench_points': statistics['benchPoints'],
            'biggest_lead': statistics['biggestLead'],
            'biggest_lead_score': statistics['biggestLeadScore'],
            'biggest_scoring_run': statistics['biggestScoringRun'],
            'biggest_scoring_run_score': statistics['biggestScoringRunScore'],
            'blocks': statistics['blocks'],
            'blocks_received': statistics['blocksReceived'],
            'fast_break_points_attempted': statistics['fastBreakPointsAttempted'],
            'fast_break_points_made': statistics['fastBreakPointsMade'],
            'fast_break_points_percentage': statistics['fastBreakPointsPercentage'],
            'field_goals_attempted': statistics['fieldGoalsAttempted'],
            'field_goals_effective_adjusted': statistics['fieldGoalsEffectiveAdjusted'],
            'field_goals_made': statistics['fieldGoalsMade'],
            'field_goals_percentage': statistics['fieldGoalsPercentage'],
            'fouls_offensive': statistics['foulsOffensive'],
            'fouls_drawn': statistics['foulsDrawn'],
            'fouls_personal': statistics['foulsPersonal'],
            'fouls_team': statistics['foulsTeam'],
            'fouls_technical': statistics['foulsTechnical'],
            'fouls_team_technical': statistics['foulsTeamTechnical'],
            'free_throws_attempted': statistics['freeThrowsAttempted'],
            'free_throws_made': statistics['freeThrowsMade'],
            'free_throws_percentage': statistics['freeThrowsPercentage'],
            'lead_changes': statistics['leadChanges'],
            'minutes': statistics['minutes'],
            'points': statistics['points'],
            'points_against': statistics['pointsAgainst'],
            'points_fast_break': statistics['pointsFastBreak'],
            'points_from_turnovers': statistics['pointsFromTurnovers'],
            'points_in_the_paint': statistics['pointsInThePaint'],
            'points_in_the_paint_attempted': statistics['pointsInThePaintAttempted'],
            'points_in_the_paint_made': statistics['pointsInThePaintMade'],
            'points_in_the_paint_percentage': statistics['pointsInThePaintPercentage'],
            'points_second_chance': statistics['pointsSecondChance'],
            'rebounds_defensive': statistics['reboundsDefensive'],
            'rebounds_offensive': statistics['reboundsOffensive'],
            'rebounds_personal': statistics['reboundsPersonal'],
            'rebounds_team': statistics['reboundsTeam'],
            'rebounds_team_defensive': statistics['reboundsTeamDefensive'],
            'rebounds_team_offensive': statistics['reboundsTeamOffensive'],
            'rebounds_total': statistics['reboundsTotal'],
            'second_chance_points_attempted': statistics['secondChancePointsAttempted'],
            'second_chance_points_made': statistics['secondChancePointsMade'],
            'second_chance_points_percentage': statistics['secondChancePointsPercentage'],
            'steals': statistics['steals'],
            'three_pointers_attempted': statistics['threePointersAttempted'],
            'three_pointers_made': statistics['threePointersMade'],
            'three_pointers_percentage': statistics['threePointersPercentage'],
            'time_leading': statistics['timeLeading'],
            'times_tied': statistics['timesTied'],
            'true_shooting_attempts': statistics['trueShootingAttempts'],
            'true_shooting_percentage': statistics['trueShootingPercentage'],
            'turnovers': statistics['turnovers'],
            'turnovers_team': statistics['turnoversTeam'],
            'turnovers_total': statistics['turnoversTotal'],
            'two_pointers_attempted': statistics['twoPointersAttempted'],
            'two_pointers_made': statistics['twoPointersMade'],
            'two_pointers_percentage': statistics['twoPointersPercentage']
        }
    )

    for player in players:
        print(player)
        player_stat, created = PlayerStatistics.objects.update_or_create(
            player=Player.objects.get(id=player['personId']),
            game=game,
            team=game.home_team,
            defaults={
                'status': player['status'],
                'order': player['order'],
                'position': player.get('position', None),
                'starter': player['starter'],
                'assists': player['statistics']['assists'],
                'blocks': player['statistics']['blocks'],
                'blocks_received': player['statistics']['blocksReceived'],
                'field_goals_attempted': player['statistics']['fieldGoalsAttempted'],
                'field_goals_made': player['statistics']['fieldGoalsMade'],
                'field_goals_percentage': player['statistics']['fieldGoalsPercentage'],
                'fouls_offensive': player['statistics']['foulsOffensive'],
                'fouls_drawn': player['statistics']['foulsDrawn'],
                'fouls_personal': player['statistics']['foulsPersonal'],
                'fouls_technical': player['statistics']['foulsTechnical'],
                'free_throws_attempted': player['statistics']['freeThrowsAttempted'],
                'free_throws_made': player['statistics']['freeThrowsMade'],
                'free_throws_percentage': player['statistics']['freeThrowsPercentage'],
                'minus': player['statistics']['minus'],
                'minutes': player['statistics']['minutes'],
                'plus': player['statistics']['plus'],
                'plus_minus_points': player['statistics']['plusMinusPoints'],
                'points': player['statistics']['points'],
                'points_fast_break': player['statistics']['pointsFastBreak'],
                'points_in_the_paint': player['statistics']['pointsInThePaint'],
                'points_second_chance': player['statistics']['pointsSecondChance'],
                'rebounds_defensive': player['statistics']['reboundsDefensive'],
                'rebounds_offensive': player['statistics']['reboundsOffensive'],
                'rebounds_total': player['statistics']['reboundsTotal'],
                'steals': player['statistics']['steals'],
                'three_pointers_attempted': player['statistics']['threePointersAttempted'],
                'three_pointers_made': player['statistics']['threePointersMade'],
                'three_pointers_percentage': player['statistics']['threePointersPercentage'],
                'turnovers': player['statistics']['turnovers'],
                'two_pointers_attempted': player['statistics']['twoPointersAttempted'],
                'two_pointers_made': player['statistics']['twoPointersMade'],
                'two_pointers_percentage': player['statistics']['twoPointersPercentage']
            }
        )