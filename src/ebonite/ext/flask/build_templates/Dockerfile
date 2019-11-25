FROM python:3.6

RUN apt update
RUN apt install -y \
    bash \
    nginx \
    supervisor
    #&& \
    #rm /etc/nginx/conf.d/default.conf

RUN pip install uwsgi==2.0.17.1

# Copy python requirements file
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Copy the Nginx global conf
COPY nginx.conf /etc/nginx/
# Copy the Flask Nginx site conf
COPY flask-site-nginx.conf /etc/nginx/conf.d/
# Copy the base uWSGI ini file to enable default dynamic uwsgi process number
COPY uwsgi.ini /etc/uwsgi/
# Custom Supervisord config
COPY supervisord.conf /etc/supervisord.conf


# Add demo app
COPY ./app /app
WORKDIR /app

CMD ["/usr/bin/supervisord"]
