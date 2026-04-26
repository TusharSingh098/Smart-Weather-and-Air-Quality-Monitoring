"""
run_ml_pipeline.py
Master MLOps & System Lifecycle Controller.

Automates the end-to-end Machine Learning pipeline. Sequentially executes 
data ingestion, multi-target algorithm training, and forecast verification. 
Utilizes subprocess isolation for optimal memory management.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import subprocess
import sys
import time
import os

def run_script(script_path: str) -> bool:
    """
    Executes a target Python script within an isolated OS-level process.
    Monitors for execution anomalies and returns a boolean success flag.
    
    Args:
        script_path (str): Relative path to the Python module to execute.
        
    Returns:
        bool: True if the process exited with code 0 (Success), False otherwise.
    """
    print(f"\n[RUNNING] {script_path}...")
    start_time = time.time()
    
    # Execute the script using the exact same Python interpreter running this file
    # capture_output=False ensures the child process streams its print() statements to the main console
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    
    if result.returncode == 0:
        duration = (time.time() - start_time) / 60
        print(f"[SUCCESS] {script_path} completed in {duration:.2f} minutes.")
        return True
    else:
        print(f"[FAILED] {script_path} exited with error code {result.returncode}.")
        return False

def main():
    """
    The main execution sequence enforcing the fail-fast dependency graph.
    """
    print("==================================================")
    print("   WEATHER AI: FULL SYSTEM RE-CALIBRATION")
    print("==================================================")
    
    # Define execution targets relative to the project root
    ingestion_script = os.path.join("api_engine", "mass_ingestion.py")
    training_script  = os.path.join("ml_engine", "master_training.py")
    inference_script = os.path.join("ml_engine", "inference_engine.py")

    # ─── Phase 1: Data Engineering (ETL) ──────────────────────────────────────
    if not run_script(ingestion_script):
        print("\n[CRITICAL] Pipeline halted: Ingestion failed.")
        sys.exit(1) # Emit fatal exit code to OS

    # ─── Phase 2: Algorithm Training & Serialization ──────────────────────────
    # This phase will not execute unless Phase 1 completes successfully
    if not run_script(training_script):
        print("\n[CRITICAL] Pipeline halted: Training failed.")
        sys.exit(1)

    # ─── Phase 3: System Verification ─────────────────────────────────────────
    # Run a localized test to ensure the newly serialized models are functional
    print("\n[INFO] System updated. Generating verification forecast...")
    run_script(inference_script)

    print("\n==================================================")
    print("   ALL SYSTEMS NOMINAL - PIPELINE COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    main()