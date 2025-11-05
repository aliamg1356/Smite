"""Hysteria2 server for panel-node communication"""
import asyncio
import ssl
import logging
from pathlib import Path
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class Hysteria2Server:
    """Hysteria2 server with mTLS for secure panel-node communication"""
    
    def __init__(self):
        self.port = settings.hysteria2_port
        self.cert_path = settings.hysteria2_cert_path
        self.key_path = settings.hysteria2_key_path
        self.server: Optional[asyncio.Server] = None
        self.clients = {}
    
    async def start(self):
        """Start Hysteria2 server"""
        # Ensure certs exist
        cert_path = Path(self.cert_path)
        key_path = Path(self.key_path)
        
        if not cert_path.exists() or not key_path.exists():
            # Generate self-signed cert for CA
            await self._generate_certs()
        
        # Start server (simplified - actual Hysteria2 integration would use their library)
        logger.info(f"Hysteria2 server starting on port {self.port}")
        # TODO: Integrate with actual Hysteria2 library
    
    async def stop(self):
        """Stop Hysteria2 server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
    
    async def _generate_certs(self):
        """Generate CA certificate and key"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from datetime import datetime, timedelta
        import os
        
        # Resolve paths (handle relative paths)
        cert_path = Path(self.cert_path)
        key_path = Path(self.key_path)
        
        # If relative paths, resolve from current working directory
        if not cert_path.is_absolute():
            # Try to resolve from app directory
            base_dir = Path(os.getcwd())
            cert_path = base_dir / cert_path
            key_path = base_dir / key_path
        
        logger.info(f"Generating certificate at: {cert_path}")
        logger.info(f"Generating key at: {key_path}")
        
        # Create directories
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure parent directories are writable
        if not os.access(cert_path.parent, os.W_OK):
            raise PermissionError(f"Cannot write to {cert_path.parent}")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "SF"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Smite Panel"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Smite CA"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate
        try:
            cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
            with open(cert_path, "wb") as f:
                f.write(cert_bytes)
            # Verify write
            if cert_path.stat().st_size == 0:
                raise IOError(f"Certificate file is empty after write: {cert_path}")
            logger.info(f"Certificate written successfully ({cert_path.stat().st_size} bytes)")
        except Exception as e:
            logger.error(f"Error writing certificate: {e}")
            raise
        
        # Write private key
        try:
            key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(key_path, "wb") as f:
                f.write(key_bytes)
            # Verify write
            if key_path.stat().st_size == 0:
                raise IOError(f"Key file is empty after write: {key_path}")
            logger.info(f"Key written successfully ({key_path.stat().st_size} bytes)")
        except Exception as e:
            logger.error(f"Error writing key: {e}")
            raise
        
        # Update paths in instance
        self.cert_path = str(cert_path)
        self.key_path = str(key_path)
        
        logger.info(f"Generated CA certificate at {cert_path}")

