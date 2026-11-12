"""Tests for the import of a PEM bundle (full chain) with a review page."""

from django.urls import reverse
from nautobot.apps.testing import TestCase
from nautobot.extras.models import ObjectChange

from nautobot_ssl_manager import bundles, forms, models, utils
from nautobot_ssl_manager.choices import CertificateAuthorityTypeChoices
from nautobot_ssl_manager.tests import certificates, fixtures
from nautobot_ssl_manager.tests.test_ca_certificate import create_certificate


class BundleTestCase(TestCase):
    """Base test case: a real chain Bundle Root CA -> Bundle Issuing CA -> www.bundle.example.com."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.root_pem, cls.intermediate_pem, cls.leaf_pem = certificates.build_chain()
        cls.ca_status = fixtures.get_certificate_authority_statuses()[0]
        cls.certificate_status = fixtures.get_certificate_statuses()[1]

    def create_root_ca(self, link_certificate=True):
        """Create the Root CA in Nautobot, optionally linked to its certificate."""
        root = models.CertificateAuthority.objects.create(
            name="Bundle Root CA", type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=self.ca_status
        )
        if link_certificate:
            root.certificate = create_certificate("Bundle Root CA", pem=self.root_pem, certificate_authority=root)
            root.validated_save()
        return root

    def selection(self, entry, **overrides):
        """Values of a selected entry, as cleaned by the review form."""
        values = {"selected": True, "tenant": None}
        if entry.action == bundles.ACTION_CREATE_CA:
            values.update(
                ca_name=bundles.default_authority_name(entry.parsed),
                ca_type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
                ca_status=self.ca_status,
                provider=None,
            )
        if entry.creates_certificate:
            values.update(name=bundles.default_certificate_name(entry.parsed), status=self.certificate_status)
        values.update(overrides)
        return values

    def form_data(self, plan, pem, **overrides):
        """POST data of the review form selecting every actionable entry."""
        data = {"pem": pem}
        for entry in plan.actionable_entries:
            for name, value in self.selection(entry).items():
                if value is None:
                    continue
                data[f"{entry.prefix}-{name}"] = value.pk if hasattr(value, "pk") else value
        data.update(overrides)
        return data


class ParseBundleTest(BundleTestCase):
    """Parsing and signature helpers."""

    def test_parse_bundle_keeps_order_and_removes_duplicates(self):
        parsed = utils.parse_pem_bundle(self.leaf_pem + self.root_pem + self.leaf_pem)
        self.assertEqual([entry.common_name for entry in parsed], ["www.bundle.example.com", "Bundle Root CA"])

    def test_private_key_rejected(self):
        _, _, key = certificates.build_certificate()
        with self.assertRaises(utils.CertificateParseError):
            utils.parse_pem_bundle(self.leaf_pem + certificates.private_key_pem(key))

    def test_signature_verification(self):
        bundle = utils.parse_pem_bundle(self.root_pem + self.intermediate_pem + self.leaf_pem)
        root, intermediate, leaf = bundle[0], bundle[1], bundle[2]
        self.assertTrue(utils.is_issued_by(leaf.certificate, intermediate.certificate))
        self.assertTrue(utils.is_issued_by(intermediate.certificate, root.certificate))
        self.assertFalse(utils.is_issued_by(leaf.certificate, root.certificate))
        self.assertTrue(root.is_self_signed)
        self.assertFalse(intermediate.is_self_signed)
        # Same names, different key: the signature is not verified.
        fake_root = utils.parse_pem_certificate(
            certificates.build_certificate(
                common_name="Bundle Root CA", issuer_common_name="Bundle Root CA", is_ca=True, dns_names=()
            )[0]
        )
        self.assertFalse(utils.is_issued_by(intermediate.certificate, fake_root.certificate))


class BundlePlanTest(BundleTestCase):
    """Analysis of the bundle."""

    def test_order_by_signature_not_by_file(self):
        plan = bundles.BundlePlan.from_pem(self.leaf_pem + self.root_pem + self.intermediate_pem)
        self.assertEqual(
            [(entry.parsed.common_name, entry.role, entry.action) for entry in plan.entries],
            [
                ("Bundle Root CA", bundles.ROLE_ROOT, bundles.ACTION_CREATE_CA),
                ("Bundle Issuing CA", bundles.ROLE_INTERMEDIATE, bundles.ACTION_CREATE_CA),
                ("www.bundle.example.com", bundles.ROLE_CERTIFICATE, bundles.ACTION_CREATE_CERTIFICATE),
            ],
        )
        root, intermediate, leaf = plan.entries
        self.assertTrue(root.self_signed)
        self.assertIs(intermediate.issuer_entry, root)
        self.assertIs(leaf.issuer_entry, intermediate)
        self.assertEqual(leaf.issuer_label, "Bundle Issuing CA (in this bundle)")

    def test_existing_root_ca_is_detected(self):
        root_ca = self.create_root_ca()
        plan = bundles.BundlePlan.from_pem(self.root_pem + self.intermediate_pem)
        root, intermediate = plan.entries
        self.assertEqual(root.action, bundles.ACTION_NONE)
        self.assertEqual(root.existing_authority, root_ca)
        self.assertIn("CA certificate of Bundle Root CA", root.finding)
        self.assertEqual(intermediate.action, bundles.ACTION_CREATE_CA)

    def test_issuer_proven_in_nautobot(self):
        root_ca = self.create_root_ca()
        plan = bundles.BundlePlan.from_pem(self.intermediate_pem + self.leaf_pem)
        intermediate = plan.entries[0]
        self.assertIsNone(intermediate.issuer_entry)
        self.assertEqual(intermediate.issuer_authority, root_ca)
        self.assertEqual(intermediate.issuer_label, "Bundle Root CA (in Nautobot)")

    def test_issuer_with_same_name_but_another_key_is_not_used(self):
        root_ca = self.create_root_ca(link_certificate=False)
        root_ca.certificate = create_certificate(
            "Other Bundle Root CA",
            pem=certificates.build_certificate(
                common_name="Bundle Root CA", issuer_common_name="Bundle Root CA", is_ca=True, dns_names=()
            )[0],
            certificate_authority=root_ca,
        )
        root_ca.validated_save()
        intermediate = bundles.BundlePlan.from_pem(self.intermediate_pem).entries[0]
        self.assertIsNone(intermediate.issuer_authority)
        self.assertIn("Issuer not found", " ".join(intermediate.notes))

    def test_named_ca_without_certificate_is_linked(self):
        self.create_root_ca(link_certificate=False)
        root = bundles.BundlePlan.from_pem(self.root_pem + self.leaf_pem).entries[0]
        self.assertEqual(root.action, bundles.ACTION_LINK_CA)
        self.assertIn("existing CA Bundle Root CA (same name)", root.action_label)

    def test_named_ca_with_another_certificate(self):
        root_ca = self.create_root_ca(link_certificate=False)
        root_ca.certificate = create_certificate("Previous root certificate")
        root_ca.validated_save()
        root = bundles.BundlePlan.from_pem(self.root_pem + self.leaf_pem).entries[0]
        self.assertEqual(root.action, bundles.ACTION_CREATE_CERTIFICATE)
        self.assertIn("link it manually", " ".join(root.notes))

    def test_permissions(self):
        self.add_permissions("nautobot_ssl_manager.add_certificate")
        plan = bundles.BundlePlan.from_pem(self.root_pem + self.leaf_pem, user=self.user)
        root, leaf = plan.entries
        self.assertIn("add Certificate Authorities", root.disabled_reason)
        self.assertEqual(leaf.disabled_reason, "")


class ApplyPlanTest(BundleTestCase):
    """Creation of the selected objects."""

    def _apply(self, plan, skip=()):
        selections = {
            entry.index: self.selection(entry) for entry in plan.actionable_entries if entry.index not in skip
        }
        return bundles.apply_plan(plan, selections)

    def test_full_chain(self):
        plan = bundles.BundlePlan.from_pem(self.leaf_pem + self.intermediate_pem + self.root_pem)
        changed = self._apply(plan)
        self.assertEqual(len(changed), 5)
        root = models.CertificateAuthority.objects.get(name="Bundle Root CA")
        intermediate = models.CertificateAuthority.objects.get(name="Bundle Issuing CA")
        leaf = models.Certificate.objects.get(common_name="www.bundle.example.com")
        self.assertIsNone(root.parent)
        self.assertEqual(root.certificate.certificate_authority, root)
        self.assertEqual(intermediate.parent, root)
        self.assertEqual(intermediate.certificate.certificate_authority, root)
        self.assertEqual(leaf.certificate_authority, intermediate)
        self.assertEqual(leaf.pem, utils.parse_pem_certificate(self.leaf_pem).pem)
        self.assertEqual(leaf.status, self.certificate_status)
        self.assertEqual(intermediate.type, CertificateAuthorityTypeChoices.TYPE_PRIVATE)

    def test_under_existing_root(self):
        root_ca = self.create_root_ca()
        plan = bundles.BundlePlan.from_pem(self.root_pem + self.intermediate_pem + self.leaf_pem)
        self._apply(plan)
        intermediate = models.CertificateAuthority.objects.get(name="Bundle Issuing CA")
        self.assertEqual(intermediate.parent, root_ca)
        self.assertEqual(models.CertificateAuthority.objects.filter(name="Bundle Root CA").count(), 1)

    def test_link_existing_ca_sets_its_issuer(self):
        root_ca = self.create_root_ca()
        intermediate_ca = models.CertificateAuthority.objects.create(
            name="Bundle Issuing CA", type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=self.ca_status
        )
        plan = bundles.BundlePlan.from_pem(self.intermediate_pem)
        self._apply(plan)
        intermediate_ca.refresh_from_db()
        self.assertEqual(intermediate_ca.parent, root_ca)
        self.assertEqual(intermediate_ca.certificate.common_name, "Bundle Issuing CA")

    def test_unselected_root(self):
        plan = bundles.BundlePlan.from_pem(self.root_pem + self.intermediate_pem + self.leaf_pem)
        self._apply(plan, skip=(plan.entries[0].index,))
        self.assertFalse(models.CertificateAuthority.objects.filter(name="Bundle Root CA").exists())
        intermediate = models.CertificateAuthority.objects.get(name="Bundle Issuing CA")
        self.assertIsNone(intermediate.parent)
        self.assertIsNone(intermediate.certificate.certificate_authority)
        self.assertEqual(
            models.Certificate.objects.get(common_name="www.bundle.example.com").certificate_authority, intermediate
        )

    def test_all_or_nothing(self):
        models.CertificateAuthority.objects.create(
            name="Already used", type=CertificateAuthorityTypeChoices.TYPE_PRIVATE, status=self.ca_status
        )
        plan = bundles.BundlePlan.from_pem(self.root_pem + self.intermediate_pem + self.leaf_pem)
        root, intermediate, _ = plan.entries
        selections = {entry.index: self.selection(entry) for entry in plan.entries}
        selections[intermediate.index]["ca_name"] = "Already used"
        with self.assertRaisesMessage(bundles.BundleImportError, "Bundle Issuing CA"):
            bundles.apply_plan(plan, selections)
        self.assertFalse(models.CertificateAuthority.objects.filter(name=root.parsed.common_name).exists())
        self.assertFalse(models.Certificate.objects.filter(common_name__startswith="Bundle").exists())


class BundleReviewFormTest(BundleTestCase):
    """Review form."""

    def test_selected_entries_require_values(self):
        plan = bundles.BundlePlan.from_pem(self.root_pem + self.leaf_pem)
        root, leaf = plan.entries
        data = self.form_data(plan, "pem", **{f"{root.prefix}-ca_type": "", f"{leaf.prefix}-status": ""})
        form = forms.CertificateImportBundleForm(data, plan=plan)
        self.assertFalse(form.is_valid())
        self.assertIn(f"{root.prefix}-ca_type", form.errors)
        self.assertIn(f"{leaf.prefix}-status", form.errors)

    def test_unselected_entries_are_ignored(self):
        plan = bundles.BundlePlan.from_pem(self.root_pem + self.leaf_pem)
        root, leaf = plan.entries
        data = {"pem": "pem", f"{leaf.prefix}-selected": "on", f"{leaf.prefix}-name": "leaf"}
        data[f"{leaf.prefix}-status"] = self.certificate_status.pk
        form = forms.CertificateImportBundleForm(data, plan=plan)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(list(form.selections), [leaf.index])
        self.assertNotIn(root.index, form.selections)

    def test_nothing_selected(self):
        plan = bundles.BundlePlan.from_pem(self.root_pem + self.leaf_pem)
        form = forms.CertificateImportBundleForm({"pem": "pem"}, plan=plan)
        self.assertFalse(form.is_valid())
        self.assertIn("Select at least one action.", form.non_field_errors())

    def test_no_value_is_guessed(self):
        plan = bundles.BundlePlan.from_pem(self.root_pem + self.leaf_pem)
        root, leaf = plan.entries
        form = forms.CertificateImportBundleForm(plan=plan)
        self.assertEqual(form.fields[f"{root.prefix}-ca_name"].initial, "Bundle Root CA")
        for name in ("ca_type", "ca_status", "provider", "tenant"):
            self.assertIsNone(form.fields[f"{root.prefix}-{name}"].initial)
        self.assertIsNone(form.fields[f"{leaf.prefix}-status"].initial)


class BundleImportViewTest(BundleTestCase):
    """Import page, review page and confirmation."""

    user_permissions = [
        "nautobot_ssl_manager.add_certificate",
        "nautobot_ssl_manager.view_certificate",
        "nautobot_ssl_manager.add_certificateauthority",
        "nautobot_ssl_manager.change_certificateauthority",
        "nautobot_ssl_manager.view_certificateauthority",
    ]

    def setUp(self):
        super().setUp()
        self.import_url = reverse("plugins:nautobot_ssl_manager:certificate_import_pem")
        self.confirm_url = reverse("plugins:nautobot_ssl_manager:certificate_import_bundle")

    def test_bundle_shows_review_page(self):
        response = self.client.post(self.import_url, {"pem": self.leaf_pem + self.intermediate_pem + self.root_pem})
        self.assertHttpStatus(response, 200)
        content = response.content.decode()
        self.assertIn("Review the PEM bundle", content)
        self.assertIn("Create the Certificate Authority and create its certificate", content)
        self.assertLess(content.index("Bundle Root CA"), content.index("www.bundle.example.com"))
        self.assertFalse(models.Certificate.objects.filter(common_name="www.bundle.example.com").exists())

    def test_all_certificates_exist(self):
        create_certificate("Root", pem=self.root_pem)
        create_certificate("Leaf", pem=self.leaf_pem)
        response = self.client.post(self.import_url, {"pem": self.root_pem + self.leaf_pem})
        self.assertIn("All the certificates of this bundle already exist", response.content.decode())

    def test_confirm_creates_objects_with_change_logging(self):
        pem = self.root_pem + self.intermediate_pem + self.leaf_pem
        plan = bundles.BundlePlan.from_pem(pem)
        response = self.client.post(self.confirm_url, self.form_data(plan, pem))
        leaf = models.Certificate.objects.get(common_name="www.bundle.example.com")
        self.assertRedirects(response, leaf.get_absolute_url(), fetch_redirect_response=False)
        self.assertEqual(leaf.certificate_authority.name, "Bundle Issuing CA")
        self.assertTrue(ObjectChange.objects.filter(changed_object_id=leaf.pk).exists())
        self.assertTrue(
            ObjectChange.objects.filter(changed_object_id=leaf.certificate_authority.pk, user=self.user).exists()
        )
        content = self.client.get(leaf.get_absolute_url()).content.decode()
        self.assertIn("Bundle imported", content)

    def test_confirm_with_errors_shows_review_page(self):
        pem = self.root_pem + self.leaf_pem
        plan = bundles.BundlePlan.from_pem(pem)
        data = self.form_data(plan, pem, **{f"{plan.entries[1].prefix}-status": ""})
        response = self.client.post(self.confirm_url, data)
        self.assertHttpStatus(response, 200)
        self.assertIn("This field is required for the selected action.", response.content.decode())
        self.assertFalse(models.Certificate.objects.filter(common_name="www.bundle.example.com").exists())

    def test_confirm_requires_add_certificate(self):
        self.remove_permissions("nautobot_ssl_manager.add_certificate")
        self.assertHttpStatus(self.client.post(self.confirm_url, {"pem": self.leaf_pem}), 403)

    def test_disabled_action_without_ca_permission(self):
        self.remove_permissions("nautobot_ssl_manager.add_certificateauthority")
        response = self.client.post(self.import_url, {"pem": self.root_pem + self.leaf_pem})
        self.assertIn("You are not allowed to add Certificate Authorities.", response.content.decode())

    def test_single_certificate_with_unknown_issuer(self):
        response = self.client.post(self.import_url, {"pem": self.leaf_pem}, follow=True)
        content = response.content.decode()
        self.assertIn("The issuer of this certificate (Bundle Issuing CA) is not in Nautobot", content)
        self.assertIn(
            reverse("plugins:nautobot_ssl_manager:certificateauthority_add") + "?name=Bundle+Issuing+CA", content
        )

    def test_single_certificate_with_known_issuer(self):
        root_ca = self.create_root_ca()
        intermediate_ca = models.CertificateAuthority.objects.create(
            name="Intermediate with another name",
            type=CertificateAuthorityTypeChoices.TYPE_PRIVATE,
            status=self.ca_status,
            parent=root_ca,
        )
        intermediate_ca.certificate = create_certificate(
            "Bundle Issuing CA", pem=self.intermediate_pem, certificate_authority=root_ca
        )
        intermediate_ca.validated_save()
        response = self.client.post(self.import_url, {"pem": self.leaf_pem}, follow=True)
        self.assertNotIn("is not in Nautobot", response.content.decode())

    def test_ca_add_form_prefilled_from_hint(self):
        url = reverse("plugins:nautobot_ssl_manager:certificateauthority_add") + "?name=Bundle+Issuing+CA"
        response = self.client.get(url)
        self.assertEqual(response.context["form"].initial.get("name"), "Bundle Issuing CA")
