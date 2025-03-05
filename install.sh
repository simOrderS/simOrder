#!/bin/bash

# Function to print section headers
print_header() {
    echo "-------------------------------------------------------------------------"
    echo "$1"
    echo "-------------------------------------------------------------------------"
}

# Variables
HOSTNAME='simorder'

# Update Raspberry Pi
print_header "Updating Raspberry Pi"
sudo apt-get update && sudo apt dist-upgrade -y && sudo apt-get autoremove -y

# Install Apache and configure
print_header "Installing and configuring Apache"
sudo apt install apache2 -y

# Install additional packages
print_header "Installing additional packages"
sudo apt install libapache2-mod-wsgi-py3 -y
sudo apt install python3 python3-venv python3-pip -y
sudo apt install build-essential libdbus-glib-1-dev libgirepository1.0-dev libpython3-dev libdbus-1-dev -y
sudo apt install libcairo2-dev pkg-config python3-dev libgirepository1.0-dev -y
sudo apt-get clean

# Create and activate virtual environment
print_header "Creating virtual environment"
if python3 -m venv venv; then
    echo "Virtual environment successfully created"
else
    echo "Error: Failed to create the virtual environment"
    exit 1
fi

print_header "Activating virtual environment"
source venv/bin/activate
if [[ $? -eq 0 ]]; then
    echo "Virtual environment successfully activated"
else
    echo "Error: Failed to activate the virtual environment"
    exit 1
fi

# Install project dependencies
print_header "Installing project dependencies"
if [ -f "requirements.txt" ]; then
    if python3 -m pip install -r requirements.txt; then
        echo "Python dependencies successfully installed"
    else
        echo "Error: Failed to install Python dependencies"
        echo "Please check the error messages and requirements.txt file"
        exit 1
    fi
else
    echo "Error: requirements.txt not found. Exiting."
    exit 1
fi

# Generate a secret key and write to .env file
print_header "Generating Django Secret Key"
SECRET_KEY=$(python3 -c 'import random; import string; print("".join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=50)))')

# Check if .env file exists, create it if not
if [ ! -f ".env" ]; then
    touch .env
fi

# Write the secret key to .env file
echo "SECRET_KEY=$SECRET_KEY" >> .env
echo "Django secret key generated and saved to .env file"
echo "Please ensure the .env file is secured and not exposed publicly."

# Update Apache Configuration File 1
print_header "Configuring Apache - Site Configuration"
APACHE_CONFIG_FILE_1="/etc/apache2/sites-available/000-default.conf"
FILENAME=$(basename "$APACHE_CONFIG_FILE_1")
DIRECTORY=$(dirname "$APACHE_CONFIG_FILE_1")

# a. Create config file for site (000-default.conf)
cat <<EOF > $FILENAME
<VirtualHost *:80>
    ServerAdmin webmaster@localhost
    DocumentRoot /var/www/html

    ErrorLog \${APACHE_LOG_DIR}/error.log
    CustomLog \${APACHE_LOG_DIR}/access.log combined

    Alias /static $(pwd)/static
    <Directory $(pwd)/static>
        Require all granted
    </Directory>

    <Directory $(pwd)/raspiPOS>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>

    WSGIDaemonProcess simorder user=www-data group=www-data python-home=$(pwd)/venv python-path=$(pwd)
    WSGIProcessGroup simorder
    WSGIScriptAlias / $(pwd)/raspiPOS/wsgi.py
</VirtualHost>
EOF

# b. Move config file to Apache's sites-available directory
if [ -d "$DIRECTORY" ]; then
    sudo mv -f $FILENAME $APACHE_CONFIG_FILE_1
    echo "Config file $APACHE_CONFIG_FILE_1 successfully updated"
else
    echo "Apache sites-available directory not found"
    exit 1
fi

# Update Apache Configuration File 2 (Global Apache Configuration)
print_header "Configuring Apache - Global Configuration"
APACHE_CONFIG_FILE_2="/etc/apache2/apache2.conf"
COMMAND_TO_ADD="WSGIApplicationGroup %{GLOBAL}"
echo "# Force WSGI application to run within (main) Python interpreter" | sudo tee -a /etc/apache2/apache2.conf > /dev/null
echo "WSGIApplicationGroup %{GLOBAL}" | sudo tee -a /etc/apache2/apache2.conf > /dev/null

if [ $? -eq 0 ]; then
    echo "Config file $APACHE_CONFIG_FILE_2 successfully updated"
else
    echo "Error: Failed to update Apache global configuration."
    exit 1
fi

# Configuring Django
print_header "Configuring Django static files"
PYTHON3_VENV=$(which python3)

# a. Collect static files
$PYTHON3_VENV $(pwd)/manage.py collectstatic --noinput
echo "Static files configured"

# Set permissions for Apache user (www-data)
print_header "Setting permissions for Apache user"

sudo chown -R www-data:www-data $(pwd)
sudo find $(pwd) -type d -exec chmod 750 {} +
sudo find $(pwd) -type f -exec chmod 640 {} +
sudo chmod 770 $(pwd)/static
sudo chmod 750 $(pwd)/raspiPOS/wsgi.py
sudo chmod 660 $(pwd)/db.sqlite3
sudo chmod -R 750 $(pwd)/venv
sudo usermod -aG www-data $USER
sudo chmod 750 $(pwd)
sudo chmod 755 $(dirname $(pwd))
sudo chmod 755 $(pwd)

echo "Permissions set for Apache user"

# b. USB
print_header "Configuring USB access"
sudo groupadd usbusers
sudo usermod -aG usbusers www-data

# c. Create udev rule for USB permissions
echo 'SUBSYSTEM=="usb", MODE="0660", GROUP="usbusers"' | sudo tee /etc/udev/rules.d/99-usb-permissions.rules
echo "USB permissions set"

# Configure sudoers for www-data
print_header "Configuring sudoers"
echo 'www-data ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot, /sbin/shutdown' | sudo EDITOR='tee -a' visudo
echo "Sudoers permissions set"

# Change hostname
print_header "Changing hostname"

# Set the new hostname
if ! sudo hostnamectl set-hostname "$HOSTNAME"; then
    echo "Error: Failed to change hostname. Exiting script."
    exit 1
fi

# Update /etc/hosts file
if ! sudo sed -i "s/^127.0.1.1.*/127.0.1.1\t$HOSTNAME/" /etc/hosts; then
    echo "Error: Failed to update /etc/hosts. Exiting script."
    exit 1
fi

echo "#########################################################################"
echo "After reboot, access simOrder from your browser: http://$(hostname).local"
echo "#########################################################################"

# Prompt for confirmation to reboot
print_header "Script execution completed"
echo "Your Raspberry Pi needs to be restarted so that changes take effect"
read -p "Do you want to do it now? (y/n): " answer

# Handling reboot after successful installation
case $answer in
    [Yy]* )
        echo "Rebooting now..."
        sudo reboot
        ;;
    [Nn]* )
        echo "Reboot canceled. You can reboot later if needed."
        ;;
    * )
        echo "Please answer yes or no."
        # Prompt again for a valid response
        read -p "Do you want to reboot the Raspberry Pi? (y/n): " answer
        case $answer in
            [Yy]* )
                echo "Rebooting now..."
                sudo reboot
                ;;
            [Nn]* )
                echo "Reboot canceled. You can reboot later if needed."
                ;;
            * )
                echo "Invalid input. Exiting without rebooting."
                ;;
        esac
        ;;
esac