"""Build downloadable files from the public certificates stored in Nautobot (never any private key).

Formats:

- `pem`: PEM text; with the chain, a bundle ordered from the certificate up to its issuers;
- `der`: DER binary, a single certificate only;
- `p7b`: PKCS#7 (DER encoded, certificates only), with or without the chain. PKCS#7 stores certificates in a set:
  their order in the file is not significant.

The chain is built from the Certificate Authority tree (issuing CA, then its issuers) using the CA certificate linked
to each CA. Only facts are used: if a CA certificate is missing, not visible to the user, or does not match its
issuer, the download fails explicitly instead of returning an incomplete or wrong bundle.
"""

import re
from dataclasses import dataclass

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from django.http import HttpResponse

from nautobot_ssl_manager import models

FORMAT_PEM = "pem"
FORMAT_DER = "der"
FORMAT_P7B = "p7b"
FORMATS = (FORMAT_PEM, FORMAT_DER, FORMAT_P7B)

CONTENT_TYPES = {
    FORMAT_PEM: "application/x-pem-file",
    FORMAT_DER: "application/pkix-cert",
    FORMAT_P7B: "application/x-pkcs7-certificates",
}

TRUE_VALUES = ("1", "true", "yes", "on")


class CertificateDownloadError(Exception):
    """The requested file cannot be built from the data stored in Nautobot."""


class CertificateDownloadPermissionError(CertificateDownloadError):
    """The user is not allowed to view a Certificate Authority or certificate of the chain."""


@dataclass
class CertificateDownload:
    """A file ready to be served."""

    content: bytes
    filename: str
    content_type: str


def parse_bool(value):
    """Parse a boolean query parameter (missing means False)."""
    return str(value).strip().lower() in TRUE_VALUES if value is not None else False


def safe_filename_base(certificate):
    """File name base from the Common Name (or the name): wildcard replaced, path separators and specials removed."""
    value = (certificate.common_name or certificate.name or "").strip().replace("*", "wildcard")
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return value or "certificate"


def _load(certificate):
    """Load the stored PEM of a Certificate as an x509 object."""
    try:
        return x509.load_pem_x509_certificate(certificate.pem.encode())
    except ValueError as exc:
        raise CertificateDownloadError(f"The PEM of {certificate} is invalid: {exc}") from exc


def _is_self_signed(loaded):
    return loaded.issuer == loaded.subject


def _visible(queryset, user):
    return queryset.restrict(user, "view") if user is not None else queryset


def _chain_certificates(certificate, user):
    """CA certificates of the chain of `certificate`, from its issuing CA up to the top of the CA tree."""
    authorities = certificate.chain
    if not authorities:
        raise CertificateDownloadError("No Certificate Authority is set on this certificate: the chain is unknown.")

    if user is not None and not user.has_perm("nautobot_ssl_manager.view_certificateauthority"):
        raise CertificateDownloadPermissionError("Viewing Certificate Authorities is required to download the chain.")
    visible_authorities = set(
        _visible(models.CertificateAuthority.objects.all(), user)
        .filter(pk__in=[authority.pk for authority in authorities])
        .values_list("pk", flat=True)
    )
    if len(visible_authorities) != len(authorities):
        raise CertificateDownloadPermissionError("Some Certificate Authorities of the chain are not visible to you.")

    missing = [str(authority) for authority in authorities if not authority.certificate_id]
    without_pem = [
        str(authority) for authority in authorities if authority.certificate_id and not authority.certificate.pem
    ]
    if missing or without_pem:
        details = []
        if missing:
            details.append(f"no CA certificate linked: {', '.join(missing)}")
        if without_pem:
            details.append(f"CA certificate without PEM: {', '.join(without_pem)}")
        raise CertificateDownloadError(f"The chain is incomplete ({'; '.join(details)}).")

    ca_certificates = [authority.certificate for authority in authorities]
    visible_certificates = set(
        _visible(models.Certificate.objects.all(), user)
        .filter(pk__in=[ca_certificate.pk for ca_certificate in ca_certificates])
        .values_list("pk", flat=True)
    )
    if len(visible_certificates) != len({ca_certificate.pk for ca_certificate in ca_certificates}):
        raise CertificateDownloadPermissionError("Some CA certificates of the chain are not visible to you.")
    return ca_certificates


def build_bundle(certificate, chain=False, include_root=False, user=None):
    """Return the x509 certificates to serve: the certificate, then (with `chain`) its issuers.

    Self-signed CA certificates (Root CAs) are only included with `include_root`. Each certificate must be issued by
    the next one (issuer name = subject name of the next certificate).
    """
    if not certificate.pem:
        raise CertificateDownloadError("No PEM is stored for this certificate.")
    bundle = [_load(certificate)]
    if not chain:
        return bundle

    leaf_fingerprint = bundle[0].fingerprint(hashes.SHA256())
    for ca_certificate in _chain_certificates(certificate, user):
        loaded = _load(ca_certificate)
        if loaded.fingerprint(hashes.SHA256()) == leaf_fingerprint:
            continue  # The certificate is itself the certificate of its CA (self-signed Root CA certificate).
        if bundle[-1].issuer != loaded.subject:
            raise CertificateDownloadError(
                f"The chain is inconsistent: {bundle[-1].subject.rfc4514_string()} is issued by "
                f"{bundle[-1].issuer.rfc4514_string()}, but the certificate of the next CA ({ca_certificate}) is "
                f"{loaded.subject.rfc4514_string()}."
            )
        bundle.append(loaded)

    if not include_root:
        bundle = [bundle[0], *(loaded for loaded in bundle[1:] if not _is_self_signed(loaded))]
    return bundle


def build_download(certificate, file_format=FORMAT_PEM, chain=False, include_root=False, user=None):
    """Build the file to download for `certificate`."""
    file_format = (file_format or FORMAT_PEM).lower()
    if file_format not in FORMATS:
        raise CertificateDownloadError(f"Unsupported format '{file_format}': expected one of {', '.join(FORMATS)}.")
    if file_format == FORMAT_DER and chain:
        raise CertificateDownloadError("The DER format holds a single certificate: use PEM or PKCS#7 for the chain.")

    bundle = build_bundle(certificate, chain=chain, include_root=include_root, user=user)
    if file_format == FORMAT_PEM:
        content = b"".join(loaded.public_bytes(serialization.Encoding.PEM) for loaded in bundle)
    elif file_format == FORMAT_DER:
        content = bundle[0].public_bytes(serialization.Encoding.DER)
    else:
        content = pkcs7.serialize_certificates(bundle, serialization.Encoding.DER)

    suffix = ""
    if chain:
        suffix = "-chain-with-root" if include_root else "-chain"
    return CertificateDownload(
        content=content,
        filename=f"{safe_filename_base(certificate)}{suffix}.{file_format}",
        content_type=CONTENT_TYPES[file_format],
    )


def chain_unavailable_reason(certificate):
    """Why the chain cannot be downloaded (None when it can), without permission checks. Used to disable buttons."""
    if not certificate.pem:
        return "No PEM is stored for this certificate."
    try:
        build_bundle(certificate, chain=True, include_root=True)
    except CertificateDownloadError as exc:
        return str(exc)
    return None


def download_response(download):
    """Django response serving the file as an attachment."""
    response = HttpResponse(download.content, content_type=download.content_type)
    response["Content-Disposition"] = f'attachment; filename="{download.filename}"'
    return response
