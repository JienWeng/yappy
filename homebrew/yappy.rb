class Yappy < Formula
  desc "AI-powered LinkedIn engagement assistant"
  homepage "https://github.com/jienweng/yappy"
  url "https://github.com/jienweng/yappy/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.13"

  def install
    virtualenv_install_with_resources

    # Install the package
    system libexec/"bin/pip", "install", "."
  end

  def post_install
    # Install Playwright Chromium browser
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
