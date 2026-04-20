import subprocess
import sys
import time
import os

def run_script(script_path):
    """Executes a python script and monitors for errors."""
    print(f"\n[RUNNING] {script_path}...")
    start_time = time.time()
    
    # Run the script as a separate process
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    
    if result.returncode == 0:
        duration = (time.time() - start_time) / 60
        print(f"[SUCCESS] {script_path} completed in {duration:.2f} minutes.")
        return True
    else:
        print(f"[FAILED] {script_path} exited with error code {result.returncode}.")
        return False

def main():
    print("==================================================")
    print("   WEATHER AI: FULL SYSTEM RE-CALIBRATION")
    print("==================================================")
    
    # Define paths relative to this root script
    ingestion_script = os.path.join("api_engine", "mass_ingestion.py")
    training_script = os.path.join("ml_engine", "master_training.py")
    inference_script = os.path.join("ml_engine", "inference_engine.py")

    # Step 1: Data Ingestion (The Foundation)
    if not run_script(ingestion_script):
        print("\n[CRITICAL] Pipeline halted: Ingestion failed.")
        sys.exit(1)

    # Step 2: Master Training (The Brain)
    if not run_script(training_script):
        print("\n[CRITICAL] Pipeline halted: Training failed.")
        sys.exit(1)

    # Step 3: Verification (The Test)
    print("\n[INFO] System updated. Generating verification forecast...")
    run_script(inference_script)

    print("\n==================================================")
    print("   ALL SYSTEMS NOMINAL - PIPELINE COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    main()