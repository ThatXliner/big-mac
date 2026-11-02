import io
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inventory
import migration


class ExportTests(unittest.TestCase):
    def test_metadata_omits_values_arguments_and_arbitrary_labels(self):
        private = "fixture-value-that-must-remain-private"
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            plists = home / "Library/LaunchAgents"
            plists.mkdir(parents=True)
            with (plists / "example.plist").open("wb") as stream:
                plistlib.dump({"Label": "example", "ProgramArguments": ["/usr/bin/python3", private],
                               "EnvironmentVariables": {"EXAMPLE_PASSWORD": private}}, stream)
            tunnel = home / ".cloudflared"
            tunnel.mkdir()
            (tunnel / "config.yml").write_text(f"tunnel: {private}\ningress:\n  - hostname: app.example.com\n    service: http://localhost:8093\n  - service: http_status:404\n")
            container = {"Name": "/example", "Image": "sha256:abc", "State": {"Status": "running"},
                "Config": {"Image": "example:latest", "Env": ["EXAMPLE_PASSWORD=" + private],
                           "Cmd": [private], "Labels": {"arbitrary": private}},
                "HostConfig": {"RestartPolicy": {"Name": "always"}, "PortBindings": {}}, "Mounts": []}

            def fake_run(*args):
                if args == ("docker", "ps", "-aq"):
                    return "abc"
                if args[:2] == ("docker", "inspect"):
                    return json.dumps([container])
                if args[:3] == ("docker", "image", "inspect"):
                    return '[{"RepoDigests": ["example@sha256:abc"]}]'
                raise AssertionError(args)

            with patch.object(Path, "home", return_value=home), patch.object(inventory, "run", side_effect=fake_run):
                result = inventory.collect(include_system=False)
            self.assertNotIn(private, json.dumps(result))
            self.assertEqual(result["containers"][0]["environment_keys"], ["EXAMPLE_PASSWORD"])
            self.assertEqual(result["launch_agents"][0]["environment_keys"], ["EXAMPLE_PASSWORD"])
            self.assertEqual(result["ingress_routes"][0]["hostname"], "app.example.com")

    def test_migration_tar_has_relative_members_and_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "config with spaces.txt"
            source.write_bytes(b"private test data\n")
            archive = subprocess.check_output(migration.tar_command([str(source)]))
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
                self.assertFalse(any(m.name.startswith("/") or ".." in Path(m.name).parts for m in tar))
                self.assertEqual(tar.extractfile(str(source).lstrip("/")).read(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
