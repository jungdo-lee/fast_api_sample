"""Generate RSA key pair for JWT signing."""
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_rsa_keys(output_dir: str = "keys") -> None:
    key_dir = Path(output_dir)
    key_dir.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path = key_dir / "private.pem"
    public_path = key_dir / "public.pem"

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    os.chmod(private_path, 0o600)
    os.chmod(public_path, 0o644)

    print(f"RSA keys generated in {key_dir}/")
    print(f"  Private key: {private_path}")
    print(f"  Public key:  {public_path}")


if __name__ == "__main__":
    generate_rsa_keys()
