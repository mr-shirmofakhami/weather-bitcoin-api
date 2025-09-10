from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Any
import asyncio
import httpx

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Weather & Bitcoin API",
    description="API to get weather information and Bitcoin price from multiple sources",
    version="3.0.0"
)

# API configurations
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY")
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

# Weather API endpoints
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHERAPI_BASE_URL = "http://api.weatherapi.com/v1/current.json"

# Crypto API endpoints
CRYPTO_APIS = {
    "coinbase": {
        "url": "https://api.coinbase.com/v2/exchange-rates?currency=BTC",
        "requires_key": False,
        "timeout": 8
    },
    "blockchain": {
        "url": "https://blockchain.info/ticker",
        "requires_key": False,
        "timeout": 8
    },
    "coinmarketcap": {
        "url": "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
        "requires_key": True,
        "timeout": 8
    },
    "binance": {
        "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "requires_key": False,
        "timeout": 5
    },
    "kraken": {
        "url": "https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
        "requires_key": False,
        "timeout": 8
    },
    "nobitex": {
        "url": "https://apiv2.nobitex.ir/v3/orderbook/BTCUSDT",
        "requires_key": False,
        "timeout": 8
    }
}


@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "message": "Welcome to Weather & Bitcoin API v3",
        "endpoints": {
            "weather": {
                "openweather": "/weather/{city}",
                "weatherapi": "/weather/v2/{city}",
                "test": "/weather/test"
            },
            "bitcoin": {
                "all_sources": "/bitcoin/all",
                "specific_source": "/bitcoin/source/{source}"
            }
        },
        "available_crypto_sources": list(CRYPTO_APIS.keys())
    }


@app.get("/weather/test")
async def test_weather_apis():
    """Test which weather APIs are working"""
    results = {}

    # Test OpenWeather
    if OPENWEATHER_API_KEY:
        try:
            params = {
                "q": "London",
                "appid": OPENWEATHER_API_KEY,
                "units": "metric"
            }
            response = requests.get(OPENWEATHER_BASE_URL, params=params, timeout=5)
            results["openweather"] = {
                "status": "working" if response.status_code == 200 else f"error: {response.status_code}",
                "api_key_status": "valid" if response.status_code == 200 else "invalid or not activated"
            }
        except Exception as e:
            results["openweather"] = {"status": "error", "message": str(e)}
    else:
        results["openweather"] = {"status": "no API key configured"}

    # Test WeatherAPI
    if WEATHERAPI_KEY:
        try:
            params = {
                "key": WEATHERAPI_KEY,
                "q": "London"
            }
            response = requests.get(WEATHERAPI_BASE_URL, params=params, timeout=5)
            results["weatherapi"] = {
                "status": "working" if response.status_code == 200 else f"error: {response.status_code}"
            }
        except Exception as e:
            results["weatherapi"] = {"status": "error", "message": str(e)}
    else:
        results["weatherapi"] = {"status": "no API key configured"}

    return results


