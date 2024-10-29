from celery import shared_task

from players.services import update_players


@shared_task
def update_teams_roster():
    update_players()