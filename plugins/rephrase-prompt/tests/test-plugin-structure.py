#!/usr/bin/env python3
"""Tests for rephrase-prompt plugin structure and configuration.
Run: python3 test-plugin-structure.py
"""

import json
import os
import stat
import unittest

PLUGIN_ROOT = os.path.join(os.path.dirname(__file__), "..")
CACHE_ROOT = os.path.expanduser(
    "~/.claude/plugins/cache/patrick-plugins/rephrase-prompt/0.1.0"
)
SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
INSTALLED_PATH = os.path.expanduser("~/.claude/plugins/installed_plugins.json")
CLAUDE_MD_PATH = os.path.expanduser("~/.claude/CLAUDE.md")


class TestPluginManifest(unittest.TestCase):
    def test_plugin_json_exists(self):
        path = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        self.assertTrue(os.path.exists(path))

    def test_plugin_json_valid(self):
        path = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["name"], "rephrase-prompt")
        self.assertEqual(data["version"], "0.1.0")
        self.assertIn("description", data)
        self.assertIn("author", data)

    def test_plugin_name_kebab_case(self):
        path = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        with open(path) as f:
            data = json.load(f)
        name = data["name"]
        self.assertRegex(name, r"^[a-z][a-z0-9-]*$", "Name must be kebab-case")


class TestHooksJson(unittest.TestCase):
    def setUp(self):
        path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
        with open(path) as f:
            self.hooks = json.load(f)

    def test_has_user_prompt_submit(self):
        self.assertIn("UserPromptSubmit", self.hooks)
        cmd = self.hooks["UserPromptSubmit"][0]["hooks"][0]["command"]
        self.assertIn("Invoke /rephrase", cmd)

    def test_has_pre_tool_use_verifier(self):
        self.assertIn("PreToolUse", self.hooks)
        cmd = self.hooks["PreToolUse"][0]["hooks"][0]["command"]
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", cmd, "Must use portable path variable")
        self.assertIn("verify-rephrase.py", cmd)

    def test_has_post_tool_use_reminder(self):
        self.assertIn("PostToolUse", self.hooks)
        entry = self.hooks["PostToolUse"][0]
        self.assertEqual(entry["matcher"], "AskUserQuestion|EnterPlanMode")
        self.assertIn("Invoke /rephrase", entry["hooks"][0]["command"])

    def test_has_post_tool_use_failure_reminder(self):
        self.assertIn("PostToolUseFailure", self.hooks)
        entry = self.hooks["PostToolUseFailure"][0]
        self.assertEqual(entry["matcher"], "ExitPlanMode")
        self.assertIn("Invoke /rephrase", entry["hooks"][0]["command"])

    def test_all_timeouts_set(self):
        for event, entries in self.hooks.items():
            for entry in entries:
                for hook in entry["hooks"]:
                    self.assertIn("timeout", hook, f"Missing timeout in {event}")
                    self.assertGreater(hook["timeout"], 0)

    def test_no_hardcoded_paths(self):
        """No absolute paths should appear in hooks.json (except ${CLAUDE_PLUGIN_ROOT})."""
        raw = json.dumps(self.hooks)
        self.assertNotIn("/home/", raw, "No hardcoded home paths allowed")
        self.assertNotIn("~/.claude", raw, "No tilde paths allowed")


class TestVerifyScript(unittest.TestCase):
    def test_script_exists(self):
        path = os.path.join(PLUGIN_ROOT, "hooks", "scripts", "verify-rephrase.py")
        self.assertTrue(os.path.exists(path))

    def test_script_executable(self):
        path = os.path.join(PLUGIN_ROOT, "hooks", "scripts", "verify-rephrase.py")
        mode = os.stat(path).st_mode
        self.assertTrue(mode & stat.S_IXUSR, "Script must be user-executable")

    def test_script_has_shebang(self):
        path = os.path.join(PLUGIN_ROOT, "hooks", "scripts", "verify-rephrase.py")
        with open(path) as f:
            first_line = f.readline()
        self.assertTrue(first_line.startswith("#!/"), "Must have shebang line")


