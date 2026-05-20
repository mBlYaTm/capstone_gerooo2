# crypto_utils.py - SHA-256 хэшлэх функцүүд
import hashlib
import hmac


def hash_token(token: str) -> str:
    """Токеныг SHA-256 хэшэд хувиргана. Жинхэнэ токен хэзээ ч хадгалагдахгүй."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, stored_hash: str) -> bool:
    """Токений хэш зөв эсэхийг шалгана. Constant-time comparison ашиглана."""
    computed = hash_token(token)
    return hmac.compare_digest(computed, stored_hash)
