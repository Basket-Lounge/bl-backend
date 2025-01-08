from datetime import timedelta, datetime
import re
from typing import List

from django.db import transaction
from django.db.models import Q, Prefetch, Count, Exists, OuterRef

from nba_api.stats.endpoints.franchisehistory import FranchiseHistory
from nba_api.stats.endpoints.leaguestandingsv3 import LeagueStandingsV3
from nba_api.stats.endpoints.scoreboardv2 import ScoreboardV2
import pytz

from api.exceptions import AnonymousUserError
from games.models import Game, LineScore
from games.serializers import (
    GameSerializer, 
    LineScoreSerializer, 
    PlayerCareerStatisticsSerializer, 
    PlayerStatisticsSerializer
)
from games.services import combine_games_and_linescores
from notification.services import NotificationService
from players.models import Player, PlayerCareerStatistics, PlayerStatistics
from players.serializers import PlayerSerializer
from teams.forms import TeamPostCommentForm, TeamPostForm
from teams.models import (
    Post, 
    PostComment, 
    PostCommentLike, 
    PostCommentReply,
    PostCommentStatus,
    PostCommentStatusDisplayName, 
    PostLike,
    PostStatus, 
    PostStatusDisplayName, 
    Team,
    TeamLike, 
    TeamName
)
from teams.serializers import PostCommentStatusSerializer, PostStatusSerializer, TeamSerializer
from teams.utils import calculate_time
from users.serializers import (
    PostCommentCreateSerializer, 
    PostCommentReplyCreateSerializer, 
    PostCommentReplySerializer,
    PostCommentSerializer, 
    PostCommentUpdateSerializer, 
    PostSerializer, 
    PostUpdateSerializer
)
from users.services import create_post_queryset_without_prefetch_for_user


comment_queryset_allowed_order_by_fields = [
    'created_at',
    '-created_at',
    'postcommentlike',
    '-postcommentlike',
    'postcommentreply',
    '-postcommentreply',
]

def get_all_teams_season_stats(year):
    ## Use Regex to get the year from the season
    year = re.search(r'^\d\d\d\d-\d\d', year)
    if not year:
        raise ValueError('Invalid year format. Use YYYY-YY format')
    
    ## Get the ranking from nba_api
    standings = LeagueStandingsV3(
        league_id='00',
        season=year.group(),
        season_type='Regular Season'
    ).get_dict()['resultSets'][0]

    headers = standings['headers']
    standings = standings['rowSet']

    ## Get the team ranking
    ranking = {
        'East': [],
        'West': []
    }

    # Separate the teams by conference
    all_teams = Team.objects.all().only('symbol')

    for team in standings:
        conference = team[6]
        if conference == 'East':
            ranking['East'].append(dict(zip(headers, team)))
        else:
            ranking['West'].append(dict(zip(headers, team)))

        ranking[conference][-1]['TeamAbbreviation'] = all_teams.get(id=ranking[conference][-1]['TeamID']).symbol

    return ranking

