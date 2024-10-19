#!/bin/bash
pipenv run gunicorn -w 2 -t 900 -b 0.0.0.0:8080 app:app
