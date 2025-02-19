from datetime import datetime, timedelta
from typing import List
import pytz

from api.exceptions import NotFoundError
from api.websocket import send_message_to_centrifuge
from games.models import Game, GameChat, GameChatBan, GameChatMessage, GameChatMute, LineScore, TeamStatistics

from django.db.models import Prefetch, Q
from django.db.models.manager import BaseManager

from games.serializers import GameChatBanSerializer, GameChatSerializer, GameSerializer, LineScoreSerializer, PlayerStatisticsSerializer
from players.models import Player, PlayerStatistics
from teams.models import TeamLike, TeamName, Team

from rest_framework.status import (
    HTTP_400_BAD_REQUEST, 
    HTTP_404_NOT_FOUND, 
    HTTP_500_INTERNAL_SERVER_ERROR
)
from typing import Tuple
from users.models import User
from users.utils import validate_websocket_subscription_token


def get_today_games() -> Tuple[BaseManager[Game], BaseManager[LineScore]]:
    """
    Get today's games and their linescores.
    The game time is in EST.

    Returns:
    - games: queryset of games
    - linescores: queryset of linescores
    """

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
            queryset=TeamName.objects.select_related('language')
        ),
        Prefetch(
            'visitor_team__teamname_set',
            queryset=TeamName.objects.select_related('language')
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

def combine_games_and_linescores(games, linescores) -> List[dict]:
    """
    Combine games and linescores into a single dictionary.

    Returns:
    - games: list of games with linescores
    """

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

def combine_game_and_linescores(game, linescores) -> dict:
    """
    Combine a single game and its linescores into a single dictionary.

    Returns:
    - game: game with linescores
    """

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
    game: Game,
    team: Team,
    linescore: List[dict],
    players: List[dict],
    statistics: dict
) -> None:
    """
    Update the live scores of a game.
    """

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


