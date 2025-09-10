import sys
import requests
import json
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox,
                             QTableWidgetItem, QHeaderView, QWidget,
                             QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QComboBox, QTableWidget, QGroupBox,
                             QGridLayout, QTabWidget, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QFont, QPalette, QColor

# API Base URL
API_BASE_URL = "http://localhost:8000"


class ApiWorker(QThread):
    """Worker thread for API calls"""
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
        except requests.exceptions.ConnectionError:
            self.error_occurred.emit(
                "Cannot connect to API server. Make sure the API is running on http://localhost:8000")
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(str(e))
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {str(e)}")


class StyledMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Weather & Bitcoin Tracker")
        self.setGeometry(100, 100, 900, 700)

        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#autoRefreshBtn:checked {
                background-color: #ff9800;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
            }
            QComboBox {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #4CAF50;
            }
        """)

        # Initialize worker thread
        self.api_worker = ApiWorker()
        self.api_worker.data_received.connect(self.handle_api_response)
        self.api_worker.error_occurred.connect(self.handle_api_error)

        # Setup UI
        self.setup_ui()

        # Setup auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.get_bitcoin_price)
        self.refresh_interval = 30000  # 30 seconds

        # Current API call type
        self.current_call = None

    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Weather tab
        self.weather_tab = QWidget()
        self.setup_weather_tab()
        self.tab_widget.addTab(self.weather_tab, "🌤️ Weather")

        # Bitcoin tab
        self.bitcoin_tab = QWidget()
        self.setup_bitcoin_tab()
        self.tab_widget.addTab(self.bitcoin_tab, "₿ Bitcoin Prices")

        # Status bar
        self.statusBar().showMessage("Ready")

    def setup_weather_tab(self):
        """Setup weather tab"""
        layout = QVBoxLayout(self.weather_tab)

        # Input section
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("City:"))

        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("Enter city name...")
        self.city_input.returnPressed.connect(self.get_weather)
        input_layout.addWidget(self.city_input)

        self.get_weather_btn = QPushButton("Get Weather")
        self.get_weather_btn.clicked.connect(self.get_weather)
        input_layout.addWidget(self.get_weather_btn)

        layout.addLayout(input_layout)

        # Weather info group
        self.weather_group = QGroupBox("Weather Information")
        weather_grid = QGridLayout()

        # Create weather labels
        self.temp_label = QLabel("--")
        self.desc_label = QLabel("--")
        self.humidity_label = QLabel("--")
        self.wind_label = QLabel("--")

        # Style value labels
        for label in [self.temp_label, self.desc_label, self.humidity_label, self.wind_label]:
            label.setStyleSheet("font-size: 16px; color: #333;")

        # Add to grid
        weather_grid.addWidget(QLabel("Temperature:"), 0, 0)
        weather_grid.addWidget(self.temp_label, 0, 1)
        weather_grid.addWidget(QLabel("Description:"), 1, 0)
        weather_grid.addWidget(self.desc_label, 1, 1)
        weather_grid.addWidget(QLabel("Humidity:"), 2, 0)
        weather_grid.addWidget(self.humidity_label, 2, 1)
        weather_grid.addWidget(QLabel("Wind Speed:"), 3, 0)
        weather_grid.addWidget(self.wind_label, 3, 1)

        self.weather_group.setLayout(weather_grid)
        layout.addWidget(self.weather_group)

        # Add spacer
        layout.addStretch()

    def setup_bitcoin_tab(self):
        """Setup Bitcoin tab"""
        layout = QVBoxLayout(self.bitcoin_tab)

        # Control section
        control_layout = QHBoxLayout()

        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "All Sources", "Nobitex", "Kraken", "CoinMarketCap",
            "Binance", "Coinbase", "Blockchain"
        ])
        control_layout.addWidget(self.source_combo)

        self.get_bitcoin_btn = QPushButton("Get Bitcoin Price")
        self.get_bitcoin_btn.clicked.connect(self.get_bitcoin_price)
        control_layout.addWidget(self.get_bitcoin_btn)

        self.auto_refresh_btn = QPushButton("Auto Refresh: OFF")
        self.auto_refresh_btn.setObjectName("autoRefreshBtn")
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.toggled.connect(self.toggle_auto_refresh)
        control_layout.addWidget(self.auto_refresh_btn)

        layout.addLayout(control_layout)

        # Price table
        self.price_table = QTableWidget()
        self.price_table.setColumnCount(4)
        self.price_table.setHorizontalHeaderLabels(["Source", "Price (USD)", "Status", "Last Update"])
        self.price_table.setAlternatingRowColors(True)
        self.price_table.setSortingEnabled(True)

        # Set column widths
        header = self.price_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        layout.addWidget(self.price_table)

    def get_weather(self):
        """Get weather for the specified city"""
        city = self.city_input.text().strip()
        if not city:
            QMessageBox.warning(self, "Warning", "Please enter a city name")
            return

        self.current_call = "weather"
        self.statusBar().showMessage(f"Getting weather for {city}...")

        endpoint = f"/weather/v2/{city}"
        self.api_worker.set_endpoint(endpoint)
        self.api_worker.start()

    def get_bitcoin_price(self):
        """Get Bitcoin price from selected source"""
        source = self.source_combo.currentText()

        if source == "All Sources":
            self.current_call = "bitcoin_all"
            endpoint = "/bitcoin/all"
            self.statusBar().showMessage("Getting Bitcoin prices from all sources...")
        else:
            self.current_call = "bitcoin_single"
            endpoint = f"/bitcoin/source/{source.lower()}"
            self.statusBar().showMessage(f"Getting Bitcoin price from {source}...")

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

        self.statusBar().showMessage("Ready")

    def handle_api_error(self, error_msg):
        """Handle API errors"""
        if "Cannot connect to API server" in error_msg:
            QMessageBox.critical(self, "Connection Error",
                                 "Cannot connect to API server!\n\n"
                                 "Please make sure the API is running:\n"
                                 "1. Open a terminal/command prompt\n"
                                 "2. Navigate to your API folder\n"
                                 "3. Run: python main.py\n\n"
                                 "The API should be running on http://localhost:8000")
        else:
            QMessageBox.critical(self, "Error", f"API Error: {error_msg}")
        self.statusBar().showMessage("Error occurred")

    def display_weather(self, data):
        """Display weather information"""
        try:
            # Temperature
            temp = data['temperature']['current']
            unit = data['temperature']['unit']
            self.temp_label.setText(f"{temp}{unit}")

            # Make temperature bold and larger for current temp
            self.temp_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")

            # Description
            desc = data['weather']['description']
            self.desc_label.setText(desc)

            # Humidity
            humidity = data.get('humidity', 'N/A')
            self.humidity_label.setText(humidity)

            # Wind
            wind = data.get('wind', {}).get('speed', 'N/A')
            self.wind_label.setText(wind)

            # Update status
            city = data.get('city', self.city_input.text())
            source = data.get('source', 'Unknown')
            self.statusBar().showMessage(f"Weather data from {source} for {city}")

        except KeyError as e:
            QMessageBox.warning(self, "Warning", f"Missing data in response: {e}")

    def display_all_bitcoin_prices(self, data):
        """Display Bitcoin prices from all sources"""
        self.price_table.setRowCount(0)

        prices = data.get('bitcoin_prices', {})
        timestamp = data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        for source, info in prices.items():
            row_position = self.price_table.rowCount()
            self.price_table.insertRow(row_position)

            # Source
            source_item = QTableWidgetItem(source.title())
            source_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.price_table.setItem(row_position, 0, source_item)

            if isinstance(info, dict) and 'error' not in info:
                # Price
                price = info.get('usd', 'N/A')
                if isinstance(price, (int, float)):
                    price_item = QTableWidgetItem(f"${price:,.2f}")
                    price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    price_item.setForeground(QColor("#2196F3"))
                    price_item.setFont(QFont("Arial", 11, QFont.Bold))
                    self.price_table.setItem(row_position, 1, price_item)
                else:
                    self.price_table.setItem(row_position, 1, QTableWidgetItem("N/A"))

                # Status
                status_item = QTableWidgetItem("✓ Active")
                status_item.setForeground(QColor("#4CAF50"))
                self.price_table.setItem(row_position, 2, status_item)
            else:
                # Price
                self.price_table.setItem(row_position, 1, QTableWidgetItem("--"))

                # Status
                error_msg = info.get('error', 'Unknown error') if isinstance(info, dict) else str(info)
                status_item = QTableWidgetItem(f"✗ {error_msg}")
                status_item.setForeground(QColor("#f44336"))
                self.price_table.setItem(row_position, 2, status_item)

            # Timestamp
            self.price_table.setItem(row_position, 3, QTableWidgetItem(timestamp))

        # Update summary
        successful = data.get('successful_sources', 0)
        failed = data.get('failed_sources', 0)
        self.statusBar().showMessage(f"Updated: {successful} successful, {failed} failed sources")

    def display_single_bitcoin_price(self, data):
        """Display Bitcoin price from single source"""
        self.price_table.setRowCount(0)

        source = data.get('source', 'Unknown')
        timestamp = data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Main price row
        row_position = 0
        self.price_table.insertRow(row_position)

        # Source
        source_item = QTableWidgetItem(source.title())
        source_item.setFont(QFont("Arial", 10, QFont.Bold))
        self.price_table.setItem(row_position, 0, source_item)

        # Price
        price = data.get('usd', data.get('last_trade_price', 'N/A'))
        if isinstance(price, (int, float)):
            price_item = QTableWidgetItem(f"${price:,.2f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            price_item.setForeground(QColor("#2196F3"))
            price_item.setFont(QFont("Arial", 11, QFont.Bold))
            self.price_table.setItem(row_position, 1, price_item)

            # Status
            status_item = QTableWidgetItem("✓ Active")
            status_item.setForeground(QColor("#4CAF50"))
            self.price_table.setItem(row_position, 2, status_item)

            # Additional info for Nobitex
            if source.lower() == 'nobitex' and 'best_bid' in data:
                # Best Bid
                row_position = self.price_table.rowCount()
                self.price_table.insertRow(row_position)
                self.price_table.setItem(row_position, 0, QTableWidgetItem("  → Best Bid"))
                bid_item = QTableWidgetItem(f"${data['best_bid']:,.2f}")
                bid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.price_table.setItem(row_position, 1, bid_item)

                # Best Ask
                row_position = self.price_table.rowCount()
                self.price_table.insertRow(row_position)
                self.price_table.setItem(row_position, 0, QTableWidgetItem("  → Best Ask"))
                ask_item = QTableWidgetItem(f"${data['best_ask']:,.2f}")
                ask_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.price_table.setItem(row_position, 1, ask_item)

                # Spread
                row_position = self.price_table.rowCount()
                self.price_table.insertRow(row_position)
                self.price_table.setItem(row_position, 0, QTableWidgetItem("  → Spread"))
                spread_item = QTableWidgetItem(f"${data.get('spread', 0):,.2f}")
                spread_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.price_table.setItem(row_position, 1, spread_item)
        else:
            self.price_table.setItem(row_position, 1, QTableWidgetItem("N/A"))
            status_item = QTableWidgetItem("✗ Error")
            status_item.setForeground(QColor("#f44336"))
            self.price_table.setItem(row_position, 2, status_item)

        # Timestamp
        self.price_table.setItem(row_position, 3, QTableWidgetItem(timestamp))

    def toggle_auto_refresh(self, checked):
        """Toggle auto-refresh for Bitcoin prices"""
        if checked:
            self.refresh_timer.start(self.refresh_interval)
            self.auto_refresh_btn.setText("Auto Refresh: ON")
            self.statusBar().showMessage(f"Auto-refresh enabled (every {self.refresh_interval // 1000}s)")
            # Get initial price
            self.get_bitcoin_price()
        else:
            self.refresh_timer.stop()
            self.auto_refresh_btn.setText("Auto Refresh: OFF")
            self.statusBar().showMessage("Auto-refresh disabled")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look

    # Set application icon if you have one
    # app.setWindowIcon(QIcon('icon.png'))

    window = StyledMainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()