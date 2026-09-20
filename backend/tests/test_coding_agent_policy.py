import unittest

from services.coding_agent_policy import CodingPolicyError, validate_patch


class CodingAgentPolicyTests(unittest.TestCase):
    def test_allows_small_html_content_patch(self):
        result = validate_patch(
            """diff --git a/index.html b/index.html
--- a/index.html
+++ b/index.html
@@ -1 +1 @@
-<title>Old</title>
+<title>New SEO title</title>
"""
        )
        self.assertEqual(result["files"], ["index.html"])

    def test_rejects_javascript_file(self):
        with self.assertRaises(CodingPolicyError):
            validate_patch("--- a/app.js\n+++ b/app.js\n@@ -1 +1 @@\n-console.log(1)\n+console.log(2)\n")

    def test_rejects_script_in_html(self):
        with self.assertRaises(CodingPolicyError):
            validate_patch("--- a/index.html\n+++ b/index.html\n@@ -1 +1 @@\n+<script>alert(1)</script>\n")

    def test_allows_configured_homepage_path(self):
        result = validate_patch(
            "--- a/src/app/page.html\n+++ b/src/app/page.html\n@@ -1 +1 @@\n-<title>Old</title>\n+<title>New</title>\n",
            allowed_paths={"src/app/page.html"},
        )
        self.assertEqual(result["files"], ["src/app/page.html"])

    def test_rejects_non_homepage_path_in_test_mode(self):
        with self.assertRaises(CodingPolicyError):
            validate_patch(
                "--- a/blog/post.html\n+++ b/blog/post.html\n@@ -1 +1 @@\n-<title>Old</title>\n+<title>New</title>\n",
                allowed_paths={"src/app/page.html"},
            )


if __name__ == "__main__":
    unittest.main()
