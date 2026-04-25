import os
import sys
import subprocess
import shutil

# Our project-specific temp directory
NUITKA_TMPDIR = "/tmp/code-index-nuitka"

def run_command(cmd, description):
    """Run a command with project-specific temp directory cleanup."""
    print(f"\n{description}")
    print(f"Command: {' '.join(cmd)}")
    
    if os.path.exists(NUITKA_TMPDIR):
        shutil.rmtree(NUITKA_TMPDIR, ignore_errors=True)
    os.makedirs(NUITKA_TMPDIR, exist_ok=True)
    
    env = os.environ.copy()
    env["TMPDIR"] = NUITKA_TMPDIR
    
    try:
        result = subprocess.run(cmd, cwd=os.getcwd(), env=env)
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            return True
        else:
            print(f"✗ {description} failed (exit code: {result.returncode})")
            return False
    finally:
        if os.path.exists(NUITKA_TMPDIR):
            shutil.rmtree(NUITKA_TMPDIR, ignore_errors=True)

def build_cli_binary():
    """Build the CLI binary with Magika AI, Universal Schema, and HelpTree embedded."""
    venv_python = os.path.abspath(".venv/bin/python")
    
    cmd = [
        venv_python, "-m", "nuitka",
        "--mode=onefile",
        f"--python-for-scons={venv_python}",
        "--assume-yes-for-downloads",
        "--output-filename=code-index",
        "--output-dir=dist",
        "--remove-output",
        
        # Include all essential packages
        "--include-package=code_index",
        "--include-package=tree_sitter",
        "--include-package=tree_sitter_language_pack",
        "--include-package=qdrant_client",
        "--include-package=fastmcp",
        "--include-package=magika",
        "--include-package=rich",
        "--include-package=charset_normalizer",

        # Embed Magika ONNX model and Universal Relationship Schema
        "--include-package-data=magika",
        "--include-data-dir=src/code_index/queries=code_index/queries",

        # Proven Nuitka Optimization Suite
        "--clang",
        "--lto=no", # Disabled for stability across Python minor versions
        "--prefer-source-code",

        # Onefile UX: Fast extraction to local cache
        '--onefile-tempdir-spec={CACHE_DIR}/nuitka/code-index',

        # Aggressive Bloat Exclusion (Structural elimination of unused modules)
        "--nofollow-import-to=chardet",
        "--nofollow-import-to=torch",
        "--nofollow-import-to=sympy",
        "--noinclude-custom-mode=chardet:error",
        "--noinclude-custom-mode=torch:error",
        "--noinclude-custom-mode=sympy:error",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=tests",
        "--noinclude-setuptools-mode=nofollow",
        "--noinclude-pytest-mode=nofollow",
        
        # Silence options-nanny and ensure torch is disabled
        "--module-parameter=torch-disable-jit=yes",
        
        "src/bin/cli_entry.py"
    ]

    print("Building Universal Structural Intelligence CLI binary...")
    if run_command(cmd, "Building CLI binary"):
        print("CLI binary built successfully: dist/code-index")
    else:
        sys.exit(1)

if __name__ == "__main__":
    build_cli_binary()
