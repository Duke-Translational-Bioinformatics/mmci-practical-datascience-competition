#!/bin/bash
python manage.py collectstatic --noinput
gunicorn --bind unix:/mmci-practical-datascience-competition/competition.sock competition.wsgi:application &
nginx -g "daemon off;"