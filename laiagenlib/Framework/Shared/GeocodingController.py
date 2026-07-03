import httpx
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse

def GeocodingController():
    router = APIRouter(tags=["Geocoding"])

    @router.post("/geocode/geojson")
    async def post_code_to_geojson(address: str = Body(..., embed=True)):
        try:
            if not address:
                raise HTTPException(status_code=400, detail="address is required")
            
            url = "https://nominatim.openstreetmap.org/search"
            
            headers = {
                "User-Agent": "LAIAFramework/1.0"
            }
            
            params = {
                'q': address, 
                'format': 'jsonv2'
            }

            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()  
                
            results = response.json()
            if not results:
                raise HTTPException(status_code=404, detail="No geocoding results found")
            
            lat = results[0].get("lat")
            lon = results[0].get("lon")
            if not lat or not lon:
                raise HTTPException(status_code=404, detail="Coordinates not found for this address")

            geojson_data = {
                "type": "Point",
                "coordinates": [float(lon), float(lat)]
            }
            return JSONResponse(content=geojson_data, status_code=200)

        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Error contacting Geocoding API: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def geocode_address(address: str, client: httpx.AsyncClient) -> tuple[float, float]:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "LAIAFramework/1.0"}
        params = {'q': address, 'format': 'jsonv2'}
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        results = response.json()
        if not results:
            raise HTTPException(status_code=404, detail=f"Address '{address}' not found")
        return float(results[0]["lon"]), float(results[0]["lat"])

    @router.post("/geocode/route-distance")
    async def post_route_distance(
        addresses: list[str] = Body(
            ...,
            embed=True,
            examples=[["Castelldefels", "Gava", "Viladecans"]]
        )
    ):
        if not addresses or len(addresses) < 2:
            raise HTTPException(status_code=400, detail="At least 2 addresses are required to calculate route distance")
        
        try:
            import asyncio
            async with httpx.AsyncClient(timeout=10.0) as client:
                geocode_tasks = [geocode_address(addr, client) for addr in addresses]
                coords = await asyncio.gather(*geocode_tasks)
                
                async def get_distance(p1, p2) -> float:
                    lon1, lat1 = p1
                    lon2, lat2 = p2
                    url = f"https://routing.openstreetmap.de/routed-car/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
                    params = {
                        "overview": "false",
                        "geometries": "polyline"
                    }
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    if data.get("code") != "Ok" or not data.get("routes"):
                        raise HTTPException(status_code=400, detail="Could not calculate route between points")
                    return float(data["routes"][0]["distance"])
                
                route_tasks = [get_distance(coords[i], coords[i+1]) for i in range(len(coords) - 1)]
                distances_meters = await asyncio.gather(*route_tasks)
                
                distances_km = [round(dist / 1000.0, 2) for dist in distances_meters]
                total_distance_km = round(sum(distances_meters) / 1000.0, 2)
                
                coords_response = []
                for idx, addr in enumerate(addresses):
                    lon, lat = coords[idx]
                    coords_response.append({
                        "address": addr,
                        "lat": lat,
                        "lon": lon
                    })
                
                return JSONResponse(content={
                    "distances_km": distances_km,
                    "total_distance_km": total_distance_km,
                    "coordinates": coords_response
                }, status_code=200)
                
        except HTTPException as he:
            raise he
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"External service error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
