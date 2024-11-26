from celery import shared_task
from django.conf import settings
from django.db import transaction

from nba_api.stats.endpoints.leagueleaders import LeagueLeaders

from players.models import PlayerRanking


@shared_task
def update_top_10_players():
    leaders = LeagueLeaders(
        league_id='00',
        per_mode48='PerGame',
        scope='S',
        season=settings.SEASON_YEAR,
        season_type_all_star='Regular Season',
        stat_category_abbreviation='PTS'
    )
    results = leaders.get_dict()
    top_10 = results['resultSet']['rowSet'][:10]

    with transaction.atomic():
        PlayerRanking.objects.all().delete()

        for index in range(len(top_10)):
            PlayerRanking.objects.create(
                ranking=index + 1,
                player_id=top_10[index][0],
            )