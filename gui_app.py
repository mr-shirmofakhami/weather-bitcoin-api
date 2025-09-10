import sys
import requests
import json
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox,
                             QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt5.uic import loadUi

# API Base URL - Change this if your API runs on different address
API_BASE_URL = "http://localhost:8000"


class ApiWorker(QThread):
    """Worker thread for API calls to prevent UI freezing"""
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.endpoint = ""

    def set_endpoint(self, endpoint):
        self.endpoint = endpoint

    def run(self):
        try:
            response = requests.get(f"{API_BASE_URL}{self.endpoint}", timeout=10)
            response.raise_for_status()
            data = response.json()
            self.data_received.emit(data)
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(str(e))
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the UI file
        loadUi('bitcoin_weather_gui.ui', self)

        # Initialize worker thread
        self.api_worker = ApiWorker()
        self.api_worker.data_received.connect(self.handle_api_response)
        self.api_worker.error_occurred.connect(self.handle_api_error)

        # Connect buttons
        self.getWeatherBtn.clicked.connect(self.get_weather)
        self.getBitcoinBtn.clicked.connect(self.get_bitcoin_price)
        self.autoRefreshBtn.toggled.connect(self.toggle_auto_refresh)

        # Setup auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.get_bitcoin_price)
        self.refresh_interval = 30000  # 30 seconds

        # Setup price table
        self.setup_price_table()

        # Current API call type
        self.current_call = None

        # Enable Enter key for weather search
        self.cityInput.returnPressed.connect(self.get_weather)

    def setup_price_table(self):
        """Setup the Bitcoin price table"""
        # Set column widths
        header = self.priceTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

    def get_weather(self):
        """Get weather for the specified city"""
        city = self.cityInput.text().strip()
        if not city:
            QMessageBox.warning(self, "Warning", "Please enter a city name")
            return

        self.current_call = "weather"
        self.statusLabel.setText(f"Getting weather for {city}...")

        # Use v2 endpoint which has fallback
        endpoint = f"/weather/v2/{city}"
        self.api_worker.set_endpoint(endpoint)
        self.api_worker.start()

    def get_bitcoin_price(self):
        """Get Bitcoin price from selected source"""
        source = self.sourceCombo.currentText()

        if source == "All Sources":
            self.current_call = "bitcoin_all"
            endpoint = "/bitcoin/all"
            self.statusLabel.setText("Getting Bitcoin prices from all sources...")
        else:
            self.current_call = "bitcoin_single"
            endpoint = f"/bitcoin/source/{source.lower()}"
            self.statusLabel.setText(f"Getting Bitcoin price from {source}...")

        self.api_worker.set_endpoint(endpoint)
        self.api_worker.start()

    def handle_api_response(self, data):
        """Handle successful API response"""
        if self.current_call == "weather":
            self.display_weather(data)
        elif self.current_call == "bitcoin_all":
            self.display_all_bitcoin_prices(data)
        elif self.current_call == "bitcoin_single":
            self.display_single_bitcoin_price(data)

        self.statusLabel.setText("Ready")

    def handle_api_error(self, error_msg):
        """Handle API errors"""
        QMessageBox.critical(self, "Error", f"API Error: {error_msg}")
        self.statusLabel.setText("Error occurred")

    def display_weather(self, data):
        """Display weather information"""
        try:
            # Temperature
            temp = data['temperature']['current']
            unit = data['temperature']['unit']
            self.tempLabel.setText(f"{temp}{unit}")

            # Description
            desc = data['weather']['description']
            self.descLabel.setText(desc)

            # Humidity
            humidity = data.get('humidity', 'N/A')
            self.humidityLabel.setText(humidity)

            # Wind
            wind = data.get('wind', {}).get('speed', 'N/A')
            self.windLabel.setText(wind)

            # Update status
            city = data.get('city', self.cityInput.text())
            source = data.get('source', 'Unknown')
            self.statusLabel.setText(f"Weather data from {source} for {city}")

        except KeyError as e:
            QMessageBox.warning(self, "Warning", f"Missing data in response: {e}")

    def display_all_bitcoin_prices(self, data):
        """Display Bitcoin prices from all sources"""
        self.priceTable.setRowCount(0)

        prices = data.get('bitcoin_prices', {})
        timestamp = data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        for source, info in prices.items():
            row_position = self.priceTable.rowCount()
            self.priceTable.insertRow(row_position)

            # Source
            self.priceTable.setItem(row_position, 0, QTableWidgetItem(source.title()))

            if isinstance(info, dict) and 'error' not in info:
                # Price
                price = info.get('usd', 'N/A')
                if isinstance(price, (int, float)):
                    price_item = QTableWidgetItem(f"${price:,.2f}")
                    price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.priceTable.setItem(row_position, 1, price_item)
                else:
                    self.priceTable.setItem(row_position, 1, QTableWidgetItem("N/A"))

                # Status
                status_item = QTableWidgetItem("✓ Active")
                status_item.setForeground(Qt.green)
                self.priceTable.setItem(row_position, 2, status_item)
            else:
                # Price
                self.priceTable.setItem(row_position, 1, QTableWidgetItem("--"))

                # Status
                error_msg = info.get('error', 'Unknown error') if isinstance(info, dict) else str(info)
                status_item = QTableWidgetItem(f"✗ {error_msg}")
                status_item.setForeground(Qt.red)
                self.priceTable.setItem(row_position, 2, status_item)

            # Timestamp
            self.priceTable.setItem(row_position, 3, QTableWidgetItem(timestamp))

        # Update summary
        successful = data.get('successful_sources', 0)
        failed = data.get('failed_sources', 0)
        self.statusLabel.setText(f"Updated: {successful} successful, {failed} failed sources")

    def display_single_bitcoin_price(self, data):
        """Display Bitcoin price from single source"""
        self.priceTable.setRowCount(0)

        source = data.get('source', 'Unknown')
        timestamp = data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        row_position = 0
        self.priceTable.insertRow(row_position)

        # Source
        self.priceTable.setItem(row_position, 0, QTableWidgetItem(source.title()))

        # Price
        price = data.get('usd', data.get('last_trade_price', 'N/A'))
        if isinstance(price, (int, float)):
            price_item = QTableWidgetItem(f"${price:,.2f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.priceTable.setItem(row_position, 1, price_item)

            # Status
            status_item = QTableWidgetItem("✓ Active")
            status_item.setForeground(Qt.green)
            self.priceTable.setItem(row_position, 2, status_item)

            # Additional info for Nobitex
            if source.lower() == 'nobitex' and 'best_bid' in data:
                row_position = self.priceTable.rowCount()
                self.priceTable.insertRow(row_position)
                self.priceTable.setItem(row_position, 0, QTableWidgetItem("  → Best Bid"))
                bid_item = QTableWidgetItem(f"${data['best_bid']:,.2f}")
                bid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.priceTable.setItem(row_position, 1, bid_item)

                row_position = self.priceTable.rowCount()
                self.priceTable.insertRow(row_position)
                self.priceTable.setItem(row_position, 0, QTableWidgetItem("  → Best Ask"))
                ask_item = QTableWidgetItem(f"${data['best_ask']:,.2f}")
                ask_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.priceTable.setItem(row_position, 1, ask_item)

                row_position = self.priceTable.rowCount()
                self.priceTable.insertRow(row_position)
                self.priceTable.setItem(row_position, 0, QTableWidgetItem("  → Spread"))
                spread_item = QTableWidgetItem(f"${data.get('spread', 0):,.2f}")
                spread_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.priceTable.setItem(row_position, 1, spread_item)
        else:
            self.priceTable.setItem(row_position, 1, QTableWidgetItem("N/A"))
            status_item = QTableWidgetItem("✗ Error")
            status_item.setForeground(Qt.red)
            self.priceTable.setItem(row_position, 2, status_item)

        # Timestamp
        self.priceTable.setItem(row_position, 3, QTableWidgetItem(timestamp))

    def toggle_auto_refresh(self, checked):
        """Toggle auto-refresh for Bitcoin prices"""
        if checked:
            self.refresh_timer.start(self.refresh_interval)
            self.autoRefreshBtn.setText("Auto Refresh: ON")
            self.statusLabel.setText(f"Auto-refresh enabled (every {self.refresh_interval // 1000}s)")
        else:
            self.refresh_timer.stop()
            self.autoRefreshBtn.setText("Auto Refresh: OFF")
            self.statusLabel.setText("Auto-refresh disabled")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()