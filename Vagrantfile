# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Use standard Ubuntu 22.04 LTS box
  config.vm.box = "ubuntu/jammy64"
  config.vm.hostname = "ebpf-cyberrange"

  # Forward necessary ports if you want to access webdis/vector from Windows
  config.vm.network "forwarded_port", guest: 7379, host: 7379
  config.vm.network "forwarded_port", guest: 8686, host: 8686

  # VirtualBox specific configuration
  config.vm.provider "virtualbox" do |vb|
    # Minimum 4GB RAM is recommended for running the entire pipeline
    vb.memory = "4096"
    vb.cpus = 2
    vb.name = "ebpf-cyberrange-vm"
  end

  # Provisioning script to install Docker, Docker Compose, and eBPF kernel dependencies
  config.vm.provision "shell", inline: <<-SHELL
    export DEBIAN_FRONTEND=noninteractive
    echo "Updating system..."
    apt-get update

    echo "Installing kernel headers & tools for eBPF BTF support..."
    apt-get install -y linux-headers-$(uname -r) linux-tools-common linux-tools-generic \
      bpfcc-tools libbpf-dev clang llvm jq

    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker vagrant

    echo "Ensure BTF is exposed..."
    if [ ! -f /sys/kernel/btf/vmlinux ]; then
      echo "WARNING: /sys/kernel/btf/vmlinux not found! Check kernel version."
    else
      echo "BTF file found at /sys/kernel/btf/vmlinux"
    fi

    echo "Provisioning complete. Please 'vagrant ssh' into the VM and run 'cd /vagrant && docker compose up -d --build'."
  SHELL
end
