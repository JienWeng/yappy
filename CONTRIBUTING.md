# Contributing to Yappy

Thank you for your interest in contributing to Yappy! We welcome all types of contributions, from bug fixes to documentation improvements and new features.

---

## Local Development Setup

Yappy is built with Python 3.11+ and uses Playwright for browser automation.

### 1. Clone the repository
```bash
git clone https://github.com/jienweng/yappy.git
cd yappy
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
Install Yappy in editable mode with development dependencies:
```bash
pip install -e .
pip install -r requirements.txt
```

### 4. Install Playwright browsers
Yappy uses Chromium for LinkedIn interaction:
```bash
playwright install chromium
```

---

## Testing

We use `pytest` for testing. Please ensure all tests pass before submitting a Pull Request.

Run the full test suite:
```bash
pytest
```

To run specific tests:
```bash
pytest tests/unit/test_config.py
```

---

## Code Style & Guidelines

*   **Formatting:** We aim for clean, idiomatic Python. Please follow PEP 8.
*   **Type Hints:** Use type hints for all new functions and classes.
*   **Documentation:** Update the `ARCHITECTURE.md` or `README.md` if your changes introduce new concepts or change user-facing behavior.
*   **Tests:** Every new feature or bug fix must include corresponding tests.

---

## Pull Request Process

1.  **Branching:** Create a new branch for your work:
    *   `feat/your-feature-name`
    *   `fix/your-bug-fix`
    *   `docs/your-doc-update`
2.  **Commit Messages:** Use descriptive, concise commit messages.
3.  **PR Summary:** In your Pull Request, clearly describe the changes and provide instructions on how to verify them.
4.  **Review:** Once submitted, a maintainer will review your code. We may ask for changes or clarifications before merging.

---

## License

By contributing to Yappy, you agree that your contributions will be licensed under the [MIT License](LICENSE).
