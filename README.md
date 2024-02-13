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

client = MongoClient('mongodb://localhost:27017')

db = client.test

openapi_path = os.path.join(os.getcwd(), "api.yaml")

# Inside app_instance, we got: api (fastAPI), db (MongoClient), crud_instance (CRUDMongoImpl)
app_instance = LaiaFastApi(openapi_path, db, CRUDMongoImpl)

flutter_app = LaiaFlutter(openapi_path, "frontend")

app = app_instance.api

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```