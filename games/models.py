import uuid
from django.db import models


class Game(models.Model):
    """
    Model representing a basketball game.
    """
    game_id = models.CharField(
        primary_key=True,
        max_length=50,
        help_text="Unique identifier for the game (e.g., '0022400061')."
    )
    game_date_est = models.DateTimeField(
        help_text="Scheduled date and time of the game in Eastern Standard Time."
    )
    game_sequence = models.IntegerField(
        help_text="Sequence number of the game within the season."
    )
    game_status_id = models.IntegerField(
        help_text="Status identifier of the game (e.g., 1 for scheduled, 2 for in-progress)."
    )
    game_status_text = models.CharField(
        max_length=50,
        help_text="Descriptive status text (e.g., '7:30 pm ET')."
    )
    game_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Game code (e.g., '20241022/NYKBOS')."
    )
    home_team = models.ForeignKey(
        'teams.Team',
        related_name='home_games',
        on_delete=models.CASCADE,
        help_text="Home team participating in the game."
    )
    visitor_team = models.ForeignKey(
        'teams.Team',
        related_name='visitor_games',
        on_delete=models.CASCADE,
        help_text="Visitor team participating in the game."
    )
    season = models.CharField(
        max_length=10,
        help_text="Season year (e.g., '2024')."
    )
    live_period = models.IntegerField(
        help_text="Current live period of the game."
    )
    live_pc_time = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Live PC time (if applicable)."
    )
    natl_tv_broadcaster_abbreviation = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="National TV broadcaster abbreviation (e.g., 'TNT')."
    )
    home_tv_broadcaster_abbreviation = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Home TV broadcaster abbreviation."
    )
    away_tv_broadcaster_abbreviation = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Away TV broadcaster abbreviation."
    )
    live_period_time_bcast = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Live period time broadcast information (e.g., 'Q0 - TNT')."
    )
    arena_name = models.CharField(
        max_length=100,
        help_text="Name of the arena where the game is held (e.g., 'TD Garden')."
    )
    wh_status = models.BooleanField(
        default=False,
        help_text="WH status flag."
    )
    wnba_commissioner_flag = models.BooleanField(
        default=False,
        help_text="WNBA commissioner flag."
    )
    available_pt_available = models.BooleanField(
        default=False,
        help_text="Availability status of points."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time the game was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time the game was last updated."
    )

    class Meta:
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        ordering = ['-game_date_est']

    def __str__(self):
        return f"Game {self.game_code}: {self.home_team} vs {self.visitor_team} on {self.game_date_est.strftime('%Y-%m-%d %H:%M')}"
    
    def game_date_est_local_time(self, timezone='US/Eastern'):
        """
        Returns the game date and time in the local timezone.
        """
        return self.game_date_est.astimezone(timezone)


class GameChat(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    game = models.OneToOneField(
        Game,
        on_delete=models.CASCADE,
        related_name='game_chat'
    )
    slow_mode = models.BooleanField(default=False)
    slow_mode_time = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f'Chat {self.id}'
    

class GameChatMessage(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    chat = models.ForeignKey(
        GameChat, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} in {self.chat}'
    

class GameChatMute(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    chat = models.ForeignKey(
        GameChat, 
        on_delete=models.CASCADE, 
        related_name='mutes'
    )
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} in {self.chat} muted'
    

class GameChatBan(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user}'

class GamePrediction(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE
    )
    game = models.ForeignKey(
        GameChat,
        on_delete=models.CASCADE
    )
    prediction = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} prediction for {self.game}'    
    
    class Meta:
        unique_together = ['user', 'game']


class LineScore(models.Model):
    """
    Model representing the line score details for a team in a specific game.
    """

    line_score_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="Unique identifier for the line score entry."
    )
    game = models.ForeignKey(
        'Game',
        related_name='line_scores',
        on_delete=models.CASCADE,
        help_text="Associated game identifier."
    )
    team = models.ForeignKey(
        'teams.Team',
        related_name='line_scores',
        on_delete=models.CASCADE,
        help_text="Team identifier."
    )
    pts_qtr1 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Quarter 1."
    )
    pts_qtr2 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Quarter 2."
    )
    pts_qtr3 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Quarter 3."
    )
    pts_qtr4 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Quarter 4."
    )
    pts_ot1 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 1."
    )
    pts_ot2 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 2."
    )
    pts_ot3 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 3."
    )
    pts_ot4 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 4."
    )
    pts_ot5 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 5."
    )
    pts_ot6 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 6."
    )
    pts_ot7 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 7."
    )
    pts_ot8 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 8."
    )
    pts_ot9 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 9."
    )
    pts_ot10 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points scored in Overtime 10."
    )
    fg_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Field Goal Percentage (e.g., 45.67)."
    )
    ft_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Free Throw Percentage (e.g., 78.90)."
    )
    fg3_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="3-Point Field Goal Percentage (e.g., 35.50)."
    )
    ast = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of assists."
    )
    reb = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of rebounds."
    )
    tov = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of turnovers."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time the line score was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time the line score was last updated."
    )

    class Meta:
        db_table = 'LineScores'  # Specify the exact database table name
        verbose_name = 'Line Score'
        verbose_name_plural = 'Line Scores'
        ordering = ['game__game_date_est']
        indexes = [
            models.Index(fields=['game', 'team']),
        ]
        unique_together = ('game', 'team')  # Ensure one line score per team per game

    def __str__(self):
        return f"{self.team.symbol} - {self.game.game_code}"


