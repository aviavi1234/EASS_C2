import sys

with open('frontend/c2_gui/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add the SSL generation function
ssl_gen_code = '''
def _ensure_self_signed_cert(cert_path="cert.pem", key_path="key.pem"):
    import os
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return True
        
    try:
        import datetime
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        
        print("Generating self-signed SSL certificate for HTTPS...")
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"C2 Local Dev"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        ])
        cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
            private_key.public_key()
        ).serial_number(x509.random_serial_number()).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName(u"localhost")]), critical=False
        ).sign(private_key, hashes.SHA256())

        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        return True
    except Exception as e:
        print(f"Warning: Could not generate SSL certificate: {e}")
        return False

def main() -> None:'''

content = content.replace("def main() -> None:", ssl_gen_code)

# Add argparse for https
main_old = '''    parser = argparse.ArgumentParser(description="C2 operations map (NiceGUI)")
    default_port = int(os.getenv("C2_GUI_PORT", "8081"))
    parser.add_argument("--port", type=int, default=default_port)
    args = parser.parse_args()'''

main_new = '''    parser = argparse.ArgumentParser(description="C2 operations map (NiceGUI)")
    default_port = int(os.getenv("C2_GUI_PORT", "8081"))
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument("--https", action="store_true", help="Enable HTTPS (required for mobile GPS)")
    args = parser.parse_args()'''

content = content.replace(main_old, main_new)

# Update ui.run call
run_old = '''    ui.run(
        title="C2 Operations",
        storage_secret="c2-local-dev-secret-change-me",
        reload=False,
        port=port,
    )'''

run_new = '''    run_kwargs = {
        "title": "C2 Operations",
        "storage_secret": "c2-local-dev-secret-change-me",
        "reload": False,
        "port": port,
    }
    
    if args.https and _ensure_self_signed_cert():
        run_kwargs["ssl_certfile"] = "cert.pem"
        run_kwargs["ssl_keyfile"] = "key.pem"
        print(f"Starting with HTTPS enabled. Use https://<your-ip>:{port} in your mobile browser.")
        print("Note: Your browser will warn about 'Not Secure'. You must click 'Advanced' -> 'Proceed' to access the site and use GPS.")
        
    ui.run(**run_kwargs)'''

content = content.replace(run_old, run_new)

with open('frontend/c2_gui/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated main.py")
