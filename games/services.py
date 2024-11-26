from datetime import datetime, timedelta
from typing import List
import pytz

from games.models import Game, LineScore, TeamStatistics

from django.db.models import Prefetch, Q
from django.db import transaction

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

    TeamStatistics.objects.update_or_create(
        team=team,
        game=game,
        defaults={
            'assists': statistics.get('assists', 0),
            'assists_turnover_ratio': statistics.get('assistsTurnoverRatio', 0),
            'bench_points': statistics.get('benchPoints', 0),
            'biggest_lead': statistics.get('biggestLead', 0),
            'biggest_lead_score': statistics.get('biggestLeadScore', '0-0'),
            'biggest_scoring_run': statistics.get('biggestScoringRun', 0),
            'biggest_scoring_run_score': statistics.get('biggestScoringRunScore', '0-0'),
            'blocks': statistics.get('blocks', 0),
            'blocks_received': statistics.get('blocksReceived', 0),
            'fast_break_points_attempted': statistics.get('fastBreakPointsAttempted', 0),
            'fast_break_points_made': statistics.get('fastBreakPointsMade', 0),
            'fast_break_points_percentage': statistics.get('fastBreakPointsPercentage', 0),
            'field_goals_attempted': statistics.get('fieldGoalsAttempted', 0),
            'field_goals_effective_adjusted': statistics.get('fieldGoalsEffectiveAdjusted', 0),
            'field_goals_made': statistics.get('fieldGoalsMade', 0),
            'field_goals_percentage': statistics.get('fieldGoalsPercentage', 0),
            'fouls_offensive': statistics.get('foulsOffensive', 0),
            'fouls_drawn': statistics.get('foulsDrawn', 0),
            'fouls_personal': statistics.get('foulsPersonal', 0),
            'fouls_team': statistics.get('foulsTeam', 0),
            'fouls_technical': statistics.get('foulsTechnical', 0),
            'fouls_team_technical': statistics.get('foulsTeamTechnical', 0),
            'free_throws_attempted': statistics.get('freeThrowsAttempted', 0),
            'free_throws_made': statistics.get('freeThrowsMade', 0),
            'free_throws_percentage': statistics.get('freeThrowsPercentage', 0),
            'lead_changes': statistics.get('leadChanges', 0),
            'minutes': statistics.get('minutes', 'PT0M00.000S'),
            'points': statistics.get('points', 0),
            'points_against': statistics.get('pointsAgainst', 0),
            'points_fast_break': statistics.get('pointsFastBreak', 0),
            'points_from_turnovers': statistics.get('pointsFromTurnovers', 0),
            'points_in_the_paint': statistics.get('pointsInThePaint', 0),
            'points_in_the_paint_attempted': statistics.get('pointsInThePaintAttempted', 0),
            'points_in_the_paint_made': statistics.get('pointsInThePaintMade', 0),
            'points_in_the_paint_percentage': statistics.get('pointsInThePaintPercentage', 0),
            'points_second_chance': statistics.get('pointsSecondChance', 0),
            'rebounds_defensive': statistics.get('reboundsDefensive', 0),
            'rebounds_offensive': statistics.get('reboundsOffensive', 0),
            'rebounds_personal': statistics.get('reboundsPersonal', 0),
            'rebounds_team': statistics.get('reboundsTeam', 0),
            'rebounds_team_defensive': statistics.get('reboundsTeamDefensive', 0),
            'rebounds_team_offensive': statistics.get('reboundsTeamOffensive', 0),
            'rebounds_total': statistics.get('reboundsTotal', 0),
            'second_chance_points_attempted': statistics.get('secondChancePointsAttempted', 0),
            'second_chance_points_made': statistics.get('secondChancePointsMade', 0),
            'second_chance_points_percentage': statistics.get('secondChancePointsPercentage', 0),
            'steals': statistics.get('steals', 0),
            'three_pointers_attempted': statistics.get('threePointersAttempted', 0),
            'three_pointers_made': statistics.get('threePointersMade', 0),
            'three_pointers_percentage': statistics.get('threePointersPercentage', 0),
            'time_leading': statistics.get('timeLeading', 'PT0M00.000S'),
            'times_tied': statistics.get('timesTied', 0),
            'true_shooting_attempts': statistics.get('trueShootingAttempts', 0),
            'true_shooting_percentage': statistics.get('trueShootingPercentage', 0),
            'turnovers': statistics.get('turnovers', 0),
            'turnovers_team': statistics.get('turnoversTeam', 0),
            'turnovers_total': statistics.get('turnoversTotal', 0),
            'two_pointers_attempted': statistics.get('twoPointersAttempted', 0),
            'two_pointers_made': statistics.get('twoPointersMade', 0),
            'two_pointers_percentage': statistics.get('twoPointersPercentage', 0)
        }
    )

    for player in players:
        try:
            player_obj = Player.objects.get(id=player['personId'])
        except Player.DoesNotExist:
            continue

        PlayerStatistics.objects.update_or_create(
            player=player_obj,
            game=game,
            team=team,
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


def update_team_statistics(game, team, statistics):
    TeamStatistics.objects.update_or_create(
        team=team,
        game=game,
        defaults={
            'assists': statistics.get('assists', 0),
            'assists_turnover_ratio': statistics.get('assistsTurnoverRatio', 0),
            'bench_points': statistics.get('benchPoints', 0),
            'biggest_lead': statistics.get('biggestLead', 0),
            'biggest_lead_score': statistics.get('biggestLeadScore', '0-0'),
            'biggest_scoring_run': statistics.get('biggestScoringRun', 0),
            'biggest_scoring_run_score': statistics.get('biggestScoringRunScore', '0-0'),
            'blocks': statistics.get('blocks', 0),
            'blocks_received': statistics.get('blocksReceived', 0),
            'fast_break_points_attempted': statistics.get('fastBreakPointsAttempted', 0),
            'fast_break_points_made': statistics.get('fastBreakPointsMade', 0),
            'fast_break_points_percentage': statistics.get('fastBreakPointsPercentage', 0),
            'field_goals_attempted': statistics.get('fieldGoalsAttempted', 0),
            'field_goals_effective_adjusted': statistics.get('fieldGoalsEffectiveAdjusted', 0),
            'field_goals_made': statistics.get('fieldGoalsMade', 0),
            'field_goals_percentage': statistics.get('fieldGoalsPercentage', 0),
            'fouls_offensive': statistics.get('foulsOffensive', 0),
            'fouls_drawn': statistics.get('foulsDrawn', 0),
            'fouls_personal': statistics.get('foulsPersonal', 0),
            'fouls_team': statistics.get('foulsTeam', 0),
            'fouls_technical': statistics.get('foulsTechnical', 0),
            'fouls_team_technical': statistics.get('foulsTeamTechnical', 0),
            'free_throws_attempted': statistics.get('freeThrowsAttempted', 0),
            'free_throws_made': statistics.get('freeThrowsMade', 0),
            'free_throws_percentage': statistics.get('freeThrowsPercentage', 0),
            'lead_changes': statistics.get('leadChanges', 0),
            'minutes': statistics.get('minutes', 'PT0M00.000S'),
            'points': statistics.get('points', 0),
            'points_against': statistics.get('pointsAgainst', 0),
            'points_fast_break': statistics.get('pointsFastBreak', 0),
            'points_from_turnovers': statistics.get('pointsFromTurnovers', 0),
            'points_in_the_paint': statistics.get('pointsInThePaint', 0),
            'points_in_the_paint_attempted': statistics.get('pointsInThePaintAttempted', 0),
            'points_in_the_paint_made': statistics.get('pointsInThePaintMade', 0),
            'points_in_the_paint_percentage': statistics.get('pointsInThePaintPercentage', 0),
            'points_second_chance': statistics.get('pointsSecondChance', 0),
            'rebounds_defensive': statistics.get('reboundsDefensive', 0),
            'rebounds_offensive': statistics.get('reboundsOffensive', 0),
            'rebounds_personal': statistics.get('reboundsPersonal', 0),
            'rebounds_team': statistics.get('reboundsTeam', 0),
            'rebounds_team_defensive': statistics.get('reboundsTeamDefensive', 0),
            'rebounds_team_offensive': statistics.get('reboundsTeamOffensive', 0),
            'rebounds_total': statistics.get('reboundsTotal', 0),
            'second_chance_points_attempted': statistics.get('secondChancePointsAttempted', 0),
            'second_chance_points_made': statistics.get('secondChancePointsMade', 0),
            'second_chance_points_percentage': statistics.get('secondChancePointsPercentage', 0),
            'steals': statistics.get('steals', 0),
            'three_pointers_attempted': statistics.get('threePointersAttempted', 0),
            'three_pointers_made': statistics.get('threePointersMade', 0),
            'three_pointers_percentage': statistics.get('threePointersPercentage', 0),
            'time_leading': statistics.get('timeLeading', 'PT0M00.000S'),
            'times_tied': statistics.get('timesTied', 0),
            'true_shooting_attempts': statistics.get('trueShootingAttempts', 0),
            'true_shooting_percentage': statistics.get('trueShootingPercentage', 0),
            'turnovers': statistics.get('turnovers', 0),
            'turnovers_team': statistics.get('turnoversTeam', 0),
            'turnovers_total': statistics.get('turnoversTotal', 0),
            'two_pointers_attempted': statistics.get('twoPointersAttempted', 0),
            'two_pointers_made': statistics.get('twoPointersMade', 0),
            'two_pointers_percentage': statistics.get('twoPointersPercentage', 0)
        }
    )

def create_game_queryset_without_prefetch(
    request, 
    fields_only=[], 
    **kwargs
):
    """
    Create a queryset for the Game model without prefetching and selecting related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    if kwargs is not None:
        queryset = Game.objects.filter(**kwargs)
    else:
        queryset = Game.objects.all()

    teams_filter : str | None = request.query_params.get('teams', None)
    if teams_filter is not None:
        teams_filter = teams_filter.split(',')
        queryset = queryset.filter(
            Q(home_team__symbol__in=teams_filter) | Q(visitor_team__symbol__in=teams_filter)
        ).distinct()

    date_start_filter : str | None = request.query_params.get('date-range-start', None)
    date_end_filter : str | None = request.query_params.get('date-range-end', None)

    if date_start_filter is not None and date_end_filter is not None:
        try:
            date_start = datetime.fromisoformat(date_start_filter) - timedelta(days=1)
            date_end = datetime.fromisoformat(date_end_filter) + timedelta(days=1)

            queryset = queryset.filter(
                game_date_est__range=[
                    date_start, 
                    date_end
                ]
            )
        except ValueError:
            pass

    queryset = queryset.order_by('game_date_est')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset