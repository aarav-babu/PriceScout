# celery_worker.py
from celery import Celery
import runscraper as rs

celery = Celery(__name__, broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

@celery.task
def call_webscraper(post_type, user_id):
    rs.call_webscraper(post_type,user_id)