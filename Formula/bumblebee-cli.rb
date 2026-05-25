class BumblebeeCli < Formula
  include Language::Python::Virtualenv

  desc "Dependency security scanner for macOS — detects malicious, vulnerable, and suspicious packages"
  homepage "https://github.com/Chandu00756/Bumblebee_CLI"
  url "https://github.com/Chandu00756/Bumblebee_CLI/archive/refs/tags/v2.1.1.tar.gz"
  sha256 "572512d6459510fff0eca929b0d22765b4e36274126a14887de141ff8cf7eed7"
  license "MIT"

  depends_on "python@3.13"

  resource "click" do
    url "https://pypi.io/packages/source/c/click/click-8.4.1.tar.gz"
    sha256 "918b5633eddf6b41c32d4f454bf0de810065c74e3f7dbf8ee5452f8be88d3e96"
  end

  resource "fpdf2" do
    url "https://pypi.io/packages/source/f/fpdf2/fpdf2-2.8.7.tar.gz"
    sha256 "7060ccee5a9c7ab0a271fb765a36a23639f83ef8996c34e3d46af0a17ede57f9"
  end

  resource "packaging" do
    url "https://pypi.io/packages/source/p/packaging/packaging-26.2.tar.gz"
    sha256 "ff452ff5a3e828ce110190feff1178bb1f2ea2281fa2075aadb987c2fb221661"
  end

  resource "python-dateutil" do
    url "https://pypi.io/packages/source/p/python-dateutil/python-dateutil-2.9.0.post0.tar.gz"
    sha256 "37dd54208da7e1cd875388217d5e00ebd4179249f90fb72437e91a35459a0ad3"
  end

  resource "questionary" do
    url "https://pypi.io/packages/source/q/questionary/questionary-2.1.1.tar.gz"
    sha256 "3d7e980292bb0107abaa79c68dd3eee3c561b83a0f89ae482860b181c8bd412d"
  end

  resource "requests" do
    url "https://pypi.io/packages/source/r/requests/requests-2.34.2.tar.gz"
    sha256 "f288924cae4e29463698d6d60bc6a4da69c89185ad1e0bcc4104f584e960b9ed"
  end

  resource "rich" do
    url "https://pypi.io/packages/source/r/rich/rich-15.0.0.tar.gz"
    sha256 "edd07a4824c6b40189fb7ac9bc4c52536e9780fbbfbddf6f1e2502c31b068c36"
  end

  resource "shellingham" do
    url "https://pypi.io/packages/source/s/shellingham/shellingham-1.5.4.tar.gz"
    sha256 "8dbca0739d487e5bd35ab3ca4b36e11c4078f3a234bfce294b0a0291363404de"
  end

  resource "typer" do
    url "https://pypi.io/packages/source/t/typer/typer-0.25.1.tar.gz"
    sha256 "9616eb8853a09ffeabab1698952f33c6f29ffdbceb4eaeecf571880e8d7664cc"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Bumblebee CLI", shell_output("#{bin}/bee --version")
  end
end
