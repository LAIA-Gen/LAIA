# LAIA Grafana Integration Guide

This guide explains how to expose analytics and metrics from your LAIA-based backend directly to Grafana. 

The framework provides built-in endpoints for standard user metrics (total users, active users, users by role) and a dynamic registry to expose custom business metrics without cluttering your core architecture.

## 1. Setup Built-in User Statistics

To get automatic user statistics, include the `StatsController` in your FastAPI app router.

In your main entry point (e.g. `main.py` or your primary router file), import and register the controller by passing your repository instance and your User model:

```python
from fastapi import FastAPI
from laiagenlib.Framework.Stats import StatsController
from your_project.Domain.UserModel import UserModel

app = FastAPI()

# repository is your configured instance of ModelRepository
app.include_router(
    StatsController(repository=repository, user_model=UserModel)
)
```

This automatically exposes the endpoint:
- `GET /stats/users`

The response includes:
- `total_users`: Overall user count.
- `users_by_role`: Users grouped by their assigned roles.
- `active_users`: Both daily (DAU) and monthly (MAU) active user counts.

**Note on Active Users:** 
The DAU and MAU calculations rely on the `lastLoginAt` field inside the user model. The LAIA framework handles updating this field automatically during the login process, so you don't need to manually track user sessions for this to work.

## 2. Registering Custom Business Metrics

Every project has specific domain metrics (e.g., number of completed trips, total sales, open tickets). Instead of building one-off controllers for each metric, use the `LaiaMetricsRegistry`.

### Writing the Metric Logic

Create an async function in your project that queries the database and calculates the data you want to expose. It should return a dictionary.

```python
# your_project/Metrics/Trips.py
async def get_trips_stats():
    # Example logic using your repository
    total_trips = await repository.count("trips")
    completed = await repository.count("trips", {"status": "completed"})
    
    return {
        "total_published_trips": total_trips,
        "completed_trips": completed
    }
```

### Registering the Metric

During the startup phase of your application, register the function with a unique metric name:

```python
from laiagenlib.Framework.Stats import LaiaMetricsRegistry
from your_project.Metrics.Trips import get_trips_stats

LaiaMetricsRegistry.register_metric("trips", get_trips_stats)
```

This dynamically creates the following endpoint:
- `GET /stats/custom/trips`

The route will execute your function and return the resulting JSON object. 
You can also list all registered custom metrics by fetching `GET /stats/custom`.

## 3. Configuring Grafana

To visualize this data in Grafana:

1. Install the **Infinity** or **JSON API** data source plugin in your Grafana instance.
2. Add a new Data Source pointing to your backend's base URL.
3. In your Grafana Dashboard, create a new panel and select the JSON/Infinity plugin.
4. Set the path to the specific endpoint you want to query (e.g., `/stats/users` or `/stats/custom/trips`).
5. Map the incoming JSON fields to Grafana metrics using JSONPath (for example, `$.active_users.daily` to plot DAU).