def update_team_statistics(game, team, statistics) -> None:
    """
    Update the team statistics of a game.
    """

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
) -> BaseManager[Game]:
    """
    Create a queryset for the Game model without prefetching and selecting related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter

    Returns:
    - queryset: queryset of games
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
            if date_start_filter == date_end_filter:
                date_start_filter = datetime.fromisoformat(date_start_filter) - timedelta(days=1)
                date_end_filter = datetime.fromisoformat(date_end_filter) + timedelta(days=1)

            queryset = queryset.filter(
                game_date_est__range=[
                    date_start_filter,
                    date_end_filter
                ]
            )
        except ValueError:
            pass

    queryset = queryset.order_by('game_date_est')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset


class GameService:
    @staticmethod
    def get_games(request) -> List[Game]:
        all_team_names = TeamName.objects.select_related('language')

        return create_game_queryset_without_prefetch(
            request
        ).prefetch_related(
            Prefetch(
                'line_scores',
                queryset=LineScore.objects.select_related('team').prefetch_related(
                    Prefetch(
                        'team__teamname_set',
                        queryset=all_team_names
                    )
                )
            ),
            Prefetch(
                'home_team__teamname_set',
                queryset=all_team_names
            ),
            Prefetch(
                'visitor_team__teamname_set',
                queryset=all_team_names
            )
        ).select_related(
            'home_team', 'visitor_team'
        )
    
    @staticmethod
    def get_game(pk):
        return Game.objects.select_related(
            'home_team', 'visitor_team'
        ).prefetch_related(
            'teamstatistics_set',
        ).get(game_id=pk)
    
    @staticmethod
    def get_game_line_scores(game):
        return LineScore.objects.filter(
            game=game
        ).select_related(
            'game',
            'team'
        ).order_by(
            'game__game_date_est',
            'game__game_sequence'
        )
    
    @staticmethod
    def get_game_players_statistics(game_id):
        return PlayerStatistics.objects.filter(
            game__game_id=game_id
        ).select_related(
            'player',
            'team'
        ).order_by(
            'team__id',
            'order',
            '-starter'
        ).defer(
            'game'
        )
    
    @staticmethod
    def create_game_chat_message(request, pk):
        channel = f'games/{pk}/live-chat'

        subscription_token = request.data.get('subscription_token', None)
        if subscription_token is None:
            return False, {'error': 'Subscription token is required'}, HTTP_400_BAD_REQUEST

        if not validate_websocket_subscription_token(
            subscription_token, 
            channel, 
            request.user.id
        ):
            return False, {'error': 'Invalid subscription token'}, HTTP_400_BAD_REQUEST

        message = request.data.get('message', None)
        if message is None:
            return False, {'error': 'Message is required'}, HTTP_400_BAD_REQUEST

        try:
            game = Game.objects.get(game_id=pk)
        except Game.DoesNotExist:
            return False, {'error': 'Game not found'}, HTTP_404_NOT_FOUND
        
        user_favorite_team = TeamLike.objects.filter(
            user=request.user,
            favorite=True,
        ).select_related('team').first()
        
        resp_json = send_message_to_centrifuge(channel, {
            'message': message,
            'user': {
                'id': request.user.id,
                'username': request.user.get_username(),
                'favorite_team': user_favorite_team.team.symbol if user_favorite_team else None
            },
            'game': game.game_id,
            'created_at': int(datetime.now().timestamp())
        })
        if resp_json.get('error', None):
            return False, {'error': 'Message Delivery Unsuccessful'}, HTTP_500_INTERNAL_SERVER_ERROR
        
        game_chat, created = GameChat.objects.get_or_create(game=game)
        GameChatMessage.objects.create(
            chat=game_chat,
            message=message,
            user=request.user
        )

        return True, None, None
    
class GameChatService:
    @staticmethod
    def get_game_chat(pk):
        return GameChat.objects.filter(
            game__game_id=pk
        ).select_related(
            'game'
        ).only(
            'game__game_id',
            'game__game_status_id',
            'id',
            'slow_mode',
            'slow_mode_time',
        ).first()
    
    @staticmethod
    def get_game_chat_messages(pk):
        try:
            game = Game.objects.get(game_id=pk)
        except Game.DoesNotExist:
            return None
        
        return GameChatMessage.objects.filter(chat__game=game).select_related('user').order_by('created_at')
    
    @staticmethod
    def block_user(pk: str, user: User, user_id: str) -> None:
        """
        Allow a user to block/unblock another user in a game chat.

        Args:
            - pk (str): game id
            - user (User): user who is blocking/unblocking
            - user_id (str): user id of the user to block/unblock

        Returns:
            - None
        """
        try:
            game_chat = GameChat.objects.get(game__game_id=pk)
        except GameChat.DoesNotExist:
            raise NotFoundError()
        
    @staticmethod
    def create_game_chat_message(request, pk):
        channel = f'games/{pk}/live-chat'

        subscription_token = request.data.get('subscription_token', None)
        if subscription_token is None:
            return False, {'error': 'Subscription token is required'}, HTTP_400_BAD_REQUEST

        if not validate_websocket_subscription_token(
            subscription_token, 
            channel, 
            request.user.id
        ):
            return False, {'error': 'Invalid subscription token'}, HTTP_400_BAD_REQUEST

        message = request.data.get('message', None)
        if message is None:
            return False, {'error': 'Message is required'}, HTTP_400_BAD_REQUEST

        try:
            game = Game.objects.get(game_id=pk)
        except Game.DoesNotExist:
            return False, {'error': 'Game not found'}, HTTP_404_NOT_FOUND
        
        user_favorite_team = TeamLike.objects.filter(
            user=request.user,
            favorite=True,
        ).select_related('team').first()
        
        resp_json = send_message_to_centrifuge(channel, {
            'message': message,
            'user': {
                'id': request.user.id,
                'username': request.user.get_username(),
                'favorite_team': user_favorite_team.team.symbol if user_favorite_team else None
            },
            'game': game.game_id,
            'created_at': int(datetime.now().timestamp())
        })
        if resp_json.get('error', None):
            return False, {'error': 'Message Delivery Unsuccessful'}, HTTP_500_INTERNAL_SERVER_ERROR
        
        game_chat, created = GameChat.objects.get_or_create(game=game)
        GameChatMessage.objects.create(
            chat=game_chat,
            message=message,
            user=request.user
        )

        return True, None, None

class GameSerializerService:
    @staticmethod
    def serialize_games(games):
        return GameSerializer(
            games,
            many=True,
            fields_exclude=[
                'home_team_statistics',
                'visitor_team_statistics',
                'home_team_player_statistics',
                'visitor_team_player_statistics'
            ],
            context={
                'linescore': {
                    'fields_exclude': ['id', 'game']
                },
                'team': {
                    'fields': ['id', 'symbol', 'teamname_set']
                },
                'teamname': {
                    'fields': ['name', 'language']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_game(game):
        game_fields_exclude = [
            'line_scores',
            'home_team_player_statistics',
            'visitor_team_player_statistics'
        ]

        if game.game_status_id == 1:
            game_fields_exclude.extend([
                'home_team_statistics',
                'visitor_team_statistics'
            ])

        game_serializer_context = {
            'team': {'fields': ('id', 'symbol', 'teamname_set')},
            'teamname': {'fields': ('name', 'language')},
            'language': {'fields': ('name',)},
        }

        if game.game_status_id > 1:
            game_serializer_context.update({
                'teamstatistics': {'fields_exclude': ('game',)},
            })

        return GameSerializer(
            game,
            fields_exclude=game_fields_exclude,
            context=game_serializer_context
        )
    
    @staticmethod
    def serialize_line_scores(linescores):
        return LineScoreSerializer(
            linescores,
            many=True,
            context={
                'game': {'fields': ('game_id',)},
                'team': {'fields': ('id',)},
            }
        )
    
    @staticmethod
    def serialize_game_players_statistics(players_statistics):
        return PlayerStatisticsSerializer(
            players_statistics,
            many=True,
            fields_exclude=['game_data', 'game'],
            context={
                'player': {'fields': ('id', 'first_name', 'last_name')},
                'team': {'fields': ('id',)},
            }
        )
    
class GameChatSerializerService:
    def serialize_game_chat(game_chat: GameChat) -> GameChatSerializer:
        return GameChatSerializer(
            game_chat,
        )