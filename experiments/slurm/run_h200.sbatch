#!/bin/bash -l
# Template sbatch script for the QCRI Panther cluster's gpu-H200 partition.
# Usage: sbatch run_h200.sbatch <python_script.py> [args...]
#
# Max job runtime on this partition is 3 days; email qcrisupport@hbku.edu.qa
# (CC your Research Director) to extend. Max 4 concurrent jobs per user.
# Excludes crirdchpxd005 by default (that node's H200s are split into MIG
# partitions, 4g.70gb/3g.70gb -- remove -x below if you specifically want a
# MIG slice, and use --gres=gpu:4g.70gb:N / gpu:3g.70gb:N instead of gpu:N).
# For >4 GPUs on this queue, the guide's generic example switches -A/-q to
# H200_16GPUs/h200_qos_16_gpus (preemptable by normal H200 jobs after a
# 6-hour grace period -- see the guide's SIGUSR1/SIGTERM checkpointing
# pattern if using this) -- confirm your own institution's equivalent
# account/QOS name via `sacctmgr show associations user=<you>
# format=Account,Partition,QOS -p` before assuming this name applies to you
# (this project's own A100/H200 accounts turned out to be 'a100_hbku'/
# 'h200_hbku', not the guide's generic 'A100'/'H200').

#SBATCH -J matpcr_h200
#SBATCH -o logs/%x_%j.out
#SBATCH -e logs/%x_%j.err
#SBATCH -p gpu-H200
#SBATCH -x crirdchpxd005
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=64000
#SBATCH -A h200_hbku
#SBATCH -q h200_hbku_qos

module load cuda12.6/toolkit/12.6.2

# conda activate matpcr

nvidia-smi

python3 "$@"
