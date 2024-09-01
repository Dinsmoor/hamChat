from cx_Freeze import setup, Executable
import sys

# Dependencies are automatically detected, but it might need fine-tuning.
build_exe_options = {
    "packages": ["os", "tkinter", "socket", "threading"],
    "excludes": ["tkinter.test", "unittest", "email", "html", "http", "xml"],
    "include_files": ["plugins"]  # Add any additional files you need to include
}

# Base is set to "Win32GUI" for Windows GUI applications
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="hamChat",
    version="0.1",
    description="hamChat",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base)]
)