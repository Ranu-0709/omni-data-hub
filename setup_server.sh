#!/bin/bash
# This script prepares the Google Cloud Ubuntu machine.

echo "Updating Ubuntu..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo "Installing Docker..."
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-compose-plugin

echo "Installing code-server for Jio PC browser access..."
curl -fsSL https://code-server.dev/install.sh | sh
sudo systemctl enable --now code-server@$USER

echo "Server setup is complete. Code-server is running."
