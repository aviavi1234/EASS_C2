"""Generate self-signed TLS certificates for local HTTPS development."""

from __future__ import annotations

import datetime
import ipaddress
import socket
from pathlib import Path

from backend.paths import DEFAULT_CERT_FILE, DEFAULT_KEY_FILE, ensure_data_dirs


def _local_ipv4_addresses() -> list[str]:
    ips: set[str] = {"127.0.0.1"}
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            ips.add(ip)
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ips.add(sock.getsockname()[0])
    except OSError:
        pass
    return sorted(ips)


def _cert_needs_regeneration(cert_file: Path) -> bool:
    """Regenerate legacy certs missing serverAuth (mobile browsers may reject them)."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import ExtensionOID, ExtendedKeyUsageOID

        cert = x509.load_pem_x509_certificate(cert_file.read_bytes())
        for ext in cert.extensions:
            if ext.oid == ExtensionOID.EXTENDED_KEY_USAGE:
                return ExtendedKeyUsageOID.SERVER_AUTH not in ext.value
        return True
    except Exception:
        return True


def ensure_ssl_cert(
    cert_path: Path | str | None = None,
    key_path: Path | str | None = None,
    *,
    force: bool = False,
) -> tuple[Path, Path] | None:
    cert_file = Path(cert_path or DEFAULT_CERT_FILE)
    key_file = Path(key_path or DEFAULT_KEY_FILE)
    ensure_data_dirs()

    if (
        not force
        and cert_file.exists()
        and key_file.exists()
        and not _cert_needs_regeneration(cert_file)
    ):
        return cert_file, key_file

    if cert_file.exists() and key_file.exists():
        print("Regenerating SSL certificate (missing or outdated extensions)...")
        cert_file.unlink(missing_ok=True)
        key_file.unlink(missing_ok=True)

    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    except ImportError as exc:
        print(f"Warning: Could not generate SSL certificate: {exc}")
        return None

    print("Generating self-signed SSL certificate for HTTPS...")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "C2 Local Dev"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    alt_names: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    for ip in _local_ipv4_addresses():
        if ip == "127.0.0.1":
            continue
        try:
            alt_names.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
        except ValueError:
            pass

    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )

    cert_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.parent.mkdir(parents=True, exist_ok=True)

    with open(key_file, "wb") as handle:
        handle.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(cert_file, "wb") as handle:
        handle.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Generated {cert_file} and {key_file}")
    return cert_file, key_file
