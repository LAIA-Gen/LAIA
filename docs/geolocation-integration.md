# GeoLocation Module Integration

This document outlines the recent architectural changes made to integrate the custom geocoding features into the core LAIA framework. 

Previously, features like route distance calculation and address-to-GeoJSON conversion were tightly coupled to specific projects (like MouCultura) under custom router setups. We have decoupled these features and introduced a standard, modular `GeoLocation` addon that can be toggled on or off directly from the generator configuration.

## What changed?

1. **Implicit Domain Model**  
   We introduced `GeoLocation.py` under the `Domain/GeoLocation` directory. It inherits from `LaiaBaseModel` and acts as a standard schema for any location-based data (storing address strings, latitudes, longitudes, and optional GeoJSON structures). 

2. **Route Registration**  
   We expanded the OpenAPI repository interfaces (`OpenapiRepository` and `FastAPIOpenapiRepository`) with a new method: `create_geolocation_routes`. When called, this method does two things:
   - Mounts standard CRUD operations for the `GeoLocation` collection.
   - Mounts the custom geocoding endpoints (`/geocode/geojson` and `/geocode/route-distance`) previously handled by standalone routers.

3. **Opt-in Addon System**  
   To align with the framework's vision of having a modular backoffice where features can be enabled on demand, the `GeoLocation` module is no longer forced onto every project. In `CreateRoutes.py`, we added a new `add_geolocation` boolean flag to the `create_crud_routes` function. 
   
   Just like the `smtp_config` triggers the email routes or `add_storage` enables S3/Cloudinary storage, setting `add_geolocation=True` will inject the location models and routing logic into the generated backend.

## Usage

When generating a new backend or setting up the router initialization, simply pass the flag:

```python
await create_crud_routes(
    repositoryAPI=repositoryAPI,
    # ... other config
    add_geolocation=True
)
```

By keeping it toggleable, we ensure the framework stays lightweight for projects that don't need map integrations, while providing a plug-and-play solution for those that do.
