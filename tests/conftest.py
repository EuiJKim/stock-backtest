import pytest


@pytest.fixture(scope="session")
def tk_root():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
    except Exception:
        pytest.skip("Tkinter not available")
    yield root
    try:
        root.destroy()
    except Exception:
        pass
