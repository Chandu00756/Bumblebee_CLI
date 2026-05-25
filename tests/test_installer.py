import pytest
from unittest.mock import patch, MagicMock
from bbcli import installer

def test_go_available_true():
    with patch("shutil.which", return_value="/usr/local/bin/go"):
        assert installer._go_available() is True

def test_go_available_false():
    with patch("shutil.which", return_value=None):
        assert installer._go_available() is False

def test_bumblebee_path_via_which():
    with patch("shutil.which", return_value="/usr/local/bin/bumblebee"):
        assert installer._bumblebee_path() == "/usr/local/bin/bumblebee"

def test_status_not_installed():
    with patch("bbcli.installer._bumblebee_path", return_value=None), \
         patch("bbcli.installer._go_available", return_value=True):
        s = installer.status()
        assert s["installed"] is False
        assert s["path"] == "—"

def test_install_already_installed():
    with patch("bbcli.installer._bumblebee_path", return_value="/bin/bumblebee"), \
         patch("bbcli.installer.get_version", return_value="v0.1.1"):
        result = installer.install(update=False)
        assert result is True

def test_install_no_go():
    with patch("bbcli.installer._bumblebee_path", return_value=None), \
         patch("bbcli.installer._go_available", return_value=False):
        result = installer.install()
        assert result is False