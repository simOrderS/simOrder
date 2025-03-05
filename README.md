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

## 🚀 Install

In a Raspberry Pi (ideally) with a fresh Pi OS install and connected to your local network:

1. Clone the repository:

```bash
git clone https://github.com/simOrderS/simOrder.git
cd simOrder
```

2. Run the bash script in the `simOrder` folder to install dependencies and configure Django and Apache:
```bash
bash install.sh
```

## Usage

Access the application via `http://simorder.local` or via `http://<your-pi-ip-address>` on Android 11 or lower devices.

Log in using the initial credentials: user: `admin` and password: `admin`. You can (and should) change it later in the application).

Follow the configuration steps at the **home** page.

## 📸 Video Demos

To add screenshots, upload your images to your repository or another hosting service and replace the placeholder links below with the actual URLs.

| Login and System Settings | Printers | MasterData  | Users and Groups | Order Management | Analytics |
|:-------------:|:--------------------:|:--------------:|:--------------:|:--------------:|:--------------:|
| ![Settings](link-to-pos-image) | ![Printers](link-to-inventory-image) | ![MasterData](link-to-orders-image) | ![Users](link-to-orders-image) | ![Orders](link-to-orders-image) |![Analytics](link-to-orders-image) |

![Demo Login Settings](media/demo_Login_Settings.mp4)

https://github.com/simOrderS/simOrder/raw/main/media/demo_Login_Settings.mp4


## 🧩 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚖️ License

This project is licensed under the MIT License - see the LICENSE file for details.

