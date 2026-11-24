"""Jalankan semua uji unit (tanpa Docker/FastAPI):  python scripts/uji_unit/run_all.py"""
import pathlib
import sys
import unittest

folder = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(folder))
hasil = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover(str(folder), pattern="test_*.py"))
sys.exit(0 if hasil.wasSuccessful() else 1)
