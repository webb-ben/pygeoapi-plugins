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

import logging
import os
import json
from pygeoapi.plugin import InvalidPluginError
from pygeoapi.provider.base import (ProviderNoDataError,
                                    ProviderQueryError)
from SPARQLWrapper import SPARQLWrapper, JSON
from pygeoapi.provider.csv_ import CSVProvider as BaseProvider

LOGGER = logging.getLogger(__name__)

_PREFIX = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX : <http://dbpedia.org/resource/>
PREFIX dbpedia2: <http://dbpedia.org/property/>
PREFIX dbpedia: <http://dbpedia.org/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""

_SELECT = 'SELECT *'

_WHERE = """
WHERE {{
    VALUES ?v {{ {value} }}
    {where}
}}
"""

class SPARQLProvider(BaseProvider):
    """SPARQL Wrapper API Provider
    """

    def __init__(self, provider_def):
        """
         Class constructor

        :param provider_def: provider definitions from yml pygeoapi-config.
                             data, id_field, name set in parent class

        :returns: pygeoapi.provider.base.SPARQLProvider
        """
        super().__init__(provider_def)
        sparql_endpoint = provider_def.get('sparql_endpoint')
        self.sparql = SPARQLWrapper(sparql_endpoint)
        self.subject = provider_def.get('sparql_subject')
        self.predicates = provider_def.get('sparql_predicates')

    def query(self, startindex=0, limit=10, resulttype='results',
              bbox=[], datetime_=None, properties=[], sortby=[],
              select_properties=[], skip_geometry=False, q=None):
        """
        SPARQL query
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
        content = BaseProvider.query(self, startindex,
              limit, resulttype, bbox,
              datetime_, properties, sortby,
              select_properties, skip_geometry, q)

        v = ['<{}>'.format(c['properties'][self.subject]) \
                for c in content['features']]
        search = ' '.join(v)
        values = self._sparql(search)

        for item in content['features']:
            subj = item['properties'][self.subject]
            sparql_data = values.get(subj)
            item['properties'] = self._combine(
                item['properties'], sparql_data
            )
    
        return content

    def get(self, identifier):
        """
        Query by id
        :param identifier: feature id
        :returns: dict of single GeoJSON feature
        """
        feature = BaseProvider.get(self, identifier)
        
        subject = feature['properties'][self.subject]
        values = self._sparql('<{}>'.format(subject))

        sparql_data = values.get(subject)
        feature['properties'] = self._combine(
            feature['properties'], sparql_data
        )

        return feature

    def _sparql(self, value):
        """
        Private function to request SPARQL context
        :param value: subject for SPARQL query
        :returns: dict of SPARQL feature data
        """
        LOGGER.debug('Requesting SPARQL data')
        
        w = ['?v {p} ?{o} .'.format(p=v, o=k) \
            for k, v in self.predicates.items()]
        where = ''.join(w)
        
        qs = self._makeQuery(value, where)
        result = self._sendQuery(qs)
        
        results = {}
        for v in result['results']['bindings']:
            _id = v.pop('v').get('value')
            results[_id] = v

        return results

    def _combine(self, properties, values):
        """
        Private function to add SPARQL context to feature properties
        :param properties: dict of feature properties 
        :param values: SPARQL data of feature
        :returns: dict of feature properties with SPARQL
        """
        try:
            for v in values:
                properties[v] = values[v].get('value')
        except TypeError as err:
            LOGGER.error('Error SPARQL data: {}'.format(err))
            raise ProviderNoDataError(err)

        return properties

    def _makeQuery(self, value, where, prefix=_PREFIX, select=_SELECT):
        """
        Private function to make SPARQL querystring
        :param value: str, collection of SPARQL subjects
        :param where: str, collection of SPARQL predicates
        :param prefix: str, Optional SPARQL prefixes (Default = _PREFIX)
        :param select: str, Optional SPARQL select (Default = 'SELECT *')
        :returns: str, SPARQL query
        """
        querystring = ''.join([
            prefix, select, _WHERE.format(value=value, where=where)
        ])
        LOGGER.debug('SPARQL query: {}'.format(querystring))

        return querystring
        
    def _sendQuery(self, query):
        """
        Private function to send SPARQL query
        :param query: str, SPARQL query
        :returns: SPARQL query results
        """
        LOGGER.debug('Sending SPARQL query')
        self.sparql.setQuery(query)
        self.sparql.setReturnFormat(JSON)

        try:
            results = self.sparql.query().convert()
            LOGGER.debug('Received SPARQL results')
        except Execption as err:
            LOGGER.error('Error in SPARQL query: {}'.format(err))
            raise ProviderQueryError(err)

        return results

    def __repr__(self):
        return '<SPARQLProvider> {}, {}'.format(self.data, self.table)