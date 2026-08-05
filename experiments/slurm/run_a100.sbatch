#!/bin/bash -l
# Template sbatch script for the QCRI Panther cluster's gpu-A100 partition.
# Usage: sbatch run_a100.sbatch <python_script.py> [args...]
#
# Requires membership in an A100 slurm account. The guide's generic examples
# are 'A100'/'a100_qos' (permanent QCRI staff) or 'A100_Intern'/'A100_Intern',
# but account names are actually per-user/per-institution -- this project's
# HBKU account is 'a100_hbku'/'a100_hbku_qos' (confirmed via `sacctmgr show
# associations user=<you> format=Account,Partition,QOS -p`; run that first if
# sbatch errors with "Invalid account or account/partition combination").
# Max job runtime on this partition is 3 days; email qcrisupport@hbku.edu.qa
# (CC your Research Director) to extend. Max 4 concurrent jobs per user.

#SBATCH -J matpcr_a100
#SBATCH -o logs/%x_%j.out
#SBATCH -e logs/%x_%j.err
#SBATCH -p gpu-A100
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=32000
#SBATCH -A a100_hbku
#SBATCH -q a100_hbku_qos

module load cuda12.1/toolkit/12.1.1

# Anaconda/conda env is expected to already be set up on the shared home
# (see experiments/slurm/README.md) -- activate it here, e.g.:
# conda activate matpcr

nvidia-smi

python3 "$@"
