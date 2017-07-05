FROM continuumio/anaconda3
MAINTAINER Ben Neely <nigelneely@gmail.com>
ADD requirements.txt /requirements.txt
RUN pip install -r requirements.txt
RUN apt-get update
RUN apt-get install -y nginx
ADD nginx_conf /etc/nginx
WORKDIR /mmci-practical-datascience-competition
CMD ["./start_docker.sh"]