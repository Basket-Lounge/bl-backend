def convert_month_string_to_int(month):
    months = {
        'january': 1,
        'february': 2,
        'march': 3,
        'april': 4,
        'may': 5,
        'june': 6,
        'july': 7,
        'august': 8,
        'september': 9,
        'october': 10,
        'november': 11,
        'december': 12,
    }

    return months.get(month.lower(), None)

'''
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

'''

def create_empty_player_season_stats():
    return {
        "games_played": 0,
        "games_started": 0,
        "minutes": 0.0,
        "field_goals_made": 0.0,
        "field_goals_attempted": 0.0,
        "field_goals_percentage": 0.0,
        "three_point_field_goals_made": 0.0,
        "three_point_field_goals_attempted": 0.0,
        "three_point_field_goals_percentage": 0.0,
        "free_throws_made": 0.0,
        "free_throws_attempted": 0.0,
        "free_throws_percentage": 0.0,
        "rebounds_offensive": 0.0,
        "rebounds_defensive": 0.0,
        "rebounds_total": 0.0,
        "assists": 0.0,
        "steals": 0.0,
        "blocks": 0.0,
        "turnovers": 0.0,
        "personal_fouls": 0.0,
        "points": 0.0,
    }

def calculate_time(time_str):
    '''
    "7:30 pm ET"
    '''
    clock_str = time_str.split(' ')[0]
    day_or_night = time_str.split(' ')[1]
    hours, minutes = clock_str.split(':')

    if 'pm' in day_or_night and int(hours) < 12:
        hours = int(hours) + 12

    return int(hours), int(minutes)