class TestSkill(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(PLUGIN_ROOT, "skills", "rephrase", "SKILL.md")

    def test_skill_exists(self):
        self.assertTrue(os.path.exists(self.path))

    def test_skill_frontmatter(self):
        with open(self.path) as f:
            content = f.read()
        # Extract YAML frontmatter between --- markers
        parts = content.split("---", 2)
        self.assertGreaterEqual(len(parts), 3, "Must have YAML frontmatter")
        fm_text = parts[1]
        self.assertIn("name: rephrase", fm_text)
        self.assertIn("user-invocable: false", fm_text)
        self.assertIn("description:", fm_text)

    def test_skill_contains_format_rules(self):
        with open(self.path) as f:
            content = f.read()
        self.assertIn("Rephrase: ", content)
        self.assertIn('Use "I" to refer to the user', content)
        self.assertIn("never prefix your own analysis", content)

    def test_skill_has_examples(self):
        with open(self.path) as f:
            content = f.read()
        self.assertIn("## Example", content)
        self.assertIn("make the button bigger", content)


class TestRegistration(unittest.TestCase):
    def test_installed_plugins_entry(self):
        with open(INSTALLED_PATH) as f:
            data = json.load(f)
        self.assertIn("rephrase-prompt@patrick-plugins", data["plugins"])
        entry = data["plugins"]["rephrase-prompt@patrick-plugins"][0]
        self.assertEqual(entry["scope"], "user")
        self.assertEqual(entry["version"], "0.1.0")
        self.assertTrue(
            os.path.isdir(entry["installPath"]),
            f"Install path must exist: {entry['installPath']}",
        )

    def test_enabled_in_settings(self):
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
        self.assertIn("enabledPlugins", data)
        self.assertTrue(
            data["enabledPlugins"].get("rephrase-prompt@patrick-plugins"),
            "Plugin must be enabled",
        )


class TestCleanup(unittest.TestCase):
    def test_old_skill_removed(self):
        old_skill = os.path.expanduser("~/.claude/skills/rephrase/SKILL.md")
        self.assertFalse(os.path.exists(old_skill), "Old skill should be removed")

    def test_old_hook_script_removed(self):
        old_hook = os.path.expanduser("~/.claude/hooks/verify-rephrase.py")
        self.assertFalse(os.path.exists(old_hook), "Old hook script should be removed")

    def test_settings_no_rephrase_hooks(self):
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
        hooks_str = json.dumps(data.get("hooks", {}))
        self.assertNotIn("verify-rephrase", hooks_str, "No verify-rephrase in settings hooks")
        self.assertNotIn("Invoke /rephrase", hooks_str, "No rephrase reminders in settings hooks")

    def test_claude_md_references_plugin(self):
        with open(CLAUDE_MD_PATH) as f:
            content = f.read()
        self.assertIn("rephrase-prompt", content)
        self.assertNotIn("~/.claude/skills/rephrase", content, "Should not reference old path")


class TestCacheSync(unittest.TestCase):
    def _collect_files(self, root_dir, skip_dirs=None):
        """Collect relative file paths, including hidden directories."""
        skip_dirs = skip_dirs or set()
        result = set()
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Filter out skipped dirs
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for f in filenames:
                rel = os.path.relpath(os.path.join(dirpath, f), root_dir)
                result.add(rel)
        return result

    def test_cache_matches_marketplace(self):
        """Cache copy should have the same core files as marketplace source."""
        marketplace_files = self._collect_files(PLUGIN_ROOT, skip_dirs={"tests"})
        cache_files = self._collect_files(CACHE_ROOT)

        self.assertEqual(
            marketplace_files,
            cache_files,
            f"Cache and marketplace should have same files.\n"
            f"Only in marketplace: {marketplace_files - cache_files}\n"
            f"Only in cache: {cache_files - marketplace_files}",
        )


if __name__ == "__main__":
    unittest.main()
