"""Tests for certificate helpers (SAN normalization and PEM parsing)."""

from cryptography.x509.oid import ExtendedKeyUsageOID, ObjectIdentifier
from django.test import SimpleTestCase

from nautobot_ssl_manager import utils
from nautobot_ssl_manager.choices import ExtendedKeyUsageChoices, KeyAlgorithmChoices, ValidationLevelChoices
from nautobot_ssl_manager.tests import certificates


class NormalizeSanTest(SimpleTestCase):
    """Test SAN normalization."""

    def test_valid_entries(self):
        self.assertEqual(utils.normalize_san("WWW.Example.com"), "www.example.com")
        self.assertEqual(utils.normalize_san("*.example.com"), "*.example.com")
        self.assertEqual(utils.normalize_san("10.0.0.1"), "10.0.0.1")
        self.assertEqual(utils.normalize_san("2001:DB8::0001"), "2001:db8::1")
        self.assertEqual(utils.normalize_san("Email:admin@example.com"), "email:admin@example.com")
        self.assertEqual(utils.normalize_san("URI:https://example.com/x"), "uri:https://example.com/x")

    def test_invalid_entries(self):
        for value in ("not a name", "*.com", "www.*.example.com", "-bad.example.com", "email:nope", "uri:"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    utils.normalize_san(value)

    def test_list_deduplicates_and_skips_blank_lines(self):
        self.assertEqual(
            utils.normalize_san_list(["www.example.com", "", "  ", "WWW.example.com", "10.0.0.1"]),
            ["www.example.com", "10.0.0.1"],
        )

    def test_list_reports_all_invalid_entries(self):
        with self.assertRaises(ValueError) as context:
            utils.normalize_san_list(["bad one", "www.example.com", "bad two"])
        self.assertIn("bad one", str(context.exception))
        self.assertIn("bad two", str(context.exception))


class ParsePemTest(SimpleTestCase):
    """Test PEM parsing."""

    def test_parse_rsa_certificate(self):
        pem, certificate, _ = certificates.build_certificate(
            dns_names=("www.example.com", "*.example.com"),
            ip_addresses=("192.0.2.10",),
            emails=("admin@example.com",),
            uris=("https://example.com/id",),
            eku=(ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH),
            policies=(certificates.DV_POLICY,),
        )
        parsed = utils.parse_pem_certificate(pem)
        self.assertEqual(parsed.common_name, "www.example.com")
        self.assertEqual(parsed.issuer_common_name, "Test Issuing CA")
        self.assertEqual(
            parsed.subject_alternative_names,
            [
                "www.example.com",
                "*.example.com",
                "192.0.2.10",
                "email:admin@example.com",
                "uri:https://example.com/id",
            ],
        )
        self.assertEqual(parsed.serial_number, format(certificate.serial_number, "x"))
        self.assertEqual(parsed.fingerprint_sha256, certificates.fingerprint(certificate))
        self.assertEqual(parsed.not_after, certificate.not_valid_after_utc)
        self.assertEqual(parsed.key_algorithm, KeyAlgorithmChoices.RSA)
        self.assertEqual(parsed.key_size, 2048)
        self.assertEqual(
            parsed.extended_key_usage,
            [ExtendedKeyUsageChoices.SERVER_AUTH, ExtendedKeyUsageChoices.CLIENT_AUTH],
        )
        self.assertEqual(parsed.validation_level, ValidationLevelChoices.DV)
        self.assertEqual(parsed.warnings, [])

    def test_parse_ec_and_ed25519_keys(self):
        parsed = utils.parse_pem_certificate(certificates.build_certificate(key_type="ec")[0])
        self.assertEqual((parsed.key_algorithm, parsed.key_size), (KeyAlgorithmChoices.ECDSA, 256))
        parsed = utils.parse_pem_certificate(certificates.build_certificate(key_type="ed25519")[0])
        self.assertEqual((parsed.key_algorithm, parsed.key_size), (KeyAlgorithmChoices.ED25519, None))

    def test_no_policy_leaves_validation_level_empty(self):
        parsed = utils.parse_pem_certificate(certificates.build_certificate(policies=())[0])
        self.assertEqual(parsed.validation_level, "")

    def test_conflicting_policies_leave_validation_level_empty(self):
        pem = certificates.build_certificate(policies=(certificates.DV_POLICY, certificates.OV_POLICY))[0]
        parsed = utils.parse_pem_certificate(pem)
        self.assertEqual(parsed.validation_level, "")
        self.assertTrue(parsed.warnings)

    def test_unknown_eku_is_reported(self):
        pem = certificates.build_certificate(eku=(ExtendedKeyUsageOID.SERVER_AUTH, ObjectIdentifier("1.2.3.4")))[0]
        parsed = utils.parse_pem_certificate(pem)
        self.assertEqual(parsed.extended_key_usage, [ExtendedKeyUsageChoices.SERVER_AUTH])
        self.assertIn("1.2.3.4", parsed.warnings[0])

    def test_private_key_is_rejected(self):
        pem, _, private_key = certificates.build_certificate()
        with self.assertRaisesRegex(utils.CertificateParseError, "private key"):
            utils.parse_pem_certificate(pem + certificates.private_key_pem(private_key))

    def test_invalid_pem(self):
        for value in ("", "not a certificate", "-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----"):
            with self.subTest(value=value):
                with self.assertRaises(utils.CertificateParseError):
                    utils.parse_pem_certificate(value)

    def test_bundle_with_one_leaf_selects_the_leaf(self):
        leaf_pem, leaf, _ = certificates.build_certificate(common_name="leaf.example.com")
        ca_pem = certificates.build_certificate(common_name="Intermediate CA", dns_names=(), eku=(), is_ca=True)[0]
        parsed = utils.parse_pem_certificate(ca_pem + leaf_pem)
        self.assertEqual(parsed.common_name, "leaf.example.com")
        self.assertEqual(parsed.fingerprint_sha256, certificates.fingerprint(leaf))
        self.assertEqual(parsed.pem, leaf_pem)

    def test_bundle_with_several_leaves_is_rejected(self):
        first = certificates.build_certificate(common_name="one.example.com")[0]
        second = certificates.build_certificate(common_name="two.example.com")[0]
        with self.assertRaisesRegex(utils.CertificateParseError, "several certificates"):
            utils.parse_pem_certificate(first + second)
