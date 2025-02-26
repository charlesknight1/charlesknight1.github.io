#!/bin/bash
#SBATCH --job-name=daily_job
#SBATCH --time=00:30:00  # Maximum runtime
#SBATCH --partition="Short"
#SBATCH --cpus-per-task=1

# Activate your Conda environment (if applicable)
source /path/to/your/conda/bin/activate my_env

# Navigate to the script directory
cd /path/to/your/repo

# Run your Python script
python download_satellite.py

# Git commands to commit and push changes
git add .
git commit -m "Daily update: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin master

echo "Script finished and changes pushed to GitHub."
