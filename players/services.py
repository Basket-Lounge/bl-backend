from players.models import Player, PlayerCareerStatistics
from teams.models import Team

from nba_api.stats.endpoints.playerindex import PlayerIndex
from nba_api.stats.endpoints.playercareerstats import PlayerCareerStats


def register_players_to_database():
    '''
    Initial registration of players to the database. Must be run once after the initial migration.
    '''

    teams = Team.objects.all()

    for team in teams:
        team_players = PlayerIndex(
            team_id_nullable=f'{team.id}',
            season='2024-25',
            league_id='00'
        ).get_dict()['resultSets'][0]

        headers = team_players['headers']
        players = team_players['rowSet']

        players_dict = [dict(zip(headers, player)) for player in players]
        print(players_dict)
        Player.objects.bulk_create([
            Player(
                id=player['PERSON_ID'],
                last_name=player['PLAYER_LAST_NAME'],
                first_name=player['PLAYER_FIRST_NAME'],
                slug=player['PLAYER_SLUG'],
                team=team,
                jersey_number=player['JERSEY_NUMBER'],
                position=player['POSITION'],
                height=player['HEIGHT'],
                weight=player['WEIGHT'],
                college=player['COLLEGE'],
                country=player['COUNTRY'],
                draft_year=player['DRAFT_YEAR'],
                draft_round=player['DRAFT_ROUND'],
                draft_number=player['DRAFT_NUMBER'],
                roster_status=player['ROSTER_STATUS'],
                from_year=player['FROM_YEAR'],
                to_year=player['TO_YEAR'],
                stats_timeframe=player['STATS_TIMEFRAME'],
                pts=player['PTS'],
                reb=player['REB'],
                ast=player['AST']
            ) for player in players_dict
        ])


def update_players():
    teams = Team.objects.all()

    removed_players = set()
    for team in teams:
        team_players = PlayerIndex(
            team_id_nullable=f'{team.id}',
            season='2024-25',
            league_id='00'
        ).get_dict()['resultSets'][0]

        headers = team_players['headers']
        players = team_players['rowSet']

        players_dict = [dict(zip(headers, player)) for player in players]
        removed_players_from_team_query = Player.objects.filter(team=team).exclude(id__in=[player['PERSON_ID'] for player in players_dict]) 
        removed_players.update(removed_players_from_team_query.values_list('id', flat=True))

        for player in players_dict:
            print(f"Updating player {player['PERSON_ID']}, {player['PLAYER_LAST_NAME']} {player['PLAYER_FIRST_NAME']}")
            if player['PERSON_ID'] in removed_players:
                removed_players.remove(player['PERSON_ID'])

            player_instance, created = Player.objects.update_or_create(id=player['PERSON_ID'], defaults={
                'last_name': player['PLAYER_LAST_NAME'],
                'first_name': player['PLAYER_FIRST_NAME'],
                'slug': player['PLAYER_SLUG'],
                'team': team,
                'jersey_number': player['JERSEY_NUMBER'],
                'position': player['POSITION'],
                'height': player['HEIGHT'],
                'weight': player['WEIGHT'],
                'college': player['COLLEGE'],
                'country': player['COUNTRY'],
                'draft_year': player['DRAFT_YEAR'],
                'draft_round': player['DRAFT_ROUND'],
                'draft_number': player['DRAFT_NUMBER'],
                'roster_status': player['ROSTER_STATUS'],
                'from_year': player['FROM_YEAR'],
                'to_year': player['TO_YEAR'],
                'stats_timeframe': player['STATS_TIMEFRAME'],
                'pts': player['PTS'],
                'reb': player['REB'],
                'ast': player['AST']
            })
            print("Created", created)

            player_instance.save()

    # Update players that are no longer in the team
    updated_number = Player.objects.filter(id__in=list(removed_players)).update(team=None)
    print(f'Updated {updated_number} players')

def add_career_stats_to_players():
    players = Player.objects.all()

    for player in players:
        try:
            career_stats = PlayerCareerStats(
                player_id=f'{player.id}',
                per_mode36='PerGame'
            ).get_dict()['resultSets'][0]
        except Exception as e:
            print("Error fetching career stats for player", player.id, e)
            continue

        headers = career_stats['headers']
        stats = career_stats['rowSet']

        if not stats:
            continue

        stats_dict = [dict(zip(headers, season_stats)) for season_stats in stats]

        PlayerCareerStatistics.objects.bulk_create([
            PlayerCareerStatistics(
                player=player,
                team=Team.objects.get(id=season_stats['TEAM_ID']) if season_stats['TEAM_ID'] != 0 else None,
                season_id=season_stats['SEASON_ID'],
                player_age=season_stats['PLAYER_AGE'],
                games_played=season_stats['GP'],
                games_started=season_stats['GS'],
                minutes=season_stats['MIN'],
                field_goals_made=season_stats['FGM'],
                field_goals_attempted=season_stats['FGA'],
                field_goals_percentage=season_stats['FG_PCT'],
                three_point_field_goals_made=season_stats['FG3M'],
                three_point_field_goals_attempted=season_stats['FG3A'],
                three_point_field_goals_percentage=season_stats['FG3_PCT'],
                free_throws_made=season_stats['FTM'],
                free_throws_attempted=season_stats['FTA'],
                free_throws_percentage=season_stats['FT_PCT'],
                rebounds_offensive=season_stats['OREB'],
                rebounds_defensive=season_stats['DREB'],
                rebounds_total=season_stats['REB'],
                assists=season_stats['AST'],
                steals=season_stats['STL'],
                blocks=season_stats['BLK'],
                turnovers=season_stats['TOV'],
                personal_fouls=season_stats['PF'],
                points=season_stats['PTS']
            ) for season_stats in stats_dict
        ])

        print(f"Updated player {player.id}, {player.last_name} {player.first_name}")