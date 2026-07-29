# LAIA 

LAIA is a Python library that automates the generation of backend Python code and frontend Flutter code based on an OpenAPI description file. The official python library can be found at: [laia-gen-lib](https://pypi.org/project/laia-gen-lib/)

*Please note that LAIA is currently under development.*

## Installation

```
pip install laia-gen-lib
```

## Prerequisites

Make sure you have Python installed. For using the Flutter code generation functionality, Flutter is also required `Flutter 3.16.5, Dart 3.2.3`.

## Usage

*Note: For the Flutter generator, please ensure that the necessary dependencies are available locally. Currently, the paths to the arg_code_generator used for Flutter code generation are referenced locally. For more information, visit the LAIA Flutter code generation repository: [LAIA Flutter Code Generator](https://github.com/albieta/laia_flutter_gen)*

*The `api.yaml` file needs to be located at the same directory as the following python file.*

```py
from laiagenlib.main import LaiaFastApi, LaiaFlutter
from laiagenlib.crud.crud_mongo_impl import CRUDMongoImpl
from laiagenlib.utils.logger import _logger
from pymongo import MongoClient
import os
import uvicorn
import requests
import threading
import yaml
import json

client = MongoClient('mongodb://localhost:27017')

db = client.test

openapi_path = os.path.join(os.getcwd(), "openapi.yaml")

# Inside app_instance, we got: api (fastAPI), db (MongoClient), crud_instance (CRUDMongoImpl)
app_instance = LaiaFastApi(openapi_path, db, CRUDMongoImpl)

flutter_app = LaiaFlutter(openapi_path, "frontend")

app = app_instance.api

def run_server():
    from backend.routes import router
    app.include_router(router)
    uvicorn.run(app, host="0.0.0.0", port=8000)

server_thread = threading.Thread(target=run_server)
server_thread.start()

response = requests.get("http://localhost:8000/openapi.json")
if response.status_code == 200:
    openapi_yaml = yaml.dump(json.loads(response.text), default_flow_style=False)
    with open(openapi_path, 'wb') as f: 
        f.write(openapi_yaml.encode('utf-8'))
else:
    _logger.info("Failed to retrieve OpenAPI YAML file.")
```

## Spatial searches

MongoDB-backed SEARCH routes accept GeoJSON `$near` and `$nearSphere` filters. Coordinates must use
`[longitude, latitude]`; `$minDistance` and `$maxDistance` are expressed in meters. Results are ordered
from nearest to farthest unless `orders` requests a different order.

```json
{
  "filters": {
    "location.geo": {
      "$near": {
        "$geometry": {
          "type": "Point",
          "coordinates": [-73.9667, 40.78]
        },
        "$minDistance": 1000,
        "$maxDistance": 100000
      }
    }
  },
  "orders": {},
  "populate": []
}
```

The queried field requires a MongoDB `2dsphere` index. The index path must point to the field that
contains the GeoJSON object. For example:

```javascript
db.offers.createIndex({ "location.geo": "2dsphere" })
db.demands.createIndex({ geometry: "2dsphere" })
```

If an offer stores the GeoJSON object directly in `location` instead, use
`db.offers.createIndex({ location: "2dsphere" })`. Create these indexes as part of the consuming
application's database deployment or migration; LAIA does not create production indexes while
serving a search request.

## Development

### Run tests

`python setup.py pytest`

### Build library

The wheel file will be stored in the "dist" folder and can be pip installed from there
`python setup.py bdist_wheel`

## OpenAPI.yaml extensions

### Route extensions

* `x-create-{model}` Override the default CREATE route --> POST /model
* `x-read-{model}` Override the default READ route --> GET /model/{id}
* `x-update-{model}` Override the default UPDATE route --> PUT /model/{id}
* `x-delete-{model}` Override the default DELETE route --> DELETE /model/{id}
* `x-search-{model}` Override the default SEARCH route --> GET /models

### Model Schema extensions

* `x-auth` Add authentication (CRUD + register + login)

### Public routes

By default all routes require authentication. Add a `permissions` block to a model to make specific operations publicly accessible (no token required, no access-rights check).

Set the operation value to an **empty list `[]`** to mark it as public. Omit an operation to keep it protected.

Available operations: `create`, `read`, `update`, `delete`, `search`, `aggregate`, `nice`

```yaml
components:
  schemas:
    Offer:
      type: object
      permissions:
        search: []      # anyone can search, no token needed
        read: []        # anyone can read by ID
        # create / update / delete — still require auth
      properties:
        title:
          type: string
        ...
```

> **Note:** Use `permissions` (without `x-` prefix) directly on the schema definition. The library maps it internally to `x-permissions`.

### Tab extensions (`x-frontend-tabs`)

Use the `x-frontend-tabs` extension on a model schema to customize the tabbed view of the model detail page in the frontend backoffice.

Tabs can contain either a list of standard model properties (form fields) or a dynamic read-only view of a related collection (virtual relation tab).

> [!NOTE]
> **Automatic Tab Behavior:**
> * **Relation Tabs**: Any standard class field annotated with a relation (via `x_frontend_relation`) will automatically have its relation tab generated and appended at the end of the tabs list. You do not need to list them explicitly in `x-frontend-tabs`.
> * **Default Details Tab**: If `x-frontend-tabs` is omitted, a default **Details** tab containing all the model's standard editable fields is automatically created.


#### 1. Standard Fields Tab
Displays the specified list of model fields.

```yaml
x-frontend-tabs:
  - label: General
    fields:
      - title
      - description
      - image
```

#### 2. Virtual Relation Tab (Read-Only)
Displays a dynamic read-only list of related objects from another collection. It automatically queries the related collection using the current parent ID and optional additional filters.

```yaml
x-frontend-tabs:
  - label: Matches Pendents
    relation: Match
    inverseRelationField: offerId
    filters:
      status: PENDING
  - label: Matches Acceptats
    relation: Match
    inverseRelationField: offerId
    filters:
      status: ACCEPTED
```
* `relation`: The target model name to display in the tab's list view (e.g. `Activity` or `Match`).
* `inverseRelationField`: The field (or list of comma-separated fields / YAML array) on the target model that references this model's ID (e.g. `eventId`, `offerId`, or `[offerId, demandId]`).
* `filters` / `extraFilters`: (Optional) Key-value pairs to apply additional query filters on the related list view (e.g. `status: PENDING`).


### Field extensions

* `x_frontend_widget` Name of the widget overriding the default (String)
* `x_frontend_fieldName` String name of the field (String)
* `x_frontend_fieldDescription` Description of the field (String)
* `x_frontend_editable` Editability of a field (Boolean)
* `x_frontend_placeholder` Placeholder on the edition input form (String)
* `x_frontend_relation` Model name of the relation id (String)
* `x_frontend_uspaceMap` Enaire Uspace regulation enabling (Boolean)
* `x-embedded` Marks the referenced schema as an embedded object (Boolean)
* `x-exclude-from-response` Never include this field in any API response (Boolean)

### Embedded objects

Fields annotated with `x-embedded: true` declare that the referenced schema is stored **inline** inside the parent document rather than as a separate collection.

Behaviour:
- The embedded schema is **not exposed as its own CRUD endpoint** — no routes are generated for it.
- In the generated `model.py` the embedded class extends `BaseModel` instead of `LaiaBaseModel`, so it has no persistence layer of its own.
- MongoDB serialization handles nested objects automatically via `model_dump`.

Example:

```yaml
components:
  schemas:
    Address:
      type: object
      properties:
        street:
          type: string
        city:
          type: string

    Person:
      type: object
      properties:
        name:
          type: string
        address:
          $ref: '#/components/schemas/Address'
          x-embedded: true
```

In this example, `Address` will be embedded inside `Person` documents in MongoDB. No `/address` routes will be created.
