web: gunicorn config.wsgi:application
release: python manage.py migrate && python manage.py collectstatic --noinput
worker: celery -A config worker -l info
