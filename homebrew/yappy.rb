class Yappy < Formula
  include Language::Python::Virtualenv

  desc "AI-powered LinkedIn engagement assistant"
  homepage "https://github.com/JienWeng/yappy"
  url "https://github.com/JienWeng/yappy/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "bb3c8907fcca0095e646b76b372cb9293e00b8f6956fb87c9e436a54882a60d0"
  license "MIT"

  depends_on "python@3.13"

  def install
    virtualenv_install_with_resources
  end

  def post_install
    system libexec/"bin/python", "-m", "playwright", "install", "chromium"
  end

  def caveats
    <<~EOS
      To get started, run:
        yap

      On first run, Yappy will guide you through setup:
        1. Enter your Gemini API key
        2. Log into LinkedIn
        3. Configure targeting preferences

      Get a Gemini API key at: https://aistudio.google.com/apikey
    EOS
  end

  test do
    assert_match "Yappy", shell_output("#{bin}/yap --help")
  end
end
