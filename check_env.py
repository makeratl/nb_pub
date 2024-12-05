import sys
import site
import subprocess

def check_environment():
    print("\n=== Python Environment Information ===")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    print("\nSite Packages Locations:")
    for path in site.getsitepackages():
        print(f"- {path}")
    
    print("\n=== Installed Packages ===")
    result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                          capture_output=True, text=True)
    print(result.stdout)

if __name__ == "__main__":
    check_environment() 