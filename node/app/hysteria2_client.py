"""Hysteria2 client for node to connect to panel"""
import asyncio
import httpx
import hashlib
import socket
from pathlib import Path
from typing import Optional
from app.config import settings


class Hysteria2Client:
    """Client connecting to panel via HTTPS"""
    
    def __init__(self):
        self.panel_address = settings.panel_address
        self.ca_path = Path(settings.panel_ca_path)
        self.client = None
        self.node_id = None
        self.fingerprint = None
        self.registered = False
    
    async def start(self):
        """Start client and connect to panel"""
        if not self.ca_path.exists():
            raise FileNotFoundError(f"CA certificate not found at {self.ca_path}")
        
        # Generate node fingerprint
        await self._generate_fingerprint()
        
        # Create HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            verify=False  # In production, verify with CA cert
        )
        
        print(f"Node client ready, panel address: {self.panel_address}")
    
    async def stop(self):
        """Stop client"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def register_with_panel(self):
        """Auto-register with panel"""
        if not self.client:
            await self.start()
        
        # Parse panel address
        # Format: host:port or http://host:port
        if "://" in self.panel_address:
            protocol, rest = self.panel_address.split("://", 1)
            if ":" in rest:
                panel_host, panel_hysteria_port = rest.split(":", 1)
            else:
                panel_host = rest
                panel_hysteria_port = "443"
        else:
            protocol = "http"  # Default to http for API
            if ":" in self.panel_address:
                panel_host, panel_hysteria_port = self.panel_address.split(":", 1)
            else:
                panel_host = self.panel_address
                panel_hysteria_port = "443"
        
        # Panel API is usually on a different port (8000 by default)
        # Try to get from environment or use default
        panel_api_port = 8000  # Default API port
        
        # Construct panel API URL
        panel_api_url = f"http://{panel_host}:{panel_api_port}"
        
        # Get node's actual IP/address for panel to connect back
        import socket
        try:
            # Try to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            node_ip = s.getsockname()[0]
            s.close()
        except:
            node_ip = "0.0.0.0"
        
        registration_data = {
            "name": settings.node_name,
            "ip_address": node_ip,
            "api_port": settings.node_api_port,
            "fingerprint": self.fingerprint,
            "metadata": {
                "api_address": f"http://{node_ip}:{settings.node_api_port}",
                "node_name": settings.node_name,
                "panel_address": self.panel_address
            }
        }
        
        try:
            url = f"{panel_api_url}/api/nodes"
            print(f"Registering with panel at {url}...")
            response = await self.client.post(url, json=registration_data, timeout=10.0)
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.node_id = data.get("id")
                self.registered = True
                logger.info(f"Node registered successfully with ID: {self.node_id}")
                return True
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return False
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to panel at {panel_api_url}: {str(e)}")
            print(f"   Make sure panel is running and accessible")
            return False
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return False
    
    async def _generate_fingerprint(self):
        """Generate node fingerprint for identification"""
        import socket
        # Generate fingerprint from hostname + MAC
        hostname = socket.gethostname()
        fingerprint_data = f"{hostname}-{settings.node_name}".encode()
        self.fingerprint = hashlib.sha256(fingerprint_data).hexdigest()[:16]
        print(f"Node fingerprint: {self.fingerprint}")
    
    async def push_usage_to_panel(self, tunnel_id: str, node_id: str, bytes_used: int):
        """Push usage data to panel"""
        if not self.client or not self.node_id:
            return False
        
        # Get panel API URL (same logic as register_with_panel)
        if "://" in self.panel_address:
            protocol, rest = self.panel_address.split("://", 1)
            if ":" in rest:
                panel_host, _ = rest.split(":", 1)
            else:
                panel_host = rest
        else:
            if ":" in self.panel_address:
                panel_host, _ = self.panel_address.split(":", 1)
            else:
                panel_host = self.panel_address
        
        panel_api_port = 8000  # Default API port
        panel_api_url = f"http://{panel_host}:{panel_api_port}"
        
        try:
            url = f"{panel_api_url}/api/usage/push"
            response = await self.client.post(
                url,
                json={
                    "tunnel_id": tunnel_id,
                    "node_id": node_id or self.node_id,
                    "bytes_used": bytes_used
                },
                timeout=10.0
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Warning: Failed to push usage to panel: {e}")
            return False
