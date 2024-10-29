from players.models import Player, PlayerCareerStatistics
from teams.models import Team

from nba_api.stats.endpoints.playerindex import PlayerIndex
from nba_api.stats.endpoints.playercareerstats import PlayerCareerStats

# class Player(models.Model):
#     # Basic player information
#     id = models.IntegerField(primary_key=True)  # Unique player identifier
#     last_name = models.CharField(max_length=100)
#     first_name = models.CharField(max_length=100)
#     slug = models.SlugField(max_length=150, unique=True)  # Slug for URLs

#     # Team information
#     team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, null=True, blank=True)

#     # Player profile details
#     jersey_number = models.CharField(max_length=10, blank=True, null=True)  # Jersey number can be alphanumeric
#     position = models.CharField(max_length=20)  # Position, e.g., "G" or "F-C"
#     height = models.CharField(max_length=10)  # Height in format like "6-7"
#     weight = models.FloatField()  # Weight in pounds
#     college = models.CharField(max_length=100, blank=True, null=True)  # College may be missing for international players
#     country = models.CharField(max_length=100)  # Player's country

#     # Draft information
#     draft_year = models.IntegerField(null=True, blank=True)
#     draft_round = models.IntegerField(null=True, blank=True)
#     draft_number = models.IntegerField(null=True, blank=True)

#     # Roster status and career details
#     roster_status = models.FloatField()  # Status indicating active roster, usually 1.0 for active
#     from_year = models.IntegerField()  # First year in the league
#     to_year = models.IntegerField()  # Last active or current year
#     stats_timeframe = models.CharField(max_length=20, default="Season")  # Default "Season"

#     # Optional player stats
#     pts = models.FloatField(null=True, blank=True)  # Points per game
#     reb = models.FloatField(null=True, blank=True)  # Rebounds per game
#     ast = models.FloatField(null=True, blank=True)  # Assists per game

#     def __str__(self):
#         return f"{self.player_first_name} {self.player_last_name} ({self.person_id})"


# "PlayerIndex": [
#             "PERSON_ID",
#             "PLAYER_LAST_NAME",
#             "PLAYER_FIRST_NAME",
#             "PLAYER_SLUG",
#             "TEAM_ID",
#             "TEAM_SLUG",
#             "IS_DEFUNCT",
#             "TEAM_CITY",
#             "TEAM_NAME",
#             "TEAM_ABBREVIATION",
#             "JERSEY_NUMBER",
#             "POSITION",
#             "HEIGHT",
#             "WEIGHT",
#             "COLLEGE",
#             "COUNTRY",
#             "DRAFT_YEAR",
#             "DRAFT_ROUND",
#             "DRAFT_NUMBER",
#             "ROSTER_STATUS",
#             "PTS",
#             "REB",
#             "AST",
#             "STATS_TIMEFRAME",
#             "FROM_YEAR",
#             "TO_YEAR"
#         ]

def register_players_to_database():
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

    updated_number = Player.objects.filter(id__in=list(removed_players)).update(team=None)
    print(f'Updated {updated_number} players')


