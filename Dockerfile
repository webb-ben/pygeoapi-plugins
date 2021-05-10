FROM geopython/pygeoapi:latest

COPY ./ext_data /ext_data
COPY ./schemas.opengis.net /opt/schemas.opengis.net
COPY ./sparql.pygeoapi.config.yml /pygeoapi/local.config.yml
COPY ./sparql.py /pygeoapi/pygeoapi/provider/sparql.py
COPY ./plugin.py /pygeoapi/pygeoapi/plugin.py
RUN ["python3", "-m", "pip", "install", "SPARQLWrapper"]