# This file is now the main entry point for the application.
# It imports the AppCore and runs it.

from core import AppCore

if __name__ == "__main__":
    app = AppCore()
    app.run()
