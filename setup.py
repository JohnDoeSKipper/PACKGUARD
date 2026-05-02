"""
PackGuard — First-time setup script
Works on Windows, macOS, and Linux.
Run: python setup.py
"""

import subprocess, sys, os, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(ROOT, "venv")
PY   = sys.executable

# Detect venv python path
if os.name == "nt":   # Windows
    VENV_PY  = os.path.join(VENV, "Scripts", "python.exe")
    VENV_PIP = os.path.join(VENV, "Scripts", "pip.exe")
else:                  # macOS / Linux
    VENV_PY  = os.path.join(VENV, "bin", "python")
    VENV_PIP = os.path.join(VENV, "bin", "pip")


def run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kw)


def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║  PackGuard v2.0 — First-time setup       ║")
    print("╚══════════════════════════════════════════╝\n")

    # 1. Create venv
    if not os.path.exists(VENV_PY):
        print("→ Creating virtual environment...")
        run([PY, "-m", "venv", "venv"], cwd=ROOT)
    else:
        print("→ Virtual environment already exists, skipping")

    # 2. Upgrade pip
    print("\n→ Upgrading pip...")
    run([VENV_PY, "-m", "pip", "install", "--upgrade", "pip", "-q"], cwd=ROOT)

    # 3. Install requirements
    print("\n→ Installing dependencies from requirements.txt...")
    run([VENV_PIP, "install", "-r", "requirements.txt", "-q"], cwd=ROOT)

    # 4. Build KB index
    print("\n→ Building knowledge base index...")
    run([VENV_PY, "kb/embed.py"], cwd=ROOT)

    # 5. Run tests
    print("\n→ Running unit tests...")
    run([VENV_PY, "-m", "pytest", "tests/test_all.py", "-v", "--tb=short"], cwd=ROOT)

    # 6. Create .env from template
    env_path = os.path.join(ROOT, ".env")
    example_path = os.path.join(ROOT, ".env.example")
    if not os.path.exists(env_path):
        shutil.copy(example_path, env_path)
        print(f"\n→ Created .env from template")
        print(f"   ⚠  Open .env and paste your ANTHROPIC_API_KEY")
    else:
        print("\n→ .env already exists, skipping")

    print("\n╔══════════════════════════════════════════╗")
    print("║  Setup complete! Next steps:             ║")
    print("║                                          ║")
    print("║  1. Open .env and add your API key       ║")
    print("║  2. Press F5 in VS Code to start server  ║")
    print("║     OR run: python -m uvicorn main:app   ║")
    print("║             --reload --port 8001         ║")
    print("║  3. Open frontend/index.html in browser  ║")
    print("║  4. Swagger docs: localhost:8001/docs    ║")
    print("╚══════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
