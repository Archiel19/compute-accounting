import re
import os
import sys
import subprocess

project_stage_tags = [
    "Data",
    "Explore",
    "Debug",
    "Baseline",
    "Ablate",
    "Hyperparameter search",
    "Hopefully final",
    "Other",
]

run_type_tags = [
    "Train (single stage)",
    "Pre-train",
    "Post-train",
    "Fine-tune",
    "Evaluate or probe",
    "Generate",
    "Other",
]


def prompt_index(tags, prompt_name):
    """Prompt for a numeric index into tags; if 'other' is selected, prompt for a custom string.
    Ensures the index is an integer in range and any custom string contains at least one alphanumeric character.
    """
    print("\n")
    for i, tag in enumerate(tags):
        print(f"{tag:.<25}{i}")
    while True:
        choice = input(f"\nSelect a {prompt_name.upper()} tag: ").strip()
        try:
            idx = int(choice)
        except ValueError:
            print("Please enter a valid integer index")
            continue
        if not (0 <= idx < len(tags)):
            print(f"Index out of range. Enter a number between 0 and {len(tags) - 1}")
            continue
        selected = tags[idx]
        if selected.lower() == "other":
            while True:
                selected = input(f"Enter custom {prompt_name}: ").strip()
                if not selected:
                    print("Tag cannot be empty")
                    continue
                if re.search(r"[\w-]", selected):
                    if re.search(r"[a-zA-Z0-9]", selected):
                        break
                    print("Tag must contain at least one alphanumeric character")
                else:
                    print("Only alphanumeric characters, dashes and underscores are allowed")
        return re.sub(r" \(.*\)", "", selected).lower().replace(" ", "_")


def save_tags(slurm_job_id):
    job_id = slurm_job_id or os.getenv("SLURM_JOB_ID")
    if not job_id:
        print("[ERROR] Cannot save tags: No SLURM_JOB_ID found")
        return
    cmd = ["scontrol", "update", "job", str(job_id), f"comment={project_stage},{run_type}"]
    try:
        subprocess.run(cmd, check=True)
        print(f"Saved tags for job {job_id}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to run scontrol: {e}")


if __name__ == "__main__":
    # Prompt the user for both choices
    project_stage = prompt_index(project_stage_tags, "project stage")
    run_type = prompt_index(run_type_tags, "run type")
    print(f"\nJob tags: ({project_stage}, {run_type})")

    # Run the original sbatch command with the provided arguments
    sbatch_cmd = sys.argv[1:]
    result = subprocess.run(
        sbatch_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    match = re.search(r"Submitted batch job (\d+)", result.stdout)
    if match:
        slurm_job_id = match.group(1)
    save_tags(slurm_job_id)
    sys.exit(result.returncode)
