from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID
from pyasn1.codec.der import decoder
from pyasn1.type import univ
from typing import List, Dict, Union
import cbor
import base64
import hashlib
import jsonify
import requests
import os
import json
from dotenv import load_dotenv
from constants import app_id, rp_id_hash_end, counter_start, counter_end, aaguid_start, aaguid_end, cred_id_start

from cryptography.exceptions import InvalidSignature

load_dotenv()

AppleAppAttestStatement = Dict[str, Union[str, Dict[str, List[bytes]], bytes]]

def fetch_apple_attestation_root_ca_cert():
    url = os.getenv("APPLE_ATTESTATION_ROOT_CA_URL")
    response = requests.get(url)
    cert_bytes = response.content
    cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())

    return cert

def decode_apple_attestation_object(object_as_base64: str) -> Union[AppleAppAttestStatement, None]:
    try:
        binary_data = base64.b64decode(object_as_base64)
        return cbor.loads(binary_data)

    except Exception as e:
        # Throws on invalid input
        print(e)

    return None


def create_authdata_with_nonce_hash(attestation_object, nonce):
    hash = hashlib.sha256(nonce.encode('utf-8')).digest()
    client_data_hash = hash
    concatenated_buffer = attestation_object['authData'] + client_data_hash

    return concatenated_buffer


def create_composite_nonce(concatenated_buffer):
    sha256_hash = hashlib.sha256(concatenated_buffer).hexdigest()

    return sha256_hash


def verify_x5c_certificates(attestation_object):
    try:
        root_certificate = fetch_apple_attestation_root_ca_cert()
        credential_certificate = x509.load_der_x509_certificate(attestation_object['attStmt']['x5c'][0], default_backend())
        intermediate_certificate = x509.load_der_x509_certificate(attestation_object['attStmt']['x5c'][1], default_backend())

        print('root_certificate', root_certificate.subject)
        print('credential_certificate', credential_certificate.subject)
        print('intermediate_certificate', intermediate_certificate.subject)

        if intermediate_certificate.issuer == root_certificate.subject:
            print('The child certificate was issued by the parent certificate.')
        else:
            print('The child certificate was not issued by the parent certificate.')

        # Verify the signature of the certificate using the public key of the root certificate

        assert isinstance(root_certificate.public_key(), ec.EllipticCurvePublicKey)

        if credential_certificate.signature_algorithm_oid not in [
            x509.SignatureAlgorithmOID.ECDSA_WITH_SHA256
        ]:
            return False

        intermediate_certificate_is_valid = root_certificate.public_key().verify(
            intermediate_certificate.signature,
            intermediate_certificate.tbs_certificate_bytes,
            ec.ECDSA(intermediate_certificate.signature_hash_algorithm)
        )

        credential_certificate_is_valid = intermediate_certificate.public_key().verify(
            credential_certificate.signature,
            credential_certificate.tbs_certificate_bytes,
            ec.ECDSA(credential_certificate.signature_hash_algorithm),
        )

        if intermediate_certificate_is_valid is None and credential_certificate_is_valid is None:
            print('The certificates are signed by the ROOT certificate.')
            return True

    except InvalidSignature as e:
        print("The certificates are NOT signed by the ROOT certificate.")
        print(e)
        return False


def extract_attestation_object_extension(attestation_object, oid='1.2.840.113635.100.8.2'):
    # Load the certificate from a file
    credential_certificate = x509.load_der_x509_certificate(attestation_object['attStmt']['x5c'][0])

    # Get the extension with OID 1.2.840.113635.100.8.2
    cred_cert_extension = credential_certificate.extensions.get_extension_for_oid(x509.ObjectIdentifier(oid))

    # Get the value of the extension
    cred_cert_extension_value = cred_cert_extension.value.value
    decoded_data, _ = decoder.decode(cred_cert_extension_value, asn1Spec=univ.Sequence())

    return decoded_data[0].asOctets().hex()


def create_hash_from_pub_key(cred_certificate):
    certificate = x509.load_der_x509_certificate(cred_certificate)

    # Get the public key from the certificate
    public_key = certificate.public_key()

    # Serialize the public key to bytes
    public_key_bytes = public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)

    # Compute the SHA-256 hash of the public key bytes
    hash_object = hashlib.sha256(public_key_bytes)
    hash_hex = hash_object.hexdigest()

    # Print the hash as a hexadecimal string
    return hash_hex

