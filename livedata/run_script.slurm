#!/bin/bash
#SBATCH --job-name=daily_update
#SBATCH --time=00:30:00  # Maximum runtime
#SBATCH --partition="Short"
#SBATCH --nodelist=ouce-cn10
#SBATCH --cpus-per-task=1

# Activate your Conda environment (if applicable)
source activate myenv

# Navigate to the script directory
cd /soge-home/users/kebl6418/charlesknight1.github.io

# Run your Python script
python livedata/download_satellite.py

# Git commands to commit and push changes
git add .
git commit -m "Daily update: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin master

echo "Script finished and changes pushed to GitHub."
