# =================================================================
#
# Authors: Jorge Samuel Mendes de Jesus <jorge.dejesus@protonmail.net>
#          Tom Kralidis <tomkralidis@gmail.com>
#          Francesco Bartoli <xbartolone@gmail.com>
#
# Copyright (c) 2018 Jorge Samuel Mendes de Jesus
# Copyright (c) 2021 Tom Kralidis
# Copyright (c) 2020 Francesco Bartoli
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

import requests
import logging
import os
import json
from pygeoapi.plugin import InvalidPluginError
from pygeoapi.provider.base import (BaseProvider, ProviderConnectionError,
                                    ProviderItemNotFoundError)

LOGGER = logging.getLogger(__name__)
LOGGER.debug("Logger Init")


class SensorthingsProvider(BaseProvider):
    """Sensorthings API Provider
    """

    def __init__(self, provider_def):
        """
        Sensorthings Class constructor

        :param provider_def: provider definitions from yml pygeoapi-config.
                             data,id_field, name set in parent class

        :returns: pygeoapi.provider.base.SensorthingsProvider
        """
        LOGGER.debug("Logger SDFInit")
        super().__init__(provider_def)
        self.entity = provider_def.get('entity')

    def _load(self, startindex=0, limit=10, resulttype='results',
              identifier=None, bbox=[], datetime_=None, properties=[],
              select_properties=[], skip_geometry=False, q=None):
        """
        Load sensorthings data
        :param startindex: starting record to return (default 0)
        :param limit: number of records to return (default 10)
        :param resulttype: return results or hit limit (default results)
        :param bbox: bounding box [minx,miny,maxx,maxy]
        :param datetime_: temporal (datestamp or extent)
        :param properties: list of tuples (name, value)
        :param sortby: list of dicts (property, order)
        :param select_properties: list of property names
        :param skip_geometry: bool of whether to skip geometry (default False)
        :param q: full-text search term(s)
        :returns: dict of GeoJSON FeatureCollection
        """

        found = False
        result = None
        feature_collection = {
            'type': 'FeatureCollection',
            'features': []
        }

        params = {'$expand': 'Locations', '$skip': startindex, '$top': limit}

        url = self.data + self.entity
        if identifier:
            url += '({})'.format(identifier)
        r = requests.get(url, params=params)
        LOGGER.debug(r.url)
        v = r.json().get('value')
        if resulttype == 'hits':
            LOGGER.debug('Returning hits only')
            feature_collection['numberMatched'] = len(v)
            return feature_collection

        if identifier:
            v = [r.json(),]
        LOGGER.debug(v)
        for entity in v:
            feature = {'type': 'Feature'}
            feature['id'] = str(entity.pop(self.id_field))
            if not skip_geometry:
                location = entity.pop('Locations')[0]
                feature['geometry'] = location.get('location')
            else:
                feature['geometry'] = None

            if self.properties or select_properties:
                feature['properties'] = OrderedDict()
                for p in set(self.properties) | set(select_properties):
                    try:
                        feature['properties'][p] = v[p]
                    except KeyError as err:
                        LOGGER.error(err)
                        raise ProviderQueryError()
            else:
                feature['properties'] = {**entity, **entity.pop('properties')}
                feature['properties']['@iot.selfLink'] += '?'
                
            feature_collection['features'].append(feature)

        if identifier is not None and feature['id'] == identifier:
            LOGGER.debug(feature)
            return feature
        elif identifier is not None:
            return None

        feature_collection['numberReturned'] = len(
            feature_collection['features'])
        
        return feature_collection

    def query(self, startindex=0, limit=10, resulttype='results',
              bbox=[], datetime_=None, properties=[], sortby=[],
              select_properties=[], skip_geometry=False, q=None):
        """
        Sensorthings query
        :param startindex: starting record to return (default 0)
        :param limit: number of records to return (default 10)
        :param resulttype: return results or hit limit (default results)
        :param bbox: bounding box [minx,miny,maxx,maxy]
        :param datetime_: temporal (datestamp or extent)
        :param properties: list of tuples (name, value)
        :param sortby: list of dicts (property, order)
        :param select_properties: list of property names
        :param skip_geometry: bool of whether to skip geometry (default False)
        :param q: full-text search term(s)
        :returns: dict of GeoJSON FeatureCollection
        """

        return self._load(startindex, limit, resulttype,
                          select_properties=select_properties,
                          skip_geometry=skip_geometry)

    def get(self, identifier):
        """
        query the provider by id
        :param identifier: feature id
        :returns: dict of single GeoJSON feature
        """
        return self._load(identifier=identifier)

    def __repr__(self):
        return '<SensorthingsProvider> {}, {}'.format(self.data, self.table)