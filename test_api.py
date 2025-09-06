import requests
import json
from datetime import datetime

# Base URL for your API
BASE_URL = "http://localhost:8000"


def test_weather_apis():
    """Test which weather APIs are working"""
    print("=== Testing Weather API Status ===")
    response = requests.get(f"{BASE_URL}/weather/test")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
        print()


def test_weather():
    """Test weather endpoints"""
    cities = ["London", "Tehran", "Tokyo"]

    print("=== Testing Weather (Alternative API) ===")
    for city in cities:
        response = requests.get(f"{BASE_URL}/weather/v2/{city}")
        if response.status_code == 200:
            data = response.json()
            print(f"\n{city}:")
            print(f"  Source: {data.get('source', 'N/A')}")
            print(f"  Temperature: {data['temperature']['current']}{data['temperature']['unit']}")
            print(f"  Weather: {data['weather']['description']}")
            print(f"  Humidity: {data.get('humidity', 'N/A')}")
        else:
            print(f"Error getting weather for {city}: {response.status_code}")


def test_bitcoin_sources():
    """Test individual Bitcoin sources"""
    print("\n=== Testing Individual Bitcoin Sources ===")
    sources = ["nobitex", "binance", "coinbase", "blockchain", "kraken"]

    for source in sources:
        try:
            response = requests.get(f"{BASE_URL}/bitcoin/source/{source}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                price = data.get('usd', data.get('price_usd', 'N/A'))
                print(f"\n{source.upper()}:")
                print(f"  Price: ${price:,.2f}" if isinstance(price, (int, float)) else f"  Price: {price}")
                if source == "nobitex" and 'rls' in data:
                    print(f"  Price (RLS): {data['rls']:,.0f} Rials")
                if '24h_change' in data:
                    print(f"  24h Change: {data['24h_change']:.2f}%")
            else:
                print(f"\n{source.upper()}: Error {response.status_code}")
        except requests.exceptions.Timeout:
            print(f"\n{source.upper()}: Timeout")
        except Exception as e:
            print(f"\n{source.upper()}: Error - {str(e)}")


def test_all_bitcoin_sources():
    """Test all Bitcoin sources"""
    print("\n=== Testing All Bitcoin Sources ===")
    try:
        response = requests.get(f"{BASE_URL}/bitcoin/all", timeout=15)
        if response.status_code == 200:
            data = response.json()
            print(f"Successful sources: {data['successful_sources']}")
            print(f"Failed sources: {data['failed_sources']}")
            print("\nPrice by source:")
            for source, info in data['bitcoin_prices'].items():
                if 'error' not in info:
                    price = info.get('usd', 'N/A')
                    print(f"  {source}: ${price:,.2f}" if isinstance(price, (int, float)) else f"  {source}: {price}")
                else:
                    print(f"  {source}: {info['error']}")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    print(f"Testing API at {BASE_URL}")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Test weather
    test_weather_apis()
    test_weather()

    # Test Bitcoin
    test_bitcoin_sources()
    test_all_bitcoin_sources()