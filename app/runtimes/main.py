import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Dynamic path configuration to ensure the application can resolve local modules
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ui2.main_window import MainWindow

def run_application():
    """
    Initializes the Qt Application context and launches the main dashboard interface.
    Manages the application lifecycle and ensures clean exit.
    """
    # Initialize the high-level GUI framework
    app = QApplication(sys.argv)
    
    # Create the primary application window (The Dashboard)
    window = MainWindow()
    window.show()
    
    # Start the event loop and exit the process when the window is closed
    sys.exit(app.exec())

if __name__ == "__main__":
    run_application()