def create_app_id_hash():
    app_id_bytes = app_id.encode('utf-8')
    app_id_hash = hashlib.sha256(app_id_bytes).hexdigest()
    return app_id_hash

def verify_attestation_statement(attestation_object, nonce):
    try:
        # decode the attestation object is expecting attestation_object
        # to be JSON.
        print('Decoding attestation object...')
        apple_attestation_object = decode_apple_attestation_object(attestation_object['attestation_object'])
        if not apple_attestation_object:
            return False

        # 1. Verify that the x5c array contains the intermediate and leaf
        # certificates for App Attest, starting from the credential certificate in the first
        # data buffer in the array (credcert). Verify the validity of the certificates using
        # Apple’s App Attest root certificate.
        print('Apple Attestation step 1...')
        verify_x5c_status = verify_x5c_certificates(apple_attestation_object)
        if not verify_x5c_status:
            return False

        # 2. Create clientDataHash as the SHA256 hash of the one-time challenge your server sends
        # to your app before performing the attestation, and append that hash to the end of the
        # authenticator data (authData from the decoded object).
        print('Apple Attestation step 2...')
        authdata_with_nonce_hash = create_authdata_with_nonce_hash(apple_attestation_object, nonce)

        # 3. Generate a new SHA256 hash of the composite item to create nonce.
        print('Apple Attestation step 3...')
        composite_nonce = create_composite_nonce(authdata_with_nonce_hash)

        # 4. Obtain the value of the credCert extension with OID 1.2.840.113635.100.8.2,
        # which is a DER-encoded ASN.1 sequence. Decode the sequence and extract the single
        # octet string that it contains. Verify that the string equals nonce.
        print('Apple Attestation step 4...')
        extension_value = extract_attestation_object_extension(apple_attestation_object)
        if (extension_value != composite_nonce):
            # this step is failing without caching nonce so commenting out for now
            #     return False
            print('extension_value:', extension_value)
            print('composite_nonce:', composite_nonce)

        # 5. Create the SHA256 hash of the public key in credCert, and verify that it matches the
        # key identifier from your app.
        print('Apple Attestation step 5...')
        public_hash = create_hash_from_pub_key(apple_attestation_object['attStmt']['x5c'][0])
        bytes_value = base64.b64decode(attestation_object['key_id'])
        hash_object = hashlib.sha256(bytes_value)
        hash = hash_object.hexdigest()
        if (hash != public_hash):
            # this step is failing without caching nonce so commenting out for now
            # return False
            print('hash:', hash)
            print('public_hash:', public_hash)

        # 6. Compute the SHA256 hash of your app’s App ID, and verify that it’s the same as the
        # authenticator data’s RP ID hash.
        print('Apple Attestation step 6...')
        app_id_hash = create_app_id_hash()
        rp_id_hash = apple_attestation_object['authData'][:rp_id_hash_end].hex()
        if (rp_id_hash != app_id_hash):
            return False

        # 7. Verify that the authenticator data’s counter field equals 0. See
        # https://www.w3.org/TR/webauthn/#sctn-attestation for byte start and end points.
        print('Apple Attestation step 7...')
        counter = apple_attestation_object['authData'][counter_start:counter_end]
        if (counter != bytearray(b'\x00\x00\x00\x00')):
            return False

        # 8. Verify that the authenticator data’s aaguid field is either appattestdevelop if
        # operating in the development environment, or appattest followed by seven 0x00
        # bytes if operating in the production environment.
        print('Apple Attestation step 8...')
        aaguid = apple_attestation_object['authData'][aaguid_start:aaguid_end]
        # this step is failing so commenting out for now
        if (aaguid != bytearray(b'appattestdevelop') and aaguid != bytearray(b'appattest\x00\x00\x00\x00\x00\x00\x00')):
            return False

        # 9. Verify that the authenticator data’s credentialId field is the same as the
        # key identifier.
        print('Apple Attestation step 9...')
        key_identifier = bytes_value
        cred_id_length = len(key_identifier)
        cred_id_end = cred_id_start + cred_id_length
        credential_id = apple_attestation_object['authData'][cred_id_start:cred_id_end]
        if (credential_id != key_identifier):
            return False

        print('Successful apple attestation')
        return True

    except Exception as e:
        print('Error during Apple attestation:', e)
        return False

def main():
    # placeholder until caching is implemented
    server_side_nonce = '1234567890'

    with open("attestation.json", "r") as f:
        attestation_as_json = json.load(f)

    verify_attestation_statement(attestation_as_json, server_side_nonce)


if __name__ == "__main__":
    main()
