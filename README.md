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

### Field extensions

* `x_frontend_widget` Name of the widget overriding the default (String)
* `x_frontend_fieldName` String name of the field (String)
* `x_frontend_fieldDescription` Description of the field (String)
* `x_frontend_editable` Editability of a field (Boolean)
* `x_frontend_placeholder` Placeholder on the edition input form (String)
* `x_frontend_relation` Model name of the relation id (String)
* `x_frontend_uspaceMap` Enaire Uspace regulation enabling (Boolean)
