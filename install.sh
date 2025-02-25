#!/bin/bash

# Function to print section headers
print_header() {
    echo "----------------------------------------"
    echo "$1"
    echo "----------------------------------------"
}

# Variables
current_user=$USER
current_path=$(pwd)
current_app='simorder'

# Check if file structure has been correctly copied from development drive
print_header "IMPORTANT:"
echo "Make sure all file structures from the Django project and app are copied correctly before proceeding."
echo "Please verify that the following directory structure exists:"
echo "/home/$current_user/raspiPOS/"
echo "    ├── install.sh"
echo "    ├── db.sqlite3.py"
echo "    ├── manage.py"
echo "    ├── requirements.txt"
echo "    ├── raspiPOS/"
echo "    |   ├── ..."
echo "    └── simorder/"
echo "    |   ├── ..."
echo "    └── static/"
echo "    |   ├── ..."

read -p "Have you verified the file structure? (y/n): " answer

if [[ $answer != "y" ]]; then
    echo "Please copy the correct file structure and run the script again."
    exit 1
fi

echo "Proceeding with the setup..."

# Change comitup name
print_header "Changing comitup name"
sudo comitup-cli n $current_app
echo "Comitup hostname updated to $current_app"

# Update Raspberry Pi
print_header "Updating Raspberry Pi"
sudo apt-get update && sudo apt dist-upgrade -y && sudo apt-get autoremove -y

# Install Apache and configure
print_header "Installing and configuring Apache"
sudo apt install apache2 -y

# Install additional packages
print_header "Installing additional packages"
sudo apt install libapache2-mod-wsgi-py3 -y
sudo apt-get install libjpeg-dev -y
sudo apt install python3 python3-venv python3-pip -y

# Create and activate virtual environment
print_header "Creating virtual environment"
python3 -m venv venv
source venv/bin/activate

# Install project dependencies
print_header "Installing project dependencies"
pip3 install -r requirements.txt

# Update Apache configuration file
print_header "Configuring Apache"
config_file="/etc/apache2/sites-enabled/000-default.conf"
master_file="/home/$current_user/raspiPOS/000-default.conf"

# a. Check if the file exists
if [[ ! -f "$config_file" ]]; then
    echo "Error: $config_file does not exist."
    exit 1
fi

# b. Create a backup of the original file
sudo cp "$config_file" "$config_file.bak"

# c. Move the master file to the config file
sudo mv "$master_file" "$config_file"

echo "Config file $config_file successfully updated"

# d. Force WSGI application to run within (main) Python interpreter
config_file="/etc/apache2/apache2.conf"
command_to_add="WSGIApplicationGroup %{GLOBAL}"

# e. Check if the file exists
if [[ ! -f "$config_file" ]]; then
    echo "Error: $config_file does not exist."
    exit 1
fi

# f. Append the command to the end of the file
{
    echo ""
    echo "# Force WSGI application to run within (main) Python interpreter"
    echo "$command_to_add"
} | sudo tee -a "$config_file" > /dev/null

if [ $? -eq 0 ]; then
    echo "Config file $config_file successfully updated"
else
    echo "Failed to update $config_file"
    exit 1
fi

# Configuring Django
print_header "Configuring Django"
django_root="/home/$current_user/raspiPOS/"
django_migrations="$django_root$current_app/migrations"
python3_venv=$django_root"venv/bin/python3"

# a. Collect static files
print_header "Collecting static files"
$python3_venv $django_root/manage.py collectstatic

# b. Reset Django database
print_header "Reset Django database"
find $django_migrations -type f -name '*.py' ! -name '__init__.py' -delete
$python3_venv $django_root/manage.py flush
$python3_venv $django_root/manage.py makemigrations
$python3_venv $django_root/manage.py migrate

# c. Create superuser admin w/ pass admin
print_header "Create Django superuser"
$python3_venv manage.py createsuperuser

# Set permissions
print_header "Setting permissions for Apache user"
# a. Django database
sudo chmod -R u+w /home/dubaleeiro/raspiPOS
sudo chown www-data:www-data /home/dubaleeiro/raspiPOS
sudo chmod -R 775 /home/dubaleeiro/raspiPOS
sudo chown www-data:www-data /home/dubaleeiro/raspiPOS/db.sqlite3
sudo chmod 664 /home/dubaleeiro/raspiPOS/db.sqlite3
sudo usermod -aG www-data dubaleeiro
echo "Databaase permissions set"

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

# Modify comitup configuration
print_header "Modifying comitup configuration"
sudo sed -i "/# web_service: httpd.service/a web_service: apache2.service" /etc/comitup.conf
echo "Config file successfully updated"

# Prompt for confirmation to reboot
print_header "Script execution completed"
echo "Your Raspberry Pi needs to be restarted so that changes take effect"
read -p "Do you want to do it now? (y/n): " answer

# Handling reboot after successful instalation
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