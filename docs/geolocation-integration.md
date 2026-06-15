# Integració del mòdul GeoLocation

En aquest document s'expliquen els canvis que hem fet per integrar les funcions de geocoding a dins del core de LAIA.

Fins ara, les funcions per calcular distàncies o passar adreces a GeoJSON estaven clavades en projectes específics (com el MouCultura) amb rutes fetes a mida. El que hem fet ara és separar tot això i crear un addon de `GeoLocation` modular que es pot activar o desactivar directament des de la configuració del generador.

## Què hem canviat?

1. **Model de domini implícit**  
   Hem creat `GeoLocation.py` dins de `Domain/GeoLocation`. Aquest model hereta de `LaiaBaseModel` i ens serveix d'esquema estàndard per guardar qualsevol dada de localització (carrers, latituds, longituds i estructures GeoJSON opcionals).

2. **Registre de rutes**  
   Hem afegit un mètode nou a les interfícies de l'OpenAPI (`OpenapiRepository` i `FastAPIOpenapiRepository`) que es diu `create_geolocation_routes`. Aquesta funció s'encarrega de dues coses:
   - Muntar el CRUD típic per a la col·lecció `GeoLocation`.
   - Muntar les rutes custom de geocoding (`/geocode/geojson` i `/geocode/route-distance`) que abans anaven a part.

3. **Sistema d'addons**  
   La idea del framework és tenir un backoffice on puguis activar només el que necessites. Per això, el mòdul de `GeoLocation` ja no s'empassa per defecte a tots els projectes. A `CreateRoutes.py` hem ficat un paràmetre `add_geolocation` a la funció `create_crud_routes`.
   
   De la mateixa manera que `smtp_config` aixeca el tema dels correus o `add_storage` activa l'emmagatzematge, posant `add_geolocation=True` injectarem tot el que fa falta per als mapes al backend que estiguem generant.

## Com fer-ho servir?

Quan generis un backend nou o preparis la càrrega de rutes, només has de passar-li el paràmetre així:

```python
await create_crud_routes(
    repositoryAPI=repositoryAPI,
    # ... altres paràmetres
    add_geolocation=True
)
```

Fent-ho opcional ens assegurem que el framework no pesi més del compte en projectes on no calguin mapes, però que alhora sigui super fàcil d'endollar on sí que facin falta.