class TeamStatistics(models.Model):
    # Basic team information (you might want to link it to a Team model)
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)

    # Game statistics
    assists = models.IntegerField()
    assists_turnover_ratio = models.FloatField()
    bench_points = models.IntegerField()
    biggest_lead = models.IntegerField()
    biggest_lead_score = models.CharField(max_length=50)
    biggest_scoring_run = models.IntegerField()
    biggest_scoring_run_score = models.CharField(max_length=50)
    blocks = models.IntegerField()
    blocks_received = models.IntegerField()
    fast_break_points_attempted = models.IntegerField()
    fast_break_points_made = models.IntegerField()
    fast_break_points_percentage = models.FloatField()
    field_goals_attempted = models.IntegerField()
    field_goals_effective_adjusted = models.FloatField()
    field_goals_made = models.IntegerField()
    field_goals_percentage = models.FloatField()
    fouls_offensive = models.IntegerField()
    fouls_drawn = models.IntegerField()
    fouls_personal = models.IntegerField()
    fouls_team = models.IntegerField()
    fouls_technical = models.IntegerField()
    fouls_team_technical = models.IntegerField()
    free_throws_attempted = models.IntegerField()
    free_throws_made = models.IntegerField()
    free_throws_percentage = models.FloatField()
    lead_changes = models.IntegerField()
    minutes = models.CharField(max_length=20)  # Using Django's DurationField for handling time durations
    points = models.IntegerField()
    points_against = models.IntegerField()
    points_fast_break = models.IntegerField()
    points_from_turnovers = models.IntegerField()
    points_in_the_paint = models.IntegerField()
    points_in_the_paint_attempted = models.IntegerField()
    points_in_the_paint_made = models.IntegerField()
    points_in_the_paint_percentage = models.FloatField()
    points_second_chance = models.IntegerField()
    rebounds_defensive = models.IntegerField()
    rebounds_offensive = models.IntegerField()
    rebounds_personal = models.IntegerField()
    rebounds_team = models.IntegerField()
    rebounds_team_defensive = models.IntegerField()
    rebounds_team_offensive = models.IntegerField()
    rebounds_total = models.IntegerField()
    second_chance_points_attempted = models.IntegerField()
    second_chance_points_made = models.IntegerField()
    second_chance_points_percentage = models.FloatField()
    steals = models.IntegerField()
    three_pointers_attempted = models.IntegerField()
    three_pointers_made = models.IntegerField()
    three_pointers_percentage = models.FloatField()
    time_leading = models.CharField(max_length=20)  # Using DurationField to represent time leading
    times_tied = models.IntegerField()
    true_shooting_attempts = models.FloatField()
    true_shooting_percentage = models.FloatField()
    turnovers = models.IntegerField()
    turnovers_team = models.IntegerField()
    turnovers_total = models.IntegerField()
    two_pointers_attempted = models.IntegerField()
    two_pointers_made = models.IntegerField()
    two_pointers_percentage = models.FloatField()

    class Meta:
        verbose_name = 'Team Statistics'
        verbose_name_plural = 'Team Statistics'
        ordering = ['game__game_date_est']
        unique_together = ['team', 'game']

    def __str__(self):
        return f"{self.team.symbol} - {self.points} Points"