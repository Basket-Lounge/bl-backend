from django.db import models


class Player(models.Model):
    # Basic player information
    id = models.IntegerField(primary_key=True)  # Unique player identifier
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, unique=True)  # Slug for URLs

    # Team information
    team = models.ForeignKey(
        'teams.Team', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )

    # Player profile details
    jersey_number = models.CharField(
        max_length=10, 
        blank=True, 
        null=True
    )  # Jersey number can be alphanumeric
    position = models.CharField(max_length=20, null=True)  # Position, e.g., "G" or "F-C"
    height = models.CharField(max_length=10)  # Height in format like "6-7"
    weight = models.FloatField(null=True)  # Weight in pounds
    college = models.CharField(max_length=100, blank=True, null=True)  # College may be missing for international players
    country = models.CharField(max_length=100)  # Player's country

    # Draft information
    draft_year = models.IntegerField(null=True, blank=True)
    draft_round = models.IntegerField(null=True, blank=True)
    draft_number = models.IntegerField(null=True, blank=True)

    # Roster status and career details
    roster_status = models.FloatField(null=True)  # Status indicating active roster, usually 1.0 for active
    from_year = models.IntegerField(null=True)  # First year in the league
    to_year = models.IntegerField(null=True)  # Last active or current year
    stats_timeframe = models.CharField(max_length=20, default="Season")  # Default "Season"

    # Optional player stats
    pts = models.FloatField(null=True, blank=True)  # Points per game
    reb = models.FloatField(null=True, blank=True)  # Rebounds per game
    ast = models.FloatField(null=True, blank=True)  # Assists per game

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.id})"


class PlayerStatistics(models.Model):
    # Link to Player
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    game = models.ForeignKey(
        'games.Game', 
        on_delete=models.CASCADE, 
        default=None, 
        null=True
    )
    team = models.ForeignKey(
        'teams.Team', 
        on_delete=models.CASCADE, 
        default=None,
        null=True
    )

    # Game status details
    status = models.CharField(
        max_length=10, 
        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")]
    )
    order = models.IntegerField()  # Player's order in the lineup
    position = models.CharField(
        max_length=5, 
        null=True, 
        blank=True
    )  # Position, e.g., SF, PF, etc.
    starter = models.BooleanField(default=False)  # Whether the player started the game

    # Game statistics
    assists = models.IntegerField()
    blocks = models.IntegerField()
    blocks_received = models.IntegerField()
    field_goals_attempted = models.IntegerField()
    field_goals_made = models.IntegerField()
    field_goals_percentage = models.FloatField()
    fouls_offensive = models.IntegerField()
    fouls_drawn = models.IntegerField()
    fouls_personal = models.IntegerField()
    fouls_technical = models.IntegerField()
    free_throws_attempted = models.IntegerField()
    free_throws_made = models.IntegerField()
    free_throws_percentage = models.FloatField()
    minus = models.FloatField()
    minutes = models.CharField(max_length=20)  # Duration field to represent time played
    plus = models.FloatField()
    plus_minus_points = models.FloatField()
    points = models.IntegerField()
    points_fast_break = models.IntegerField()
    points_in_the_paint = models.IntegerField()
    points_second_chance = models.IntegerField()
    rebounds_defensive = models.IntegerField()
    rebounds_offensive = models.IntegerField()
    rebounds_total = models.IntegerField()
    steals = models.IntegerField()
    three_pointers_attempted = models.IntegerField()
    three_pointers_made = models.IntegerField()
    three_pointers_percentage = models.FloatField()
    turnovers = models.IntegerField()
    two_pointers_attempted = models.IntegerField()
    two_pointers_made = models.IntegerField()
    two_pointers_percentage = models.FloatField()

    class Meta:
        unique_together = ('player', 'game')

    def __str__(self):
        return f"{self.player.first_name} {self.player.last_name} - {self.game.game_code}"

    
class PlayerCareerStatistics(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE, 
        default=None, 
        null=True
    )
    season_id = models.CharField(max_length=20)
    player_age = models.FloatField()
    games_played = models.IntegerField()
    games_started = models.IntegerField()
    minutes = models.FloatField()  # Renamed from 'min' to 'minutes' to avoid conflict with the built-in 'min' function
    field_goals_made = models.FloatField()
    field_goals_attempted = models.FloatField()
    field_goals_percentage = models.FloatField()
    three_point_field_goals_made = models.FloatField()
    three_point_field_goals_attempted = models.FloatField()
    three_point_field_goals_percentage = models.FloatField()
    free_throws_made = models.FloatField()
    free_throws_attempted = models.FloatField()
    free_throws_percentage = models.FloatField()
    rebounds_offensive = models.FloatField()
    rebounds_defensive = models.FloatField()
    rebounds_total = models.FloatField()
    assists = models.FloatField()
    steals = models.FloatField()
    blocks = models.FloatField()
    turnovers = models.FloatField()
    personal_fouls = models.FloatField()
    points = models.FloatField()

    class Meta:
        unique_together = ('player', 'season_id', 'team')  # Ensures unique records for a player-season-team combination

    def __str__(self):
        return f"{self.player.first_name} {self.player.last_name} - {self.season_id}"

