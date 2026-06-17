# Guía de Integración de Grafana con LAIA

Esta guía explica cómo exponer analíticas y métricas directamente a Grafana desde tu backend basado en LAIA.

El framework proporciona endpoints integrados para métricas estándar de usuarios (total de usuarios, usuarios activos, usuarios por rol) y un registro dinámico para exponer métricas de negocio personalizadas sin ensuciar la arquitectura central.

## 1. Configurar Estadísticas Base de Usuarios

¡Buenas noticias! **No tienes que configurar absolutamente nada de código**.

El framework LAIA inyecta automáticamente el `StatsController` y el `GeocodingController` en el enrutador de tu aplicación al compilarla.

Esto expone automáticamente el endpoint:
- `GET /stats/users`

La respuesta incluye:
- `total_users`: Recuento total de usuarios.
- `users_by_role`: Usuarios agrupados por los roles que tengan asignados.
- `active_users`: Recuento de usuarios activos, tanto diarios (DAU) como mensuales (MAU).

**Nota sobre los Usuarios Activos:**
Los cálculos de DAU y MAU dependen del campo `lastLoginAt` dentro del modelo de usuario. El framework LAIA se encarga de actualizar este campo de manera automática durante el proceso de login, por lo que no necesitas rastrear las sesiones de los usuarios manualmente para que esto funcione.

## 2. Registrar Métricas de Negocio Personalizadas

Cada proyecto tiene métricas de dominio específicas (ej. número de viajes completados, ventas totales, tickets abiertos). En lugar de construir controladores de un solo uso para cada métrica, utiliza el `LaiaMetricsRegistry`.

### Escribir la lógica de la métrica

Crea una función asíncrona en tu proyecto que consulte la base de datos y calcule los datos que quieres exponer. Debe devolver un diccionario.

```python
# your_project/Metrics/Trips.py
async def get_trips_stats():
    # Lógica de ejemplo usando tu repositorio
    total_trips = await repository.count("trips")
    completed = await repository.count("trips", {"status": "completed"})
    
    return {
        "total_published_trips": total_trips,
        "completed_trips": completed
    }
```

### Registrar la Métrica

Durante la fase de arranque de tu aplicación, registra la función con un nombre de métrica único:

```python
from laiagenlib.Framework.Stats import LaiaMetricsRegistry
from your_project.Metrics.Trips import get_trips_stats

LaiaMetricsRegistry.register_metric("trips", get_trips_stats)
```

Esto crea de forma dinámica el siguiente endpoint:
- `GET /stats/custom/trips`

La ruta ejecutará tu función y devolverá el objeto JSON resultante.
También puedes listar todas las métricas personalizadas registradas haciendo una petición a `GET /stats/custom`.

## 3. Configuración de Métricas "Low-Code" (YAML)

Si prefieres no escribir código Python para cada métrica, LAIA te permite definirlas de forma declarativa usando un archivo YAML (por ejemplo, `metrics.yaml`).

### Exemple de `metrics.yaml`
```yaml
metrics:
  # Exemple 'count'
  - name: completed_trips
    collection: offer
    type: count
    filters:
      statusOffer: "expired"
      
  # Exemple 'aggregate'
  - name: users_by_city
    collection: user
    type: aggregate
    pipeline:
      - $group:
          _id: "$city"
          total: { $sum: 1 }
```

### Inicializando el archivo YAML
¡LAIA lo hace todo por ti! Solo tienes que crear el archivo `metrics.yaml` en la misma carpeta donde tengas tu `api.yaml`. Al arrancar el servidor, LAIA lo detectará y registrará todo automáticamente.

Las métricas definidas en el YAML aparecerán automáticamente en `/stats/custom/{nombre}` exactamente igual que si las hubieras programado en Python.

## 4. Configurar Grafana

Para visualizar estos datos en Grafana:

1. Instala el plugin de origen de datos **Infinity** o **JSON API** en tu instancia de Grafana.
2. Añade un nuevo *Data Source* apuntando a la URL base de tu backend.
3. En tu Dashboard de Grafana, crea un nuevo panel y selecciona el plugin JSON/Infinity.
4. Establece la ruta al endpoint específico que quieres consultar (ej. `/stats/users` o `/stats/custom/trips`).
5. Mapea los campos JSON entrantes a métricas de Grafana usando JSONPath (por ejemplo, `$.active_users.daily` para graficar el DAU).
