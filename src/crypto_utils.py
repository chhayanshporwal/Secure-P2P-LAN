import os
import struct
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from Crypto.Cipher import AES

def generate_ecc_key_pair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    return private_key, public_key

def serialize_public_key(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def deserialize_public_key(pem_data):
    return serialization.load_pem_public_key(pem_data)

def generate_aes_key():
    return os.urandom(32) # 256-bit key

def encrypt_aes_key_with_ecc(aes_key, receiver_public_key):
    # ECIES-like encryption
    ephemeral_private_key = ec.generate_private_key(ec.SECP256R1())
    ephemeral_public_key = ephemeral_private_key.public_key()
    
    shared_secret = ephemeral_private_key.exchange(ec.ECDH(), receiver_public_key)
    
    # Derive a symmetric key from the shared secret
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
    ).derive(shared_secret)
    
    # Encrypt the AES key using the derived key
    nonce = os.urandom(16)
    cipher = AES.new(derived_key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(aes_key)
    
    ephemeral_pub_bytes = serialize_public_key(ephemeral_public_key)
    
    # Format: [Ephemeral Pub Key Len (4 bytes)][Ephemeral Pub Key][Nonce (16 bytes)][Tag (16 bytes)][Ciphertext]
    payload = struct.pack("!I", len(ephemeral_pub_bytes)) + ephemeral_pub_bytes + nonce + tag + ciphertext
    return payload

def decrypt_aes_key_with_ecc(payload, receiver_private_key):
    # ECIES-like decryption
    pub_key_len = struct.unpack("!I", payload[:4])[0]
    offset = 4
    
    ephemeral_pub_bytes = payload[offset:offset+pub_key_len]
    offset += pub_key_len
    
    ephemeral_public_key = deserialize_public_key(ephemeral_pub_bytes)
    
    nonce = payload[offset:offset+16]
    offset += 16
    
    tag = payload[offset:offset+16]
    offset += 16
    
    ciphertext = payload[offset:]
    
    shared_secret = receiver_private_key.exchange(ec.ECDH(), ephemeral_public_key)
    
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
    ).derive(shared_secret)
    
    cipher = AES.new(derived_key, AES.MODE_GCM, nonce=nonce)
    aes_key = cipher.decrypt_and_verify(ciphertext, tag)
    return aes_key

def encrypt_chunk(chunk, aes_key):
    nonce = os.urandom(16)
    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(chunk)
    # Format: [Nonce (16 bytes)][Tag (16 bytes)][Ciphertext]
    return nonce + tag + ciphertext

def decrypt_chunk(encrypted_chunk, aes_key):
    nonce = encrypted_chunk[:16]
    tag = encrypted_chunk[16:32]
    ciphertext = encrypted_chunk[32:]
    
    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)
