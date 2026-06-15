from fastapi import FastAPI
from laiagenlib.Framework.Stats import StatsController
import uvicorn

# Simulamos la Base de Datos para que no necesites tener MongoDB instalado
class MockCollection:
    def count_documents(self, filters):
        # Simula que encuentra 23 ofertas caducadas
        return 23

class MockRepo:
    def __init__(self):
        # Simulamos que existe la coleccion "offer"
        self.db = {"offer": MockCollection()}
    
    async def get_items(self, model_name, limit):
        # Devuelve 150 usuarios totales
        return [], 150
    
    async def aggregate_items(self, model_name, pipeline):
        # Simulamos las agregaciones según lo que pida
        if "roles" in str(pipeline):
            return [{"_id": "admin", "count": 10}, {"_id": "volunteer", "count": 140}]
        else:
            return [{"count": 42}] # DAU o MAU

class MockUser:
    __name__ = "LaiaUser"

# Creamos el YAML simulado
with open("metrics_mock.yaml", "w") as f:
    f.write("""
metrics:
  - name: expired_trips
    collection: offer
    type: count
    filters:
      statusOffer: expired
""")

# Arrancamos FastAPI
app = FastAPI()
app.include_router(
    StatsController(repository=MockRepo(), user_model=MockUser, metrics_file="metrics_mock.yaml")
)

if __name__ == "__main__":
    print("¡Servidor de prueba arrancado! Ve a http://127.0.0.1:8001/docs")
    uvicorn.run(app, host="127.0.0.1", port=8001)
