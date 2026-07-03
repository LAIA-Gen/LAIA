# Integracio del modul d'estadistiques amb Grafana

Generalitzacio de les rutes d'estadistiques dins del core de LAIA.

Previament, les metriques necessaries per construir panells de Grafana estaven
vinculades a projectes especifics, com MouCultura, mitjancant rutes i calculs
fets a mida. Actualment, aquesta logica s'ha desacoblat per oferir un modul
d'estadistiques reutilitzable des de qualsevol backend generat amb LAIA.

Grafana no forma part directament del core. LAIA exposa endpoints HTTP amb
respostes JSON estandarditzades, i Grafana els pot consumir mitjancant un
origen de dades compatible amb JSON, com Infinity.

## Canvis realitzats

### 1. Controlador generic d'estadistiques

S'ha creat `StatsController.py` dins del directori `Framework/Stats`. Aquest
controlador registra les rutes generiques seguents:

- `GET /stats/users`: retorna el nombre total d'usuaris, els usuaris agrupats
  per rol i els usuaris actius diaris i mensuals.
- `GET /stats/custom`: retorna la llista de metriques personalitzades
  registrades.
- `GET /stats/custom/{metric_name}`: executa i retorna una metrica concreta.

Les metriques d'usuaris actius utilitzen el camp `lastLoginAt`. Aquest camp
s'actualitza automaticament amb la data i hora UTC quan un usuari inicia
sessio correctament.

### 2. Registre de metriques personalitzades

S'ha creat `MetricsRegistry.py`, que incorpora `LaiaMetricsRegistry`. Aquest
registre permet definir metriques especifiques de cada projecte sense afegir
la seva logica al core de LAIA.

Cada metrica s'identifica amb un nom i una funcio asincrona. Aquesta via esta
pensada per a calculs que requereixen logica Python, diverses fonts de dades o
integracions amb serveis externs.

Exemple:

```python
from laiagenlib.Framework.Stats import LaiaMetricsRegistry


async def get_conversion_rate():
    return {
        "conversion_rate": 72.5,
        "status": "success",
    }


LaiaMetricsRegistry.register_metric("conversion_rate", get_conversion_rate)
```

La metrica queda disponible a:

```text
GET /stats/custom/conversion_rate
```

### 3. Definicio de metriques amb YAML

Per a consultes directes a MongoDB, s'ha afegit una alternativa declarativa
mitjancant un fitxer `metrics.yaml`. Aquesta opcio evita haver de programar una
funcio Python per a recomptes o agregacions senzilles.

Actualment, el modul admet les operacions seguents:

- `count`: compta els documents que compleixen uns filtres.
- `aggregate`: executa un pipeline d'agregacio de MongoDB.

Exemple:

```yaml
metrics:
  - name: expired_offers
    collection: offer
    type: count
    filters:
      statusOffer: expired

  - name: offers_by_status
    collection: offer
    type: aggregate
    pipeline:
      - $group:
          _id: "$statusOffer"
          total:
            $sum: 1
```

Aquestes metriques queden disponibles respectivament a:

```text
GET /stats/custom/expired_offers
GET /stats/custom/offers_by_status
```

### 4. Registre automatic a LaiaFastApi

`LaiaFastApi` localitza automaticament el model d'usuari marcat amb
`x-auth: true` a l'especificacio OpenAPI i injecta el `StatsController` a
l'aplicacio FastAPI.

Durant l'arrencada, LAIA tambe busca un fitxer anomenat `metrics.yaml` al
mateix directori que el fitxer OpenAPI principal. Si el troba, carrega i
registra les metriques declarades sense que el projecte hagi d'incloure el
controlador manualment.

En un projecte amb l'estructura de MouCultura, la ubicacio esperada es:

```text
backend/openapi.yaml
backend/metrics.yaml
```

## Mode d'us

Per habilitar les estadistiques automatiques, el projecte ha de tenir un model
d'usuari amb l'extensio `x-auth: true`:

```yaml
User:
  type: object
  x-auth: true
  properties:
    email:
      type: string
```

En arrencar el backend, les rutes apareixen automaticament a la documentacio
Swagger de FastAPI:

```text
http://localhost:8000/docs
```

Les rutes son peticions `GET` i no necessiten cos de peticio. Abans de
configurar Grafana, es recomana verificar directament que els endpoints
retornen el JSON esperat.

Finalment, Grafana pot consultar aquestes rutes mitjancant un origen de dades
JSON. Si Grafana s'executa dins de Docker i el backend s'executa a la maquina
local, la URL habitual es:

```text
http://host.docker.internal:8000/stats/custom/expired_offers
```

## Prova local dels endpoints

Abans de configurar Grafana, cal comprovar que MongoDB i el backend del
projecte estan en execucio. En el cas de MouCultura, el servidor s'inicia des
de l'arrel del projecte:

```powershell
docker compose up -d mongo
python backend/main.py
```

Amb el backend disponible al port `8000`, es poden revisar les rutes a Swagger:

```text
http://localhost:8000/docs
```

També es poden consultar directament des del navegador o amb Postman:

```text
GET http://localhost:8000/stats/users
GET http://localhost:8000/stats/custom
GET http://localhost:8000/stats/custom/expired_offers
GET http://localhost:8000/stats/custom/offers_by_status
```

Com que totes aquestes operacions son `GET`, no necessiten cap cos de peticio.
Una resposta valida per a una metrica de recompte tindria aquesta forma:

```json
{
  "expired_offers": 12
}
```

## Connexio amb Grafana

Una vegada validats els endpoints, Grafana es pot iniciar localment amb Docker:

```powershell
docker run -d --name grafana -p 3000:3000 grafana/grafana:latest
```

La interfície queda disponible a:

```text
http://localhost:3000
```

Des de l'administracio de Grafana s'ha d'instal·lar el connector Infinity i
crear un origen de dades o una consulta de tipus JSON. Per representar la
metrica d'ofertes caducades, la consulta es configura amb aquests valors:

```text
Tipus: JSON
Metode: GET
URL: http://host.docker.internal:8000/stats/custom/expired_offers
Format: Table
Camp numeric: expired_offers
```

S'utilitza `host.docker.internal` perquè `localhost`, des de dins del
contenidor de Grafana, identifica el mateix contenidor i no la maquina on
s'executa el backend.

La prova es considera correcta quan el valor representat al panell de Grafana
coincideix amb el valor retornat directament per l'endpoint HTTP.

Aquesta generalitzacio permet mantenir LAIA independent del domini de cada
projecte: el core proporciona el mecanisme de registre i exposicio, mentre que
cada backend defineix les metriques que necessita mitjancant YAML o Python.
