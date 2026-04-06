# Bifrost Docs Test Environment - Proxmox VM Plan

## Goal
Create a dedicated Proxmox VM for bifrost-docs development/testing that matches bifrost-poc specs (8GB RAM, 80GB disk).

## Proxmox Host
- **Host:** pve.netbird.cloud (100.103.31.53)
- **Access:** SSH via Netbird
- **VM ID Range:** 100+ available (100, 201, 202 taken)

## Specifications

| Resource | Value |
|----------|-------|
| VM ID | 101 (next available) |
| Name | bifrost-docs-dev |
| CPU | 4 cores (match bifrost-poc) |
| Memory | 8192 MB (8GB) |
| Disk | 80GB |
| OS | Debian 13 (trixie) or Ubuntu 22.04 LTS |
| Network | DHCP via vmbr0 |

## Provisioning Steps

### 1. Download Cloud Image
```bash
# On Proxmox host
mkdir -p /var/lib/vz/template/iso
cd /var/lib/vz/template/iso

# Debian 13 (trixie) - latest stable
wget https://cloud.debian.org/images/cloud/trixie/latest/debian-13-generic-amd64.qcow2

# OR Ubuntu 22.04 LTS
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img
```

### 2. Create VM Template
```bash
# Create VM (Debian example)
qm create 101 --name bifrost-docs-dev --memory 8192 --cores 4 --net0 virtio,bridge=vmbr0

# Import disk
qm importdisk 101 debian-13-generic-amd64.qcow2 local-lvm

# Attach disk
qm set 101 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-101-disk-0

# Resize to 80GB
qm disk resize 101 scsi0 80G

# Add cloud-init drive
qm set 101 --ide2 local-lvm:cloudinit

# Set boot
qm set 101 --boot order=scsi0
```

### 3. Cloud-Init Configuration
```bash
# Set cloud-init user
qm set 101 --ciuser thomas

# Set SSH key (copy from current machine)
cat ~/.ssh/authorized_keys | qm set 101 --sshkeys -

# Network (DHCP)
qm set 101 --ipconfig0 ip=dhcp

# Optional: static IP if preferred
# qm set 101 --ipconfig0 ip=10.1.23.101/24,gw=10.1.23.1
```

### 4. Convert to Template (optional but recommended)
```bash
# Convert to template for quick cloning in future
qm template 101

# Future clones:
# qm clone 101 102 --name bifrost-docs-test-2 --full
```

### 5. Start VM and Verify
```bash
qm start 101

# Wait for boot, check IP
qm guest cmd 101 network-get-interfaces
# OR check DHCP leases
 cat /var/lib/misc/dnsmasq.leases
```

## Post-Provisioning (Inside VM)

### 1. Initial Setup
```bash
# SSH into VM (use IP from above)
ssh thomas@<vm-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install essentials
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    ca-certificates \
    gnupg \
    lsb-release
```

### 2. Install Docker
```bash
# Add Docker repo
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker thomas
```

### 3. Clone Bifrost Docs Repository
```bash
# Create workspace
mkdir -p ~/workspace
cd ~/workspace

# Clone repo
git clone https://github.com/MTG-Thomas/bifrost-docs.git
cd bifrost-docs
```

### 4. Install Netbird (for remote access)
```bash
# Install Netbird
export NETBIRD_FQDN=bifrost-docs-dev.netbird.cloud
curl -fsSL https://pkgs.netbird.io/install.sh | sh

# Join network (token from your netbird setup)
# sudo netbird up --management-url https://api.netbird.io:443 --setup-key <KEY>
```

### 5. Test Environment
```bash
# Start services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Verify health
curl http://localhost:8000/health
```

## Automation Script

Save this as `create-bifrost-docs-vm.sh` on Proxmox host:

```bash
#!/bin/bash
set -e

VMID=101
NAME="bifrost-docs-dev"
MEMORY=8192
CORES=4
DISK_SIZE=80G
IMAGE="/var/lib/vz/template/iso/debian-13-generic-amd64.qcow2"

# Download image if not exists
if [ ! -f "$IMAGE" ]; then
    echo "Downloading Debian 12 cloud image..."
    mkdir -p /var/lib/vz/template/iso
    wget -O "$IMAGE" https://cloud.debian.org/images/cloud/trixie/latest/debian-13-generic-amd64.qcow2
fi

# Destroy existing VM if present
if qm status $VMID &>/dev/null; then
    echo "Destroying existing VM $VMID..."
    qm stop $VMID || true
    qm destroy $VMID
fi

# Create VM
echo "Creating VM $VMID: $NAME"
qm create $VMID --name $NAME --memory $MEMORY --cores $CORES --net0 virtio,bridge=vmbr0

# Import disk
echo "Importing disk..."
qm importdisk $VMID $IMAGE local-lvm

# Configure
echo "Configuring VM..."
qm set $VMID --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-${VMID}-disk-0
qm disk resize $VMID scsi0 $DISK_SIZE
qm set $VMID --ide2 local-lvm:cloudinit
qm set $VMID --boot order=scsi0
qm set $VMID --ciuser thomas
qm set $VMID --ipconfig0 ip=dhcp

# Add SSH key if available
if [ -f ~/.ssh/authorized_keys ]; then
    qm set $VMID --sshkeys ~/.ssh/authorized_keys
fi

# Start VM
echo "Starting VM..."
qm start $VMID

echo "VM $VMID created and started!"
echo "Check IP with: qm guest cmd $VMID network-get-interfaces"
```

## Access Methods

### 1. Netbird (Recommended)
Once Netbird is installed in VM:
- FQDN: `bifrost-docs-dev.netbird.cloud`
- Access from any Netbird-connected machine

### 2. Port Forwarding (Alternative)
On Proxmox host:
```bash
# Forward local port 8080 to VM's port 8080
iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination <vm-ip>:8080
```

### 3. SSH Jump
```bash
ssh -J root@pve.netbird.cloud thomas@<vm-internal-ip>
```

## Resource Management

### Start VM
```bash
ssh root@pve.netbird.cloud "qm start 101"
```

### Stop VM
```bash
ssh root@pve.netbird.cloud "qm stop 101"
```

### Snapshot (before major changes)
```bash
ssh root@pve.netbird.cloud "qm snapshot 101 clean-state"
```

### Clone for Parallel Testing
```bash
ssh root@pve.netbird.cloud "qm clone 101 102 --name bifrost-docs-test-branch --full"
```

## Testing Workflow

1. **Developer pushes code** to feature branch
2. **SSH to bifrost-docs-dev VM**
3. **Pull latest code**: `git pull origin feature-branch`
4. **Run tests**: `./test.sh`
5. **Verify**: `docker compose logs -f`
6. **Snapshot**: `qm snapshot 101 test-passed`

## Cost/Benefit

- **No local resource usage** - Laptop stays responsive
- **Consistent environment** - Same specs for all devs
- **Snapshot/rollback** - Easy to test destructive changes
- **24/7 availability** - Can run long tests overnight
- **Parallel testing** - Clone VMs for branch isolation

## Next Steps

1. Review and approve plan
2. Run provisioning script on Proxmox host
3. Install Docker and dependencies in VM
4. Clone bifrost-docs repo
5. Test environment with `./test.sh`
6. Document VM IP/Netbird FQDN for team access