FROM geopython/pygeoapi:latest

COPY ./schemas.opengis.net /opt/schemas.opengis.net
COPY ./sensorthings.pygeoapi.config.yml /pygeoapi/local.config.yml
COPY ./sensorthings.py /pygeoapi/pygeoapi/provider/sensorthings.py
COPY ./plugin.py /pygeoapi/pygeoapi/plugin.py
