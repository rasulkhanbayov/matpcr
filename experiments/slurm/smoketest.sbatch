#!/bin/bash -l
# Minimal smoke test -- confirms account/QOS/module access works before
# submitting any real job. Run once per partition after initial setup:
#   sbatch -p gpu-A100 -A a100_hbku      -q a100_hbku_qos  experiments/slurm/smoketest.sbatch cuda12.1/toolkit/12.1.1
#   sbatch -p gpu-H200 -A h200_hbku -x crirdchpxd005 -q h200_hbku_qos  experiments/slurm/smoketest.sbatch cuda12.6/toolkit/12.6.2
# (partition/account/qos passed as sbatch CLI flags here so one file covers both queues --
#  account/QOS names are per-user, confirmed via: sacctmgr show associations user=<you> format=Account,Partition,QOS -p)

#SBATCH -J matpcr_smoketest
#SBATCH -o logs/%x_%j.out
#SBATCH -e logs/%x_%j.err
#SBATCH --gres=gpu:1
#SBATCH -c 2
#SBATCH --mem=4000

module load "$1"
nvidia-smi
python3 --version
echo "Smoke test OK on $(hostname)"