# [
#     {
#         "PLAYER_ID": 1629726,
#         "SEASON_ID": "2019-20",
#         "LEAGUE_ID": "00",
#         "TEAM_ID": 1610612764,
#         "TEAM_ABBREVIATION": "WAS",
#         "PLAYER_AGE": 23.0,
#         "GP": 18,
#         "GS": 0,
#         "MIN": 12.6,
#         "FGM": 1.3,
#         "FGA": 3.1,
#         "FG_PCT": 0.429,
#         "FG3M": 1.1,
#         "FG3A": 2.6,
#         "FG3_PCT": 0.413,
#         "FTM": 1.7,
#         "FTA": 1.9,
#         "FT_PCT": 0.912,
#         "OREB": 0.3,
#         "DREB": 1.0,
#         "REB": 1.3,
#         "AST": 0.6,
#         "STL": 0.4,
#         "BLK": 0.1,
#         "TOV": 0.4,
#         "PF": 1.8,
#         "PTS": 5.4
#     },
#     {
#         "PLAYER_ID": 1629726,
#         "SEASON_ID": "2020-21",
#         "LEAGUE_ID": "00",
#         "TEAM_ID": 1610612764,
#         "TEAM_ABBREVIATION": "WAS",
#         "PLAYER_AGE": 24.0,
#         "GP": 64,
#         "GS": 24,
#         "MIN": 16.2,
#         "FGM": 1.5,
#         "FGA": 3.7,
#         "FG_PCT": 0.409,
#         "FG3M": 1.2,
#         "FG3A": 3.1,
#         "FG3_PCT": 0.384,
#         "FTM": 1.3,
#         "FTA": 1.5,
#         "FT_PCT": 0.884,
#         "OREB": 0.3,
#         "DREB": 1.1,
#         "REB": 1.4,
#         "AST": 0.4,
#         "STL": 0.5,
#         "BLK": 0.1,
#         "TOV": 0.2,
#         "PF": 1.7,
#         "PTS": 5.5
#     },
#     {
#         "PLAYER_ID": 1629726,
#         "SEASON_ID": "2021-22",
#         "LEAGUE_ID": "00",
#         "TEAM_ID": 1610612745,
#         "TEAM_ABBREVIATION": "HOU",
#         "PLAYER_AGE": 25.0,
#         "GP": 65,
#         "GS": 33,
#         "MIN": 26.3,
#         "FGM": 2.8,
#         "FGA": 7.1,
#         "FG_PCT": 0.399,
#         "FG3M": 2.1,
#         "FG3A": 5.9,
#         "FG3_PCT": 0.36,
#         "FTM": 2.2,
#         "FTA": 2.8,
#         "FT_PCT": 0.794,
#         "OREB": 0.5,
#         "DREB": 2.4,
#         "REB": 2.9,
#         "AST": 1.0,
#         "STL": 0.9,
#         "BLK": 0.4,
#         "TOV": 0.6,
#         "PF": 2.6,
#         "PTS": 10.0
#     },
#     {
#         "PLAYER_ID": 1629726,
#         "SEASON_ID": "2022-23",
#         "LEAGUE_ID": "00",
#         "TEAM_ID": 1610612745,
#         "TEAM_ABBREVIATION": "HOU",
#         "PLAYER_AGE": 26.0,
#         "GP": 45,
#         "GS": 0,
#         "MIN": 13.4,
#         "FGM": 1.3,
#         "FGA": 3.8,
#         "FG_PCT": 0.353,
#         "FG3M": 1.2,
#         "FG3A": 3.4,
#         "FG3_PCT": 0.342,
#         "FTM": 0.9,
#         "FTA": 1.0,
#         "FT_PCT": 0.911,
#         "OREB": 0.2,
#         "DREB": 1.2,
#         "REB": 1.4,
#         "AST": 0.5,
#         "STL": 0.5,
#         "BLK": 0.1,
#         "TOV": 0.4,
#         "PF": 1.2,
#         "PTS": 4.8
#     },
#     {
#         "PLAYER_ID": 1629726,
#         "SEASON_ID": "2022-23",
#         "LEAGUE_ID": "00",
#         "TEAM_ID": 1610612737,
#         "TEAM_ABBREVIATION": "ATL",
#         "PLAYER_AGE": 26.0,
#         "GP": 9,
#         "GS": 0,
#         "MIN": 9.4,
#         "FGM": 1.4,
#         "FGA": 3.4,
#         "FG_PCT": 0.419,
#         "FG3M": 1.1,
#         "FG3A": 2.8,
#         "FG3_PCT": 0.4,
#         "FTM": 0.8,
#         "FTA": 0.9,
#         "FT_PCT": 0.875,
#         "OREB": 0.1,
#         "DREB": 1.1,
#         "REB": 1.2,
#         "AST": 0.3,
#         "STL": 0.1,
#         "BLK": 0.1,
#         "TOV": 0.1,
#         "PF": 0.7,
#         "PTS": 4.8
#     },
#     {
#         "PLAYER_ID": 1629726,
#         "SEASON_ID": "2022-23",
#         "LEAGUE_ID": "00",
#         "TEAM_ID": 0,
#         "TEAM_ABBREVIATION": "TOT",
#         "PLAYER_AGE": 26.0,
#         "GP": 54,
#         "GS": 0,
#         "MIN": 12.7,
#         "FGM": 1.4,
#         "FGA": 3.7,
#         "FG_PCT": 0.363,
#         "FG3M": 1.2,
#         "FG3A": 3.3,
#         "FG3_PCT": 0.35,
#         "FTM": 0.9,
#         "FTA": 1.0,
#         "FT_PCT": 0.906,
#         "OREB": 0.2,
#         "DREB": 1.1,
#         "REB": 1.4,
#         "AST": 0.5,
#         "STL": 0.4,
#         "BLK": 0.1,
#         "TOV": 0.4,
#         "PF": 1.1,
#         "PTS": 4.8
#     },
#     {
#         "PLAYER_ID": 1629726,
#         "SEASON_ID": "2023-24",
#         "LEAGUE_ID": "00",
#         "TEAM_ID": 1610612737,
#         "TEAM_ABBREVIATION": "ATL",
#         "PLAYER_AGE": 27.0,
#         "GP": 66,
#         "GS": 5,
#         "MIN": 15.0,
#         "FGM": 1.6,
#         "FGA": 3.4,
#         "FG_PCT": 0.456,
#         "FG3M": 1.3,
#         "FG3A": 2.9,
#         "FG3_PCT": 0.44,
#         "FTM": 0.5,
#         "FTA": 0.6,
#         "FT_PCT": 0.81,
#         "OREB": 0.3,
#         "DREB": 1.1,
#         "REB": 1.4,
#         "AST": 0.6,
#         "STL": 0.3,
#         "BLK": 0.1,
#         "TOV": 0.3,
#         "PF": 1.7,
#         "PTS": 4.9
#     },
#     {
#         "PLAYER_ID": 1629726,
#         "SEASON_ID": "2024-25",
#         "LEAGUE_ID": "00",
#         "TEAM_ID": 1610612737,
#         "TEAM_ABBREVIATION": "ATL",
#         "PLAYER_AGE": 28.0,
#         "GP": 1,
#         "GS": 0,
#         "MIN": 18.5,
#         "FGM": 2.0,
#         "FGA": 3.0,
#         "FG_PCT": 0.667,
#         "FG3M": 2.0,
#         "FG3A": 3.0,
#         "FG3_PCT": 0.667,
#         "FTM": 2.0,
#         "FTA": 2.0,
#         "FT_PCT": 1.0,
#         "OREB": 0.0,
#         "DREB": 1.0,
#         "REB": 1.0,
#         "AST": 0.0,
#         "STL": 0.0,
#         "BLK": 0.0,
#         "TOV": 0.0,
#         "PF": 2.0,
#         "PTS": 8.0
#     }
# ]

