#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jednoduchý launcher pro crawler
"""

import subprocess
import sys
import os

def install_requirements():
    """Instaluje potřebné balíčky"""
    print("Instaluji požadované balíčky...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def main():
    try:
        # Pokusíme se importovat potřebné moduly
        import requests
        import bs4
    except ImportError:
        print("Instaluji chybějící balíčky...")
        install_requirements()
    
    # Spustíme crawler
    subprocess.run([sys.executable, os.path.join("lib", "crawler.py")])

if __name__ == "__main__":
    main()
