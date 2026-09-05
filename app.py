import subprocess
import sys

if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "streamlit_app.py",
            "--server.port",
            "8000",
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
        ],
        check=True,
    )