# class PlayerCareerStatistics(models.Model):
#     player = models.ForeignKey(Player, on_delete=models.CASCADE)
#     team = models.ForeignKey(
#         'teams.Team', 
#         on_delete=models.CASCADE, 
#         default=None, 
#         null=True
#     )
#     season_id = models.CharField(max_length=20)
#     player_age = models.FloatField()
#     games_played = models.IntegerField()
#     games_started = models.IntegerField()
#     minutes = models.FloatField()  # Renamed from 'min' to 'minutes' to avoid conflict with the built-in 'min' function
#     field_goals_made = models.FloatField()
#     field_goals_attempted = models.FloatField()
#     field_goals_percentage = models.FloatField()
#     three_point_field_goals_made = models.FloatField()
#     three_point_field_goals_attempted = models.FloatField()
#     three_point_field_goals_percentage = models.FloatField()
#     free_throws_made = models.FloatField()
#     free_throws_attempted = models.FloatField()
#     free_throws_percentage = models.FloatField()
#     rebounds_offensive = models.FloatField()
#     rebounds_defensive = models.FloatField()
#     rebounds_total = models.FloatField()
#     assists = models.FloatField()
#     steals = models.FloatField()
#     blocks = models.FloatField()
#     turnovers = models.FloatField()
#     personal_fouls = models.FloatField()
#     points = models.FloatField()

#     class Meta:
#         unique_together = ('player', 'season_id', 'team')  # Ensures unique records for a player-season-team combination

#     def __str__(self):
#         return f"{self.player.first_name} {self.player.last_name} - {self.season_id}"


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