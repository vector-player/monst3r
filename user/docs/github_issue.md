# 🔧 GitHub DNS Resolution Issue - Troubleshooting Guide

## 📋 Overview

This document describes a DNS resolution issue encountered when connecting to GitHub via SSH from a Docker container or network environment with custom DNS configuration.

## 🚨 Problem Description

### Symptoms

When attempting to push to GitHub or connect via SSH, you encounter:

```
ssh: connect to host github.com port 22: Connection timed out
fatal: 无法读取远程仓库。

请确认您有正确的访问权限并且仓库存在。
```

### Error Breakdown

1. **Connection Timeout**: SSH cannot connect to `github.com` on port 22
2. **DNS Misresolution**: `github.com` resolves to an incorrect private IP address (`192.168.11.10`)
3. **Git Push Failure**: Git operations fail due to SSH connection issues

## 🔍 Root Causes

### 1. DNS Misconfiguration

The system's DNS resolver is redirecting GitHub domains to a private IP address:

```bash
$ host github.com
github.com has address 192.168.11.10  # ❌ Wrong! Should be GitHub's public IP
```

**Why this happens:**
- Docker's internal DNS resolver (`127.0.0.11`) may redirect traffic
- Corporate proxy/gateway configurations
- Network-level DNS manipulation
- `/etc/resolv.conf` pointing to a custom DNS server

### 2. Port 22 Blocked

Even with correct DNS, port 22 (SSH) may be blocked by:
- Firewall rules
- Network security policies
- Corporate network restrictions
- ISP-level blocking

### 3. Network Environment

Common in:
- Docker containers with custom network configurations
- Corporate networks with proxy servers
- VPN-connected environments
- Restricted network environments

## ✅ Solutions

### Solution 1: Fix DNS Resolution (Recommended)

Add correct GitHub IP addresses to `/etc/hosts` to override DNS resolution.

#### Step-by-Step Fix

```bash
# 1. Check current DNS resolution
host github.com
getent hosts github.com

# 2. Add GitHub IPs to /etc/hosts
sudo bash -c 'cat >> /etc/hosts << EOF
# GitHub DNS override - added to fix DNS resolution issue
140.82.112.4  github.com
140.82.112.4  ssh.github.com
EOF'

# 3. Verify DNS resolution
getent hosts github.com
getent hosts ssh.github.com

# 4. Test SSH connection
ssh -T xgy1-vp-gh
```

#### Expected Output After Fix

```bash
$ getent hosts github.com
140.82.112.4    github.com  # ✅ Correct IP

$ ssh -T xgy1-vp-gh
Hi username! You've successfully authenticated...  # ✅ Connection works
```

#### Alternative GitHub IPs

If `140.82.112.4` doesn't work, try these GitHub IP ranges:

```bash
# Add multiple IPs for redundancy
sudo bash -c 'cat >> /etc/hosts << EOF
# GitHub DNS override
140.82.112.4  github.com
140.82.112.4  ssh.github.com
192.30.252.0  github.com
185.199.108.0  github.com
EOF'
```

**Note**: GitHub uses multiple IP addresses. You can find current IPs using:
```bash
curl -s https://api.github.com/meta | grep -A 5 '"git"'
```

### Solution 2: Use HTTPS Instead of SSH

If DNS/SSH issues persist, switch to HTTPS authentication:

```bash
# Change remote URL from SSH to HTTPS
git remote set-url remote1 https://github.com/vector-player/Depth-Anything-3.git

# Push using HTTPS (will prompt for credentials or token)
git push -u --force remote1 main
```

**Advantages:**
- Works even when SSH is blocked
- Simpler authentication (personal access token)
- No DNS resolution issues

**Disadvantages:**
- Requires entering credentials/token each time
- Less secure than SSH keys (if not using token)

### Solution 3: Use SSH Over Port 443

If port 22 is blocked but port 443 (HTTPS) is open, configure SSH to use port 443:

#### Update SSH Config

```bash
# Edit ~/.ssh/config
cat >> ~/.ssh/config << EOF
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile ~/.ssh/xgy1
EOF
```

#### Test Connection

```bash
ssh -T git@github.com
```

### Solution 4: Configure Docker DNS

If running in Docker, configure DNS at container level:

```bash
# Run container with custom DNS
docker run --dns 8.8.8.8 --dns 8.8.4.4 ...

# Or in docker-compose.yml
services:
  your-service:
    dns:
      - 8.8.8.8
      - 8.8.4.4
```

## 🔬 Diagnosis Steps

### 1. Check DNS Resolution

```bash
# Check what IP github.com resolves to
host github.com
getent hosts github.com
nslookup github.com

# Should show GitHub's public IP, not private IPs like 192.168.x.x
```

### 2. Check Network Connectivity

```bash
# Test if GitHub IP is reachable
ping -c 3 140.82.112.4

# Test SSH port 22
telnet github.com 22
# Or
nc -zv github.com 22

# Test HTTPS port 443
nc -zv github.com 443
```

### 3. Check SSH Configuration

```bash
# View SSH config
cat ~/.ssh/config

# Test SSH connection with verbose output
ssh -vT xgy1-vp-gh
```

### 4. Check Git Remote Configuration

```bash
# View remote URLs
git remote -v

# Check if using SSH or HTTPS
git remote get-url remote1
```

