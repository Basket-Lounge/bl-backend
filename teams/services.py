import re

from django.conf import settings

from nba_api.stats.endpoints.franchisehistory import FranchiseHistory
from nba_api.stats.endpoints.leaguestandingsv3 import LeagueStandingsV3
from nba_api.stats.endpoints.teamgamelogs import TeamGameLogs

from teams.models import Team

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

    for team in standings:
        if team[6] == 'East':
            ranking['East'].append(dict(zip(headers, team)))
        else:
            ranking['West'].append(dict(zip(headers, team)))

    return ranking

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

def get_last_n_games_log(team_id, n=5):
    if n < 1 or n > 82:
        raise ValueError('Invalid n value. n should be between 1 and 82')

    try:
        Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        raise ValueError('Invalid team_id')
    
    ## Get the last 5 games log from nba_api
    team_log = TeamGameLogs(
        team_id_nullable=team_id,
        season_nullable=settings.SEASON_YEAR,
        season_type_nullable='Regular Season'
    ).get_dict()['resultSets'][0]

    headers = team_log['headers']
    team_log = team_log['rowSet']

    return [dict(zip(headers, game)) for game in team_log[:n]]