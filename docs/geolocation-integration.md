# Integració del mòdul GeoLocation

Canvis de les funcions de geocoding a dins del core de LAIA.

Prèviament, les funcions per calcular distàncies o convertir adreces a GeoJSON estaven vinculades a projectes específics (com MouCultura) amb rutes fetes a mida. Actualment, s'han desacoblat aquestes funcions per crear un addon de `GeoLocation` modular que es pot activar o desactivar directament des de la configuració del generador.

## Canvis realitzats

1. **Model de domini implícit**  
   S'ha creat l'arxiu `GeoLocation.py` dins del directori `Domain/GeoLocation`. Aquest model hereta de `LaiaBaseModel` i actua com a esquema estàndard per emmagatzemar qualsevol dada de localització (adreces, latituds, longituds i estructures GeoJSON opcionals).

2. **Registre de rutes**  
   S'ha afegit un mètode nou a les interfícies de l'OpenAPI (`OpenapiRepository` i `FastAPIOpenapiRepository`) anomenat `create_geolocation_routes`. Aquesta funció s'encarrega de dues tasques:
   - Muntar les operacions CRUD estàndard per a la col·lecció `GeoLocation`.
   - Muntar les rutes personalitzades de geocoding (`/geocode/geojson` i `/geocode/route-distance`) que anteriorment es gestionaven en routers independents.

3. **Sistema d'addons**  
   Amb l'objectiu d'alinear-se amb la visió del framework de disposar d'un backoffice on es puguin activar funcions sota demanda, el mòdul de `GeoLocation` ja no s'inclou per defecte a tots els projectes. A l'arxiu `CreateRoutes.py`, s'ha afegit un paràmetre booleà `add_geolocation` a la funció `create_crud_routes`.
   
   De la mateixa manera que `smtp_config` habilita les rutes de correu o `add_storage` activa l'emmagatzematge, establir `add_geolocation=True` injectarà els models de localització i la lògica de rutes al backend generat.

## Mode d'ús

En generar un backend nou o inicialitzar les rutes, s'ha de passar el paràmetre corresponent:

```python
await create_crud_routes(
    repositoryAPI=repositoryAPI,
    # ... altres paràmetres
    add_geolocation=True
)
```

En mantenir-ho de forma opcional, s'assegura que el framework continuï sent lleuger per a projectes que no requereixen integracions de mapes, alhora que proporciona una solució directa per a aquells que sí ho necessiten.