def get_all_games_for_team_this_season(team_id):
    team = None
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        raise ValueError('Invalid team_id')

    all_team_names = TeamName.objects.select_related('language').all()
    
    games = Game.objects.select_related(
        'home_team', 'visitor_team'
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
    ).filter(
        Q(home_team=team) | Q(visitor_team=team)
    ).order_by('game_date_est')

    serializer = GameSerializer(
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

    return serializer.data

def get_monthly_games_for_team_this_season(team_id, month):
    team = None
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        raise ValueError('Invalid team_id')

    all_team_names = TeamName.objects.select_related('language').all()

    games = Game.objects.select_related(
        'home_team', 'visitor_team'
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
        ),
    ).filter(
        Q(home_team=team) | Q(visitor_team=team),
        Q(game_date_est__month=month)
    ).order_by('game_date_est')

    serializer = GameSerializer(
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

    return serializer.data

def get_team_franchise_history(team_id):
    try:
        Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        raise ValueError('Invalid team_id')

    franchise_history = FranchiseHistory(
        league_id='00'
    ).get_dict()['resultSets'][0]
    
    headers = franchise_history['headers']
    franchise_history = franchise_history['rowSet']

    for team in franchise_history:
        if str(team[1]) == team_id:
            return dict(zip(headers, team))

def get_team_season_stats(year, team_id):
    ## Use Regex to get the year from the season
    year = re.search(r'^\d\d\d\d-\d\d', year)
    if not year:
        raise ValueError('Invalid year format. Use YYYY-YY format')
    
    try:
        Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        raise ValueError('Invalid team_id')
    
    ## Get the ranking from nba_api
    standings = LeagueStandingsV3(
        league_id='00',
        season=year.group(),
        season_type='Regular Season'
    ).get_dict()['resultSets'][0]

    headers = standings['headers']
    standings = standings['rowSet']

    ## Get the team ranking
    ranking = {}

    for team in standings:
        if str(team[2]) == team_id:
            ranking = dict(zip(headers, team))
            break
    
    return ranking

def get_player_last_n_games_log(player_id, n=5):
    stats = PlayerStatistics.objects.filter(
        player__id=player_id
    ).select_related(
        'player',
        'game__visitor_team',
        'team'
    ).order_by(
        '-game__game_date_est'
    )[:n]

    return stats

def get_last_n_games_log(team_id, n=5):
    if n < 1 or n > 82:
        raise ValueError('Invalid n value. n should be between 1 and 82')

    try:
        Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        raise ValueError('Invalid team_id')
    
    all_team_names = TeamName.objects.select_related('language').all()
    
    ## Get the last 5 games log from nba_api
    games = Game.objects.select_related(
        'home_team', 'visitor_team'
    ).prefetch_related(
        Prefetch(
            'home_team__teamname_set',
            queryset=all_team_names
        ),
        Prefetch(
            'visitor_team__teamname_set',
            queryset=all_team_names
        )
    ).filter(
        Q(home_team__id=team_id) | Q(visitor_team__id=team_id),
        Q(game_status_id=3) | Q(game_status_id=2)
    ).order_by('-game_date_est')[:n]

    if games.count() < n:
        games = Game.objects.select_related(
            'home_team', 'visitor_team'
        ).prefetch_related(
            Prefetch(
                'home_team__teamname_set',
                queryset=all_team_names
            ),
            Prefetch(
                'visitor_team__teamname_set',
                queryset=all_team_names
            )
        ).filter(
            Q(home_team=team_id) | Q(visitor_team=team_id),
        ).order_by('game_date_est')[:n]

    serializer = GameSerializer(
        games,
        many=True,
        fields_exclude=[
            'line_scores',
            'home_team_statistics',
            'visitor_team_statistics',
            'home_team_player_statistics',
            'visitor_team_player_statistics'
        ],
        context={
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

    linescores = LineScore.objects.filter(
        game__in=games
    ).select_related(
        'game',
        'team'
    ).order_by(
        'game__game_date_est',
        'game__game_sequence'
    )

    linescore_serializer = LineScoreSerializer(
        linescores,
        many=True,
        context={
            'game': {
                'fields': ['game_id']
            },
            'team': {
                'fields': ['id']
            }
        }
    )

    return serializer.data, linescore_serializer.data

def get_player_career_stats(player_id):
    ## Get the team players from nba_api
    career_stats = PlayerCareerStatistics.objects.select_related('player', 'team').filter(
        player__id=player_id
    )

    return career_stats

def get_player_current_season_stats(player_id, team_id):
    player = Player.objects.filter(id=player_id).prefetch_related(
        'playerstatistics_set'
    ).first()

    if not player:
        raise ValueError('Invalid player_id')
    
    serializer = PlayerSerializer(
        player,
        fields=['season_stats'],
    )

    return serializer.data['season_stats']

    # career_stats = PlayerCareerStatistics.objects.select_related('player', 'team').filter(
    #     player__id=player_id,
    #     season_id=current_season
    # )

    # if not career_stats.exists():
    #     return create_empty_player_season_stats()

    # serializer = PlayerCareerStatisticsSerializer(
    #     career_stats.first(),
    #     fields_exclude=['player', 'team', 'team_data'],
    # )
    
    # return serializer.data

def get_team_players(team_id):
    try:
        Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        raise ValueError('Invalid team_id')

    return Player.objects.filter(
        team__id=team_id
    ).prefetch_related('team__teamname_set').all()

def register_games_for_the_current_season():
    # extract data from the certain date to certain date
    # save the data to the database

    starting_date = datetime(2024, 12, 16)
    ending_date = datetime(2024, 12, 21)

    current_date = starting_date
    
    while current_date <= ending_date:
        scoreboard_data = ScoreboardV2(
            game_date=current_date,
            league_id='00',
            day_offset=0
        ).get_dict()['resultSets']

        games = scoreboard_data[0]
        headers = games['headers']
        games = games['rowSet']

        for game in games:
            game_data = dict(zip(headers, game))
            print(game_data)
            home_team = None
            visitor_team = None 

            try:
                home_team = Team.objects.get(id=game_data['HOME_TEAM_ID'])
                print(f'Home team: {home_team.symbol}')
                visitor_team = Team.objects.get(id=game_data['VISITOR_TEAM_ID'])
                print(f'Visitor team: {visitor_team.symbol}')
            except Team.DoesNotExist:
                continue

            if home_team.symbol == visitor_team.symbol:
                raise ValueError('Home team and visitor team are the same')
            
            ## create a datetime object from the string date and time, with the timezone set to EST
            datetime_obj = datetime.fromisoformat(game_data['GAME_DATE_EST'])

            timezone = pytz.timezone('US/Eastern')
            try:
                hour, minute = calculate_time(game_data['GAME_STATUS_TEXT'])
                datetime_obj = datetime_obj.replace(hour=hour, minute=minute, tzinfo=timezone)
            except IndexError:
                pass 


            if Game.objects.filter(game_id=game_data['GAME_ID']).exists():
                print(f"Game {game_data['GAME_ID']} already exists")
                continue

            game_instance = Game(
                game_id=game_data['GAME_ID'],
                game_date_est=datetime_obj,
                game_sequence=game_data['GAME_SEQUENCE'],
                game_status_id=game_data['GAME_STATUS_ID'],
                game_status_text=game_data['GAME_STATUS_TEXT'],
                game_code=game_data['GAMECODE'],
                home_team=home_team,
                visitor_team=visitor_team,
                season=game_data['SEASON'],
                live_period=game_data['LIVE_PERIOD'],
                live_pc_time=game_data['LIVE_PC_TIME'],
                natl_tv_broadcaster_abbreviation=game_data['NATL_TV_BROADCASTER_ABBREVIATION'],
                home_tv_broadcaster_abbreviation=game_data['HOME_TV_BROADCASTER_ABBREVIATION'],
                away_tv_broadcaster_abbreviation=game_data['AWAY_TV_BROADCASTER_ABBREVIATION'],
                live_period_time_bcast=game_data['LIVE_PERIOD_TIME_BCAST'],
                arena_name=game_data['ARENA_NAME'],
                wh_status=game_data['WH_STATUS'],
                wnba_commissioner_flag=game_data['WNBA_COMMISSIONER_FLAG']
            )

            game_instance.save()
            LineScore.objects.create(
                game=game_instance,
                team=home_team,
            )
            LineScore.objects.create(
                game=game_instance,
                team=visitor_team,
            )

            LineScore.objects.filter(game=game_instance, team=home_team).get()
            LineScore.objects.filter(game=game_instance, team=visitor_team).get()

            print(f"Game {game_instance.game_id} created")

        current_date += timedelta(days=1)

def create_comment_queryset_without_prefetch_for_post(
    request,
    fields_only=[],
    **kwargs
):
    """
    Create a queryset for the PostComment model without prefetching related models.\n
    - request: request object.\n
    - fields_only: list of fields to return in the queryset.\n
    - **kwargs: keyword arguments to filter
    """

    if kwargs is not None:
        queryset = PostComment.objects.filter(**kwargs)
    else:
        queryset = PostComment.objects.all()

    sort_by_likes_count, sort_by_likes_count_direction = False, True
    sort_by_replies_count, sort_by_replies_count_direction = False, True

    sort_by : str | None = request.query_params.get('sort', None)
    if sort_by is not None:
        sort_by : List[str] = sort_by.split(',')
        unique_sort_by = set(sort_by)
        new_unique_sort_by = set()

        for field in unique_sort_by:
            if field.find('postcommentlike') != -1:
                if field.find('-') != -1:
                    # if the field has a '-' at the beginning, it means that it should be sorted in descending order
                    sort_by_likes_count_direction = False

                sort_by_likes_count = True
                continue
            elif field.find('postcommentreply') != -1:
                if field.find('-') != -1:
                    sort_by_replies_count_direction = False

                sort_by_replies_count = True
                continue

            if field in comment_queryset_allowed_order_by_fields:
                new_unique_sort_by.add(field)

        sort_by = list(new_unique_sort_by)

    if sort_by_likes_count:
        queryset = queryset.annotate(
            likes_count=Count('postcommentlike')
        )

        if sort_by_likes_count_direction:
            sort_by.append('likes_count')
        else:
            sort_by.append('-likes_count')

    if sort_by_replies_count:
        queryset = queryset.annotate(
            replies_count=Count('postcommentreply')
        )

        if sort_by_replies_count_direction:
            sort_by.append('replies_count')
        else:
            sort_by.append('-replies_count')

    if sort_by:
        queryset = queryset.order_by(*sort_by)
    else:
        queryset = queryset.order_by('-created_at')

    if fields_only:
        return queryset.only(*fields_only)

    return queryset.exclude(status__name='deleted')


class TeamService:
    @staticmethod
    def get_team(request, pk):
        team = Team.objects.prefetch_related(
            Prefetch(
                'teamname_set',
                queryset=TeamName.objects.select_related(
                    'language'
                ).only('name', 'language__name'),
            )
        ).filter(id=pk)

        if request.user.is_authenticated:
            team = team.annotate(
                liked=Exists(TeamLike.objects.filter(user=request.user, team=OuterRef('pk')))
            )

        return team.first()

    @staticmethod
    def get_team_with_user_like(user):
        return Team.objects.prefetch_related(
            'teamname_set'
        ).filter(
            teamlike__user=user
        ).order_by('symbol').only('id', 'symbol')
    
    @staticmethod
    def get_all_teams():
        return Team.objects.prefetch_related(
            Prefetch(
                'teamname_set',
                queryset=TeamName.objects.select_related(
                    'language'
                )
            )
        ).order_by('symbol')
    
    @staticmethod
    def get_and_serialize_team_last_n_games(team_id, n=5):
        games_data, linescores_data = get_last_n_games_log(team_id, n)
        return combine_games_and_linescores(games_data, linescores_data)
    
    @staticmethod
    def get_all_games(team_id):
        all_team_names = TeamName.objects.select_related('language').all()

        return Game.objects.select_related(
            'home_team', 'visitor_team'
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
        ).filter(
            Q(home_team__id=team_id) | Q(visitor_team__id=team_id)
        ).order_by('game_date_est')
    
    @staticmethod
    def update_user_favorite_teams(request):
        with transaction.atomic():
            user = request.user
            data = request.data

            count_favorite_teams = 0
            favorite_team_id = None
            for team in data:
                if 'favorite' in team and team['favorite']:
                    count_favorite_teams += 1
                    favorite_team_id = team['id']
                
                if count_favorite_teams > 1:
                    return False, {'error': 'Only one favorite team allowed'}

            team_ids = [team['id'] for team in data]
            teams = Team.objects.filter(id__in=team_ids)

            TeamLike.objects.filter(user=user).delete()
            TeamLike.objects.bulk_create([
                TeamLike(user=user, team=team) if favorite_team_id != team.id else TeamLike(user=user, team=team, favorite=True)
                for team in teams
            ])

            return True, None
    
    @staticmethod
    def add_user_favorite_team(request, team_id):
        user = request.user
        TeamLike.objects.get_or_create(
            user=user, 
            team=Team.objects.get(id=team_id)
        )
        
        return Team.objects.filter(id=team_id).annotate(
            liked=Exists(TeamLike.objects.filter(user=user, team=OuterRef('pk')))
        ).first()
    
    @staticmethod
    def remove_user_favorite_team(request, team_id):
        user = request.user
        try:
            TeamLike.objects.get(user=user, team__id=team_id).delete()
        except TeamLike.DoesNotExist:
            pass
        
        return Team.objects.filter(id=team_id).annotate(
            liked=Exists(TeamLike.objects.filter(user=user, team=OuterRef('pk')))
        ).first()

    
class TeamSerializerService:
    @staticmethod
    def serialize_team(request, team: Team):
        fields_exclude = []
        if not request.user.is_authenticated:
            fields_exclude.append('liked')

        return TeamSerializer(
            team,
            fields_exclude=fields_exclude,
            context={
                'teamname': {
                    'fields': ['name', 'language'],
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    def serialize_team_without_likes_count_and_liked(teams):
        return TeamSerializer(
            teams,
            many=True,
            fields_exclude=['likes_count', 'liked'],
            context={
                'teamname': {
                    'fields': ['name', 'language'],
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

    @staticmethod
    def serialize_teams_with_user_favorite(teams, user):
        serializer = TeamSerializer(
            teams,
            many=True,
            fields=['id', 'symbol', 'teamname_set'],
            context={
                'teamname': {
                    'fields': ['name', 'language']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        favorite_team = TeamLike.objects.filter(user=user, favorite=True).first()
        if favorite_team:
            for team in serializer.data:
                if team['id'] == favorite_team.team.id:
                    team['favorite'] = True
                    break

        return serializer.data
    
    @staticmethod
    def serialize_team_without_teamname(team):
        return TeamSerializer(
            team,
            fields_exclude=['teamname_set'],
        )
    
    @staticmethod
    def serialize_all_games(games):
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
    

class TeamPlayerService:
    def get_team_players(team_id):
        try:
            Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            raise ValueError('Invalid team_id')

        return Player.objects.filter(
            team__id=team_id
        ).prefetch_related('team__teamname_set')
    
    def get_team_player_career_stats(team_id, player_id):
        players = TeamPlayerService.get_team_players(team_id)
        for player in players:
            if player.id == int(player_id):
                return get_player_career_stats(player_id)
            
        return PlayerCareerStatistics.objects.none()
    
    def get_team_player_with_season_stats(player_id):
        return Player.objects.filter(id=player_id).prefetch_related(
            'playerstatistics_set'
        ).first()
    
    def get_team_player_last_n_games_log(player_id, n=5):
        return get_player_last_n_games_log(player_id, n)
    
class TeamPlayerSerializerService:
    def serialize_players(players):
        return PlayerSerializer(
            players,
            fields_exclude=['season_stats'],
            many=True,
            context={
                'team': {
                    'fields': ('id', 'symbol', 'teamname_set')
                },
                'teamname': {
                    'fields': ('name', 'language')
                },
                'language': {
                    'fields': ('name',)
                }
            }
        )
    
    def serialize_player_career_stats(stats):
        return PlayerCareerStatisticsSerializer(
            stats,
            many=True,
            fields_exclude=['player', 'team'],
            context={
                'team': {
                    'fields': ('id', 'symbol', 'teamname_set')
                },
                'teamname': {
                    'fields': ('name', 'language')
                },
                'language': {
                    'fields': ('name',)
                }
            }
        )
    
    def serialize_player_for_season_stats(player):
        return PlayerSerializer(
            player,
            fields=['season_stats'],
        )
    
    def serialize_player_games_stats(stats):
        return PlayerStatisticsSerializer(
            stats,
            many=True,
            context={
                'player': {
                    'fields': ['id', 'first_name', 'last_name']
                },
                'team': {
                    'fields': ('id', 'symbol')
                },
                'game': {
                    'fields': ('visitor_team', 'home_team'),
                },
            }
        )

class PostService:
    @staticmethod
    def get_all_statuses():
        return PostStatus.objects.all()
    
    @staticmethod
    def get_statuses_for_post_creation():
        return PostStatus.objects.exclude(name='deleted').prefetch_related(
            Prefetch(
                'poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                )
            )
        )
    
    @staticmethod
    def get_comment_statuses():
        return PostCommentStatus.objects.prefetch_related(
            Prefetch(
                'postcommentstatusdisplayname_set',
                queryset=PostCommentStatusDisplayName.objects.select_related(
                    'language'
                )
            )
        )
    
    @staticmethod
    def create_post(request, pk):
        form = TeamPostForm(request.data)
        if not form.is_valid():
            return False, form.errors.as_data()
        
        user = request.user
        data = form.cleaned_data

        try:
            team = Team.objects.get(id=pk)
        except Team.DoesNotExist:
            return False, 'Invalid team_id'
        
        Post.objects.create(
            user=user,
            team=team,
            status=data['status'],
            title=data['title'],
            content=data['content']
        )

        return True, None
    
    @staticmethod
    def get_team_posts(request, pk):
        posts = create_post_queryset_without_prefetch_for_user(
            request,
            fields_only=[
                'id', 
                'title', 
                'created_at', 
                'updated_at', 
                'user__id', 
                'user__username', 
                'team__id', 
                'team__symbol', 
                'status__id', 
                'status__name'
            ],
            team__id=pk
        ).select_related(
            'user',
            'team',
            'status'
        ).prefetch_related(
            'postlike_set',
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                )
            ),
        ).exclude(
            Q(status__name='deleted') | Q(status__name='hidden')
        )

        if request.user.is_authenticated:
            posts = posts.annotate(
                liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
            )

        return posts

    @staticmethod
    def get_post(request, pk, post_id):
        post = Post.objects.select_related(
            'user',
            'team',
            'status'
        ).prefetch_related(
            'postlike_set',
            'postcomment_set',
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                )
            )
        ).only(
            'id', 
            'title', 
            'content', 
            'created_at', 
            'updated_at', 
            'user__id', 
            'user__username', 
            'team__id', 
            'team__symbol', 
            'status__id',
            'status__name'
        ).filter(
            team__id=pk,
            id=post_id,
        ).exclude(
            status__name='deleted'
        )

        if request.user.is_authenticated:
            post = post.annotate(
                liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
            )

        return post.first()

    @staticmethod
    def get_post_after_creating_like(request, team_id, post_id):
        post = Post.objects.filter(
            team__id=team_id,
            id=post_id
        ).only(
            'id'
        )

        if request.user.is_authenticated:
            post = post.annotate(
                liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
            )

        return post.first()

    @staticmethod
    def get_comments(request, pk, post_id):
        query = create_comment_queryset_without_prefetch_for_post(
            request,
            fields_only=[
                'id',
                'content',
                'created_at',
                'updated_at',
                'user__id',
                'user__username',
                'status__id',
                'status__name'
            ],
            post__team__id=pk,
            post__id=post_id
        ).select_related(
            'user',
            'status'
        ).prefetch_related(
            Prefetch(
                'postcommentlike_set',
                queryset=PostCommentLike.objects.only('id')
            ),
            Prefetch(
                'postcommentreply_set',
                queryset=PostCommentReply.objects.only('id')
            ),
        )

        if request.user.is_authenticated:
            query = query.annotate(
                liked=Exists(PostCommentLike.objects.filter(user=request.user, post_comment=OuterRef('pk')))
            )

        return query
    
    @staticmethod
    def get_comment(request, pk, post_id, comment_id):
        comment = PostComment.objects.select_related(
            'user',
            'status'
        ).prefetch_related(
            Prefetch(
                'postcommentlike_set',
                queryset=PostCommentLike.objects.only('id')
            ),
            Prefetch(
                'postcommentreply_set',
                queryset=PostCommentReply.objects.only('id')
            ),
        ).only(
            'id',
            'content',
            'created_at',
            'updated_at',
            'user__id',
            'user__username',
            'status__id',
            'status__name'
        ).filter(
            post__team__id=pk,
            post__id=post_id,
            id=comment_id
        )

        if request.user.is_authenticated:
            comment = comment.annotate(
                liked=Exists(PostCommentLike.objects.filter(user=request.user, post_comment=OuterRef('pk')))
            )
            
        return comment.first()
    
    @staticmethod
    def get_10_popular_posts(request):
        posts = Post.objects.annotate(
            likes_count=Count('postlike'),
        ).order_by(
            '-likes_count'
        ).select_related(
            'user',
            'team',
            'status'
        ).prefetch_related(
            'postlike_set',
            'postcomment_set',
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                )
            ),
            Prefetch(
                'team__teamname_set',
                queryset=TeamName.objects.select_related('language')
            ),
            'user__teamlike_set',
        ).only(
            'id', 
            'title', 
            'created_at', 
            'updated_at', 
            'user__id', 
            'user__username', 
            'team__id', 
            'team__symbol', 
            'status__id', 
            'status__name'
        ).filter(
            created_at__gte=datetime.now() - timedelta(hours=24)
        ).exclude(
            Q(status__name='deleted') | Q(status__name='hidden')
        )

        if request.user.is_authenticated:
            posts = posts.annotate(
                liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
            )

        return posts[:10]
    
    @staticmethod
    def get_team_10_popular_posts(request, pk):
        posts = Post.objects.annotate(
            likes_count=Count('postlike'),
        ).filter(
            team__id=pk
        ).order_by(
            '-likes_count'
        ).select_related(
            'user',
            'team',
            'status'
        ).prefetch_related(
            'postlike_set',
            'postcomment_set',
            Prefetch(
                'status__poststatusdisplayname_set',
                queryset=PostStatusDisplayName.objects.select_related(
                    'language'
                )
            ),
            'user__teamlike_set',
        ).only(
            'id', 
            'title', 
            'created_at', 
            'updated_at', 
            'user__id', 
            'user__username', 
            'team__id', 
            'team__symbol', 
            'status__id', 
            'status__name'
        ).filter(
            created_at__gte=datetime.now() - timedelta(hours=24)
        ).exclude(
            Q(status__name='deleted') | Q(status__name='hidden')
        )

        if request.user.is_authenticated:
            posts = posts.annotate(
                liked=Exists(PostLike.objects.filter(user=request.user, post=OuterRef('pk')))
            )

        return posts[:10]
    
    @staticmethod
    def update_post(request, post):
        serializer = PostUpdateSerializer(post, data=request.data, partial=True) 
        serializer.is_valid(raise_exception=True)
        serializer.save()

    @staticmethod
    def delete_post(user_id, post_id):
        post = Post.objects.filter(user__id=user_id, id=post_id).first()

        if not post:
            return
        
        post.status = PostStatus.objects.get(name='deleted')
        post.save()

    @staticmethod
    def create_comment(request, post):
        if not request.user.is_authenticated:
            raise AnonymousUserError()

        serializer = PostCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post, user=request.user)

        NotificationService.create_notification_for_post_comment(post, request.user)
    
    @staticmethod
    def update_comment(request, comment):
        form = TeamPostCommentForm(request.data)
        if not form.is_valid():
            return False, form.errors.as_data()
        
        data = form.cleaned_data
        comment.content = data['content']
        comment.save()

        return True, None
    
    @staticmethod
    def delete_comment(user_id, comment_id):
        comment = PostComment.objects.filter(user__id=user_id, id=comment_id).first()

        if not comment:
            return
        
        comment.status = PostCommentStatus.objects.get(name='deleted')
        comment.save()
    
    @staticmethod
    def update_comment_via_serializer(request, comment):
        serializer = PostCommentUpdateSerializer(
            comment,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
    
    @staticmethod
    def get_comment_with_likes_only(request, pk, post_id, comment_id):
        comment = PostComment.objects.filter(
            post__team__id=pk,
            post__id=post_id,
            id=comment_id
        ).only('id')

        if request.user.is_authenticated:
            comment = comment.annotate(
                liked=Exists(PostCommentLike.objects.filter(user=request.user, post_comment=OuterRef('pk')))
            )

        return comment.first()

    @staticmethod
    def like_comment(request, comment):
        user = request.user
        if not user.is_authenticated:
            raise AnonymousUserError()

        PostCommentLike.objects.get_or_create(
            user=user,
            post_comment=comment
        )

        likes_count = PostCommentLike.objects.filter(post_comment=comment).count()
        if likes_count % 10 == 0 and likes_count != 0:
            NotificationService.create_notification_for_post_comment_likes(
                comment, 
                likes_count, 
                user
            )
    
    @staticmethod
    def unlike_comment(request, pk, post_id, comment_id):
        user = request.user
        try:
            like = PostCommentLike.objects.get(user=user, post_comment__id=comment_id)
            like.delete()
        except PostCommentLike.DoesNotExist:
            pass

        return PostService.get_comment_with_likes_only(request, pk, post_id, comment_id)
    
    @staticmethod
    def create_comment_reply(request, comment):
        if not request.user.is_authenticated:
            raise AnonymousUserError()

        serializer = PostCommentReplyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply = serializer.save(post_comment=comment, user=request.user)

        replies_count = comment.postcommentreply_set.count()

        if replies_count % 10 == 0 and replies_count != 0:
            NotificationService.create_notification_for_post_comment_reply(
                reply, 
                replies_count, 
                request.user
            )

    @staticmethod
    def get_comment_replies(comment_id):
        return PostCommentReply.objects.filter(
            post_comment__id=comment_id
        ).select_related(
            'user',
            'status'
        ).only(
            'id',
            'content',
            'created_at',
            'updated_at',
            'user__id',
            'user__username',
            'status__id',
            'status__name'
        ).order_by('-created_at')
    

class PostSerializerService:
    @staticmethod
    def serialize_post_statuses(statuses):
        return PostStatusSerializer(
            statuses, 
            many=True,
            context={
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_post_comment_statuses(statuses):
        return PostCommentStatusSerializer(
            statuses, 
            many=True,
            context={
                'postcommentstatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_posts(request, posts):
        fields_exclude = ['content']
        if not request.user.is_authenticated:
            fields_exclude.append('liked')

        return PostSerializer(
            posts,
            many=True,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username', 'favorite_team')
                },
                'team': {
                    'fields': ('id', 'symbol', 'teamname_set')
                },
                'teamname': {
                    'fields': ('name', 'language')
                },
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_posts_without_liked(posts):
        fields_exclude = ['content', 'liked']
        return PostSerializer(
            posts,
            many=True,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'team': {
                    'fields': ('id', 'symbol')
                },
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_post(request, post):
        fields_exclude = []
        if not request.user.is_authenticated:
            fields_exclude.append('liked')

        return PostSerializer(
            post,
            fields_exclude=fields_exclude,
            context={
                'team': {
                    'fields': ['id', 'symbol']
                },
                'user': {
                    'fields': ('id', 'username')
                },
                'poststatusdisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_post_after_like(request, post):
        fields = ['id', 'likes_count']
        if request.user.is_authenticated:
            fields.append('liked')

        return PostSerializer(
            post,
            fields=fields,
        )
    
    @staticmethod
    def serialize_comments_for_post(request, comments):
        fields_exclude = ['post_data']
        if not request.user.is_authenticated:
            fields_exclude.append('liked')

        return PostCommentSerializer(
            comments,
            many=True,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                }
            }
        )
    
    @staticmethod
    def serialize_comment(request, comment):
        fields_exclude = ['post_data']
        if not request.user.is_authenticated:
            fields_exclude.append('liked')

        return PostCommentSerializer(
            comment,
            fields_exclude=fields_exclude,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                }
            }
        )
    
    @staticmethod
    def serialize_comment_with_likes_only(request, comment):
        fields = ['id', 'likes_count'] 
        if request.user.is_authenticated:
            fields.append('liked')

        return PostCommentSerializer(
            comment,
            fields=fields
        )

    @staticmethod
    def serialize_comment_after_like(comment):
        return PostCommentSerializer(
            comment,
            fields=['id', 'likes_count', 'liked']
        )
    
    @staticmethod
    def serialize_comment_replies(replies):
        return PostCommentReplySerializer(
            replies,
            many=True,
            fields_exclude=['post_comment_data'],
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                }
            }
        )