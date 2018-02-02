# parsers

A parser should conform to a simple API spec so that it can be easily accessed

# Healthcheck
Simple endpoint that accepts nothing and returns 'OK' on success.
|Path    |`/`|
|Method  |`GET`|
|Response|`"OK"`|

# Parse
The primary endpoint that will parse a message
|Path    |`/parse`|
|Method  |`POST`|
|Response|`json`|

Response
|Key     |Example Value         |Description|
|--------|----------------------|-----------|
|token   |`"1Z879E930346834440"`|String token that was extracted|
|type    |`"SHIPPING"`          |A string that indicates what type of metadata that was extracted. This will be used by other services to understand what kind of data this is.|
|metadata|`{"carrier": "UPS"}`  |A dictionary with any other additional metadat that may be used by other services|