@app.get("/weather/{city}")
async def get_weather(city: str, units: str = "metric"):
    """Get weather using OpenWeatherMap (might need activation time)"""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OpenWeather API key not configured. Use /weather/v2/{city} for alternative"
        )

    try:
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": units
        }
        response = requests.get(OPENWEATHER_BASE_URL, params=params, timeout=10)

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="API key invalid or not yet activated. Please wait a few hours or use /weather/v2/{city}"
            )

        response.raise_for_status()
        data = response.json()

        weather_info = {
            "source": "OpenWeatherMap",
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": {
                "current": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "min": data["main"]["temp_min"],
                "max": data["main"]["temp_max"],
                "unit": "°C" if units == "metric" else "°F"
            },
            "humidity": f"{data['main']['humidity']}%",
            "pressure": f"{data['main']['pressure']} hPa",
            "weather": {
                "main": data["weather"][0]["main"],
                "description": data["weather"][0]["description"]
            },
            "wind": {
                "speed": f"{data['wind']['speed']} {'m/s' if units == 'metric' else 'mph'}"
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return JSONResponse(content=weather_info)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"City '{city}' not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/weather/v2/{city}")
async def get_weather_v2(city: str):
    """Alternative weather API (WeatherAPI.com) - works immediately"""
    if not WEATHERAPI_KEY:
        # Use a free weather service that doesn't require API key
        try:
            # Using wttr.in as fallback (no API key required)
            response = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10)
            if response.status_code == 200:
                data = response.json()
                current = data["current_condition"][0]
                return {
                    "source": "wttr.in (no API key required)",
                    "city": city,
                    "temperature": {
                        "current": float(current["temp_C"]),
                        "feels_like": float(current["FeelsLikeC"]),
                        "unit": "°C"
                    },
                    "weather": {
                        "description": current["weatherDesc"][0]["value"]
                    },
                    "humidity": f"{current['humidity']}%",
                    "wind": {
                        "speed": f"{current['windspeedKmph']} km/h"
                    }
                }
        except:
            pass

        raise HTTPException(
            status_code=500,
            detail="WeatherAPI key not configured. Add WEATHERAPI_KEY to .env file"
        )

    try:
        params = {
            "key": WEATHERAPI_KEY,
            "q": city,
            "aqi": "no"
        }
        response = requests.get(WEATHERAPI_BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        weather_info = {
            "source": "WeatherAPI.com",
            "city": data["location"]["name"],
            "country": data["location"]["country"],
            "temperature": {
                "current": data["current"]["temp_c"],
                "feels_like": data["current"]["feelslike_c"],
                "unit": "°C"
            },
            "humidity": f"{data['current']['humidity']}%",
            "pressure": f"{data['current']['pressure_mb']} mb",
            "weather": {
                "description": data["current"]["condition"]["text"],
                "icon": data["current"]["condition"]["icon"]
            },
            "wind": {
                "speed": f"{data['current']['wind_kph']} km/h",
                "direction": data["current"]["wind_dir"]
            },
            "uv_index": data["current"]["uv"],
            "visibility": f"{data['current']['vis_km']} km",
            "last_updated": data["current"]["last_updated"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return JSONResponse(content=weather_info)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/bitcoin/all")
async def get_bitcoin_all_sources():
    """Get Bitcoin price from all available sources with better timeout handling"""
    results = {}

    async def fetch_source(source: str, config: dict):
        try:
            # Skip sources that require API keys if not configured
            if source == "coinmarketcap" and not COINMARKETCAP_API_KEY:
                return source, {"error": "API key required but not configured"}

            # Use the same logic as the working single source endpoint
            if source == "coinbase":
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(config["url"], timeout=config.get("timeout", 8))
                        response.raise_for_status()
                        data = response.json()

                        # Use the exact same parsing logic as the working single source
                        result = parse_crypto_response(source, data)
                        return source, result
                except Exception as e:
                    return source, {"error": f"Coinbase error: {str(e)}"}

            elif source == "binance":
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(config["url"], timeout=config.get("timeout", 5))
                        response.raise_for_status()
                        data = response.json()

                        # Use the exact same parsing logic as the working single source
                        result = parse_crypto_response(source, data)
                        return source, result
                except Exception as e:
                    return source, {"error": f"Binance error: {str(e)}"}

            else:
                # For other sources, use the existing logic
                headers = {}
                params = {}

                if source == "coinmarketcap":
                    headers = {
                        'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
                        'Accept': 'application/json'
                    }
                    params = {'symbol': 'BTC', 'convert': 'USD'}

                async with httpx.AsyncClient() as client:
                    for attempt in range(2):
                        try:
                            response = await client.get(
                                config["url"],
                                headers=headers,
                                params=params,
                                timeout=config.get("timeout", 5)
                            )

                            if response.status_code == 200:
                                data = response.json()
                                return source, parse_crypto_response(source, data)
                            else:
                                if attempt == 0:
                                    await asyncio.sleep(1)
                                    continue
                                return source, {"error": f"HTTP {response.status_code}"}
                        except httpx.TimeoutException:
                            if attempt == 0:
                                await asyncio.sleep(1)
                                continue
                            return source, {"error": "Timeout"}
                        except Exception as e:
                            if attempt == 0:
                                await asyncio.sleep(1)
                                continue
                            return source, {"error": str(e)}

        except Exception as e:
            return source, {"error": str(e)}

    # Fetch all sources concurrently
    tasks = []
    for source, config in CRYPTO_APIS.items():
        tasks.append(fetch_source(source, config))

    # Wait for all tasks with timeout
    try:
        completed = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=60
        )

        for result in completed:
            if isinstance(result, tuple):
                source, data = result
                results[source] = data
            else:
                results["unknown"] = {"error": str(result)}

    except asyncio.TimeoutError:
        results["error"] = "Global timeout reached"

    return JSONResponse(content={
        "bitcoin_prices": results,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "successful_sources": sum(1 for r in results.values() if isinstance(r, dict) and "error" not in r),
        "failed_sources": sum(1 for r in results.values() if isinstance(r, dict) and "error" in r)
    })


@app.get("/bitcoin/source/{source}")
async def get_bitcoin_from_source(source: str):

    if source not in CRYPTO_APIS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Available sources: {list(CRYPTO_APIS.keys())}"
        )

    api_config = CRYPTO_APIS[source]

    try:
        headers = {}
        params = {}

        # Handle different API requirements
        if source == "coinmarketcap":
            if not COINMARKETCAP_API_KEY:
                raise HTTPException(
                    status_code=500,
                    detail="CoinMarketCap requires API key. Add COINMARKETCAP_API_KEY to .env"
                )
            headers = {
                'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
                'Accept': 'application/json'
            }
            params = {
                'symbol': 'BTC',
                'convert': 'USD,EUR,GBP'
            }
        elif source == "nobitex":

            response = requests.get(
                "https://apiv2.nobitex.ir/v3/orderbook/BTCUSDT",
                timeout=api_config.get("timeout", 8)
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ok":
                # Extract price from orderbook data
                last_trade_price = float(data.get("lastTradePrice", 0))

                # Get best bid and ask prices
                bids = data.get("bids", [])
                asks = data.get("asks", [])

                best_bid = float(bids[0][0]) if bids else 0
                best_ask = float(asks[0][0]) if asks else 0

                # Calculate mid price
                mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else last_trade_price

                return JSONResponse(content={
                    "source": "nobitex",
                    "usd": mid_price,
                    "last_trade_price": last_trade_price,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "spread": best_ask - best_bid if best_bid and best_ask else 0,
                    "last_update": data.get("lastUpdate", 0),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                raise HTTPException(status_code=500, detail="Invalid response from Nobitex")


        for attempt in range(2):
            try:
                response = requests.get(
                    api_config["url"],
                    headers=headers,
                    params=params,
                    timeout=api_config.get("timeout", 8)
                )
                response.raise_for_status()
                data = response.json()

                # Parse response based on source
                result = parse_crypto_response(source, data)
                result["source"] = source
                result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                return JSONResponse(content=result)

            except requests.exceptions.Timeout:
                if attempt == 0:  # Retry once
                    continue
                raise HTTPException(
                    status_code=504,
                    detail=f"Timeout while fetching from {source} after retries. The service might be slow or unavailable."
                )
            except requests.exceptions.RequestException as e:
                if attempt == 0:  # Retry once
                    continue
                raise HTTPException(
                    status_code=503,
                    detail=f"Network error while fetching from {source}: {str(e)}"
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching from {source}: {str(e)}"
        )


def parse_crypto_response(source: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse response from different crypto APIs"""
    result = {}

    try:
        if source == "coinbase":
            # Fixed: Coinbase returns rates where 1 BTC = X currency
            # So we use the rates directly, not 1/rate
            result = {
                "usd": float(data["data"]["rates"]["USD"]),
                "eur": float(data["data"]["rates"]["EUR"]),
                "gbp": float(data["data"]["rates"]["GBP"])
            }

        elif source == "blockchain":
            result = {
                "usd": data["USD"]["last"],
                "eur": data["EUR"]["last"],
                "gbp": data["GBP"]["last"]
            }

        elif source == "coinmarketcap":
            btc_data = data["data"]["BTC"]["quote"]["USD"]
            result = {
                "usd": btc_data["price"],
                "24h_change": btc_data["percent_change_24h"],
                "market_cap": btc_data["market_cap"],
                "volume_24h": btc_data["volume_24h"]
            }

        elif source == "binance":
            # Fixed: Binance returns a simple object with price field
            result = {
                "usd": float(data["price"])
            }

        elif source == "kraken":
            # Fixed: Ensure we're getting the correct field from Kraken
            if "result" in data and "XXBTZUSD" in data["result"]:
                result = {
                    "usd": float(data["result"]["XXBTZUSD"]["c"][0])
                }
            else:
                result = {"error": "Unexpected Kraken response format"}

        elif source == "nobitex":
            # Handle Nobitex orderbook data
            if data.get("status") == "ok":
                last_trade_price = float(data.get("lastTradePrice", 0))
                bids = data.get("bids", [])
                asks = data.get("asks", [])

                best_bid = float(bids[0][0]) if bids else 0
                best_ask = float(asks[0][0]) if asks else 0
                mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else last_trade_price

                result = {
                    "usd": mid_price,
                    "last_trade_price": last_trade_price,
                    "best_bid": best_bid,
                    "best_ask": best_ask
                }
            else:
                result = {"error": "Invalid Nobitex response"}

    except Exception as e:
        result = {"error": f"Parse error: {str(e)}"}

    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)