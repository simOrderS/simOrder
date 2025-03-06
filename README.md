<p align="center">
  <img src="static/img/simOrder_logo.png" alt="simOrder Logo" width="150" height="auto">
</p>
<h1 align="center">simOrder</h1>
<p align="center">
  Copyright &copy; 2025 simOrder
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </a>
</p>


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
- SD Card (32GB recommended)
- 7" iOS or Android Tablet connected to your local network
- ESC/POS USB and/ or Bluetooth Thermal Printer (app configured for a 58 mm like the one below)
<img src="https://github.com/user-attachments/assets/6a7ed41b-8bac-4c5b-993b-cfa03a3c5f2b" width="256" height="auto">

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

**Login and System Settings:**

https://github.com/user-attachments/assets/91b6aec6-99ae-4eca-a774-6efa0ec34a46


**Printers:**

https://github.com/user-attachments/assets/f4251d40-add2-4b39-9a37-d622b7ab5920


**MasterData:**

https://github.com/user-attachments/assets/6ceb80bf-d669-41b7-9b16-835e35a93b78


**Order Management:**

https://github.com/user-attachments/assets/f0b0262b-9be3-49e5-b537-8dc57b4943d6

Examples of printed receipt and orders:

<img src="https://github.com/user-attachments/assets/ffb31c4c-03c1-4709-b254-ddd25c5d242f" width="512" height="auto">


**Users and Groups:**

https://github.com/user-attachments/assets/c5c29ea7-4cc1-4cf6-8eec-6868e0734f09


**Analytics:**

https://github.com/user-attachments/assets/ffd82d38-8af6-446a-a4de-04251fd98b7e


## 🧩 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

