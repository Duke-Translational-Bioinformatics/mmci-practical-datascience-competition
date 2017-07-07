#!/bin/bash
python manage.py collectstatic --noinput
gunicorn --timeout 300 --bind unix:/mmci-practical-datascience-competition/competition.sock competition.wsgi:application &
nginx -g "daemon off;"