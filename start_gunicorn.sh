[program:mark]
command=/usr/bin/pipenv run gunicorn -b 0.0.0.0:8080 -t 600 app
directory=/home/ubuntu/mark8
autostart=true
autorestart=true
stderr_logfile=/var/log/mark.err.log
stdout_logfile=/var/log/mark.out.log

[program:markb]
command=/usr/bin/pipenv run python /home/ubuntu/mark8/index.py
directory=/home/ubuntu/mark8
autostart=true
autorestart=true
stderr_logfile=/var/log/markb.err.log
stdout_logfile=/var/log/markb.out.log