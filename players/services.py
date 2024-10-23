from players.models import Player
from teams.models import Team

from nba_api.stats.endpoints.playerindex import PlayerIndex

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