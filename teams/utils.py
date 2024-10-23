from django.conf import settings

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


def create_empty_player_season_stats(
    team_abbreviation, 
    team_id,
    player_age,
    player_id,
):
    return {
        "PLAYER_ID": player_id,
        "SEASON_ID": settings.SEASON_YEAR,
        "LEAGUE_ID": "00",
        "TEAM_ID": int(team_id),
        "TEAM_ABBREVIATION": team_abbreviation,
        "PLAYER_AGE": player_age,
        "GP": 0,
        "GS": 0,
        "MIN": 0.0,
        "FGM": 0.0,
        "FGA": 0.0,
        "FG_PCT": 0.0,
        "FG3M": 0.0,
        "FG3A": 0.0,
        "FG3_PCT": 0.0,
        "FTM": 0.0,
        "FTA": 0.0,
        "FT_PCT": 0.0,
        "OREB": 0.0,
        "DREB": 0.0,
        "REB": 0.0,
        "AST": 0.0,
        "STL": 0.0,
        "BLK": 0.0,
        "TOV": 0.0,
        "PF": 0.0,
        "PTS": 0.0
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