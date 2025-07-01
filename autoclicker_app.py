"""
Main entry point for the Gelişmiş Otomatik Tıklayıcı application.

This script initializes and runs the AppCore, which in turn sets up the UI
and handles the application's core logic.
"""
# This file is now the main entry point for the application.
# It imports the AppCore and runs it.

from core import AppCore

if __name__ == "__main__":
    app = AppCore()
    app.run()
