import sys
from importlib import util
from pathlib import Path
from types import SimpleNamespace

import pytest


def _install_module_stub(name: str, attributes: dict[str, object]) -> None:
    module = SimpleNamespace(**attributes)
    sys.modules[name] = module


def _install_dependency_stubs() -> None:
    if "docker" not in sys.modules:
        errors_namespace = SimpleNamespace(DockerException=Exception, ImageNotFound=Exception)
        docker_namespace = SimpleNamespace(errors=errors_namespace)
        sys.modules["docker"] = docker_namespace
        sys.modules["docker.errors"] = errors_namespace

    if "rich" not in sys.modules:
        _install_module_stub("rich", {})
        _install_module_stub("rich.console", {"Console": object})
        _install_module_stub("rich.panel", {"Panel": object})
        _install_module_stub("rich.text", {"Text": object})


_install_dependency_stubs()

UTILS_PATH = Path(__file__).resolve().parents[2] / "strix" / "interface" / "utils.py"
spec = util.spec_from_file_location("interface_utils", UTILS_PATH)
interface_utils = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(interface_utils)

infer_target_type = interface_utils.infer_target_type


@pytest.mark.parametrize(
    "ip_input,expected",
    [
        ("192.168.1.1", {"target_ip": "192.168.1.1"}),
        ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", {"target_ip": "2001:db8:85a3::8a2e:370:7334"}),
    ],
)
def test_infer_target_type_ip_addresses(ip_input, expected):
    target_type, target_dict = infer_target_type(ip_input)

    assert target_type == "ip_address"
    assert target_dict == expected


def test_infer_target_type_bare_repository_host():
    target_type, target_dict = infer_target_type("github.com/example/repo")

    assert target_type == "repository"
    assert target_dict == {"target_repo": "https://github.com/example/repo"}


@pytest.mark.parametrize(
    "git_target",
    [
        "git@github.com:example/repo.git",
        "https://github.com/example/repo.git",
    ],
)
def test_infer_target_type_git_urls(git_target):
    target_type, target_dict = infer_target_type(git_target)

    assert target_type == "repository"
    assert target_dict == {"target_repo": git_target}


def test_infer_target_type_domain():
    target_type, target_dict = infer_target_type("example.com")

    assert target_type == "web_application"
    assert target_dict == {"target_url": "https://example.com"}


def test_infer_target_type_existing_directory(tmp_path):
    target_type, target_dict = infer_target_type(str(tmp_path))

    assert target_type == "local_code"
    assert target_dict == {"target_path": str(tmp_path.resolve())}


@pytest.mark.parametrize("invalid_target", ["", None, "not-a-valid-target"])
def test_infer_target_type_invalid_inputs(invalid_target):
    with pytest.raises(ValueError):
        infer_target_type(invalid_target)  # type: ignore[arg-type]
