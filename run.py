import os
import subprocess
import sys

def run_app():
    """Run the Flask web application"""
    print("Starting the web application...")
    app_process = subprocess.Popen([sys.executable, "app.py"])
    return app_process

def run_scheduler():
    """Run the price tracker scheduler"""
    print("Starting the price tracker scheduler...")
    scheduler_process = subprocess.Popen([sys.executable, "scheduler.py"])
    return scheduler_process

if __name__ == "__main__":
    try:
        # Start both processes
        app_process = run_app()
        scheduler_process = run_scheduler()
        
        print("Both services are running. Press Ctrl+C to stop.")
        
        # Wait for them to complete (which won't happen unless there's an error)
        app_process.wait()
        scheduler_process.wait()
        
    except KeyboardInterrupt:
        print("\nStopping services...")
        # Try to terminate processes gracefully
        if 'app_process' in locals():
            app_process.terminate()
        if 'scheduler_process' in locals():
            scheduler_process.terminate()
        print("Services stopped.")
        sys.exit(0) 