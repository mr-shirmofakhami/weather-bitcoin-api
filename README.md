# Weather & Bitcoin API

A FastAPI application that provides weather information and Bitcoin price tracking from multiple cryptocurrency exchanges.

## Features

- Get current weather for any city using multiple weather APIs
- Track Bitcoin prices from 6 different cryptocurrency sources
- RESTful API with automatic documentation
- Timeout handling and retry logic for reliable data fetching
- Support for both VPN and non-VPN accessible exchanges

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Clone or download the project files**
   ```bash
   # Create project directory
   mkdir weather-bitcoin-api
   cd weather-bitcoin-api
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```  

3. **Create environment file**
   ```bash
   # Weather APIs (Optional - fallback available)
   OPENWEATHER_API_KEY=your_openweather_key_here
   WEATHERAPI_KEY=your_weatherapi_key_here

   # Crypto APIs (Optional)
   COINMARKETCAP_API_KEY=your_coinmarketcap_key_here
   ```  
   
4. **Create environment file**
   ```bash
   python main.py
   ```  
   or
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```  
   
5. **The API will be available at:**
- Main API: http://localhost:8000
- Interactive Documentation: http://localhost:8000/docs
- Alternative Documentation: http://localhost:8000/redoc


## Network Requirements
### Bitcoin Price Sources

✅ Work with Regular Internet Connection:

- Nobitex - Iranian cryptocurrency exchange
- CoinMarketCap - Requires API key for detailed data
- Kraken - International exchange

🔒 Require VPN/Proxy:

- Binance - May be blocked in some regions
- Coinbase - May be blocked in some regions
- Blockchain.info - May be blocked in some regions
### Weather Sources

✅ Work with Regular Internet Connection:

- OpenWeatherMap - Requires API key (may need activation time)
- WeatherAPI.com - Requires API key (works immediately)
- wttr.in - Free fallback service (no API key required

   


