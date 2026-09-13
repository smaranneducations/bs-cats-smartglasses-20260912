import copy
import io
import unittest

from PIL import Image

from packages.media.commons_context import allowed_url, inspect_bytes, plain, validate_metadata


def page():
    return {"pageid": 123, "lastrevid": 456, "title": "File:Context.jpg", "imageinfo": [{
        "thumburl": "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Context.jpg/1920px-Context.jpg",
        "thumbwidth": 1920, "thumbheight": 1080, "extmetadata": {
            "Artist": {"value": '<a href="/wiki/User:Creator">Creator</a>'},
            "Credit": {"value": '<span class="int-own-work">Own work</span>'},
            "LicenseShortName": {"value": "CC0"},
            "LicenseUrl": {"value": "http://creativecommons.org/publicdomain/zero/1.0/deed.en"},
            "Copyrighted": {"value": "True"}, "Restrictions": {"value": ""}}}]}


class CommonsContextTests(unittest.TestCase):
    def test_explicit_cc0_is_distinct_from_copyrighted_flag(self):
        self.assertEqual(validate_metadata(page())["license"], "CC0-1.0")

    def test_creator_html_is_text_not_executable_markup(self):
        self.assertEqual(validate_metadata(page())["creator"], "Creator")
        self.assertEqual(plain("Photo &amp; light"), "Photo & light")

    def test_site_footer_cc0_does_not_override_file_license(self):
        item = page()
        item["imageinfo"][0]["extmetadata"]["LicenseShortName"]["value"] = "CC BY-SA 4.0"
        with self.assertRaises(ValueError):
            validate_metadata(item)

    def test_unknown_creator_origin_requires_more_evidence(self):
        item = page()
        item["imageinfo"][0]["extmetadata"]["Credit"]["value"] = "Found online"
        with self.assertRaises(ValueError):
            validate_metadata(item)

    def test_additional_restrictions_are_not_ignored(self):
        item = page()
        item["imageinfo"][0]["extmetadata"]["Restrictions"]["value"] = "personality rights"
        with self.assertRaises(ValueError):
            validate_metadata(item)

    def test_unknown_or_private_image_host_is_rejected(self):
        for url in ("http://127.0.0.1/a.jpg", "https://example.com/a.jpg", "https://thumb.wikimedia.org.evil.example/a.jpg"):
            with self.assertRaises(ValueError):
                allowed_url(url, image=True)

    def test_userinfo_and_fragments_are_rejected(self):
        for url in ("https://user:password@thumb.wikimedia.org/wikipedia/commons/a.jpg", "https://thumb.wikimedia.org/wikipedia/commons/a.jpg#fragment"):
            with self.assertRaises(ValueError):
                allowed_url(url, image=True)

    def test_metadata_bounds_precede_download(self):
        item = page()
        item["imageinfo"][0]["thumbheight"] = 10000
        with self.assertRaises(ValueError):
            validate_metadata(item)

    def test_revision_is_required_for_provenance(self):
        item = page()
        del item["lastrevid"]
        with self.assertRaises(ValueError):
            validate_metadata(item)

    def test_jpeg_pixels_must_match_metadata(self):
        data = io.BytesIO()
        Image.new("RGB", (1920, 1080), "blue").save(data, format="JPEG")
        inspect_bytes(data.getvalue(), 1920, 1080)
        with self.assertRaises(ValueError):
            inspect_bytes(data.getvalue(), 1280, 720)

    def test_non_jpeg_content_is_not_accepted(self):
        data = io.BytesIO()
        Image.new("RGB", (1920, 1080), "blue").save(data, format="PNG")
        with self.assertRaises(ValueError):
            inspect_bytes(data.getvalue(), 1920, 1080)
