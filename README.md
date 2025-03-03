<p align="center">
  <img src="static/img/simOrder_logo.png" alt="simOrder Logo" width="150" height="auto">
</p>
<h1 align="center">simOrder</h1>

# A Raspberry Pi-based Order Management and POS System

simOrder is an affordable, open-source Order Management and Point of Sale (POS) System designed for small businesses. Built on a Raspberry Pi, it offers a cost-effective solution for inventory, customer orders and sales.

## ✨ Features

- **Intuitive Interface**: Easy-to-use touchscreen interface suitable for tables and smartphones
- **Inventory Management**: Keep track of stock levels when placing customer orders
- **Order Management**: Manage and send (print) customer orders to production
- **Multi-user Support**: Different access levels for managers and staff
- **Receipt Printing**: Compatible with ESC/POS thermal receipt printers
- **Reporting**: Generate sales reports and analyze business performance

## 🛠️ Hardware Requirements

- Raspberry Pi 4 4GB RAM (recommended, tested also on a Pi 3 A+)
- 7" iOS or Android Tablet connected to your local network
- ESC/POS USB and/ or Bluetooth Thermal Receipt Printer (app configured for a 58 mm)
- SD Card (32GB recommended)

## 💻 Software Stack

- Raspberry Pi OS (64-bit) connected to your local network
- Python 3.9+
- Django web framework
- SQLite database
- HTML5, CSS3, and JavaScript for the frontend

## 📸 Screenshots

To add screenshots, upload your images to your repository or another hosting service and replace the placeholder links below with the actual URLs.

| POS Interface | Inventory Management | Order Tracking |
|:-------------:|:--------------------:|:--------------:|
| ![POS](link-to-pos-image) | ![Inventory](link-to-inventory-image) | ![Orders](link-to-orders-image) |

## 🚀 Quick Start

1. Clone the repository:

```bash
git clone https://github.com/simOrderS/simOrder.git
```

2. Execute the bash script to install all dependencies and configure Django and Apache:
```bash
bash install.sh
```
   
