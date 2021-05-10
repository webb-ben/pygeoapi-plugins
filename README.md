## SPARQL Provider for pygeoapi

### --- WORK IN PROGRESS ---

To use a provider other than CSV, the parent class for SPARQLProvider in sparql.py must be changed to the correct pygeoapi provider as well as updating the pygeoapi config file accordingly.

The SPARQL provider sits on top of another provider, and injects the reqults of its query into the properties table of the features that are produced from querying SPARQL's BaseProvider.