## 📝 Verification Checklist

After applying the fix, verify:

- [ ] `getent hosts github.com` shows correct GitHub IP (not 192.168.x.x)
- [ ] `ping 140.82.112.4` succeeds
- [ ] `ssh -T xgy1-vp-gh` connects (may show auth error, but no timeout)
- [ ] `git push` no longer shows "Connection timed out" error

## ⚠️ Common Issues After DNS Fix

### Issue 1: SSH Authentication Error

**Error:**
```
Permission denied (publickey)
```

**Cause:** DNS is fixed, but SSH key authentication fails.

**Solutions:**
1. Verify SSH key is added to GitHub account
2. Check SSH key permissions: `chmod 600 ~/.ssh/xgy1`
3. Use SSH agent: `ssh-add ~/.ssh/xgy1`
4. Switch to HTTPS authentication

### Issue 2: DNS Fix Not Persistent

**Problem:** `/etc/hosts` changes are lost after container restart.

**Solutions:**
1. **Docker**: Mount `/etc/hosts` or use `--add-host` flag:
   ```bash
   docker run --add-host github.com:140.82.112.4 ...
   ```

2. **Docker Compose**: Add to `docker-compose.yml`:
   ```yaml
   services:
     your-service:
       extra_hosts:
         - "github.com:140.82.112.4"
         - "ssh.github.com:140.82.112.4"
   ```

3. **Systemd**: Create a systemd service to update `/etc/hosts` on boot

4. **Init Script**: Add DNS fix to container's entrypoint script

### Issue 3: Multiple GitHub IPs

**Problem:** GitHub uses multiple IP addresses, and one may be blocked.

**Solution:** Add multiple IPs to `/etc/hosts`:
```bash
sudo bash -c 'cat >> /etc/hosts << EOF
140.82.112.4  github.com
192.30.252.0  github.com
185.199.108.0  github.com
EOF'
```

## 🔄 Permanent Solutions

### For Docker Containers

Create a startup script that fixes DNS on container start:

```bash
#!/bin/bash
# /usr/local/bin/fix-github-dns.sh

if ! grep -q "github.com" /etc/hosts; then
    echo "140.82.112.4  github.com" >> /etc/hosts
    echo "140.82.112.4  ssh.github.com" >> /etc/hosts
    echo "DNS fix applied"
fi
```

Add to Dockerfile:
```dockerfile
COPY fix-github-dns.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/fix-github-dns.sh
ENTRYPOINT ["/usr/local/bin/fix-github-dns.sh"]
CMD ["your-app"]
```

### For System-Wide Fix

If you have root access, configure DNS resolver:

```bash
# Edit /etc/resolv.conf (may be overwritten by NetworkManager)
# Or configure NetworkManager/DHCP to use correct DNS servers
```

## 📚 Related Issues

### SSH Key Authentication

After fixing DNS, you may encounter SSH authentication issues. See:
- GitHub SSH key setup: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
- SSH key troubleshooting: https://docs.github.com/en/authentication/troubleshooting-ssh

### Git Push Errors

Common git push errors and solutions:
- `Permission denied`: Check SSH key or use HTTPS
- `Connection refused`: Check firewall/network settings
- `Repository not found`: Verify repository name and permissions

## 🎯 Quick Reference

### Quick Fix Command

```bash
# One-liner to fix DNS
sudo bash -c 'echo -e "\n# GitHub DNS fix\n140.82.112.4  github.com\n140.82.112.4  ssh.github.com" >> /etc/hosts' && getent hosts github.com
```

### Test Connection

```bash
# Test DNS
getent hosts github.com

# Test SSH
ssh -T xgy1-vp-gh

# Test Git
git push remote1 main
```

### Revert DNS Fix

```bash
# Remove GitHub entries from /etc/hosts
sudo sed -i '/github.com/d' /etc/hosts
sudo sed -i '/ssh.github.com/d' /etc/hosts
```

## 📖 Additional Resources

- [GitHub SSH Troubleshooting](https://docs.github.com/en/authentication/troubleshooting-ssh)
- [GitHub IP Addresses](https://api.github.com/meta)
- [Docker DNS Configuration](https://docs.docker.com/config/containers/container-networking/#dns-services)
- [SSH Config Documentation](https://www.ssh.com/academy/ssh/config)

## 🔍 Troubleshooting Log

### Initial State
```
$ host github.com
github.com has address 192.168.11.10  # ❌ Wrong IP

$ ssh -T xgy1-vp-gh
ssh: connect to host github.com port 22: Connection timed out  # ❌ Timeout
```

### After DNS Fix
```
$ getent hosts github.com
140.82.112.4    github.com  # ✅ Correct IP

$ ssh -T xgy1-vp-gh
git@github.com: Permission denied (publickey)  # ✅ Connected (auth issue, not DNS)
```

### After Authentication Fix
```
$ ssh -T xgy1-vp-gh
Hi username! You've successfully authenticated...  # ✅ Fully working
```

---

**Last Updated**: Based on troubleshooting experience with Docker containers and GitHub connectivity

**Related Files**: 
- `/etc/hosts` - DNS override configuration
- `~/.ssh/config` - SSH configuration
- `.git/config` - Git remote configuration
