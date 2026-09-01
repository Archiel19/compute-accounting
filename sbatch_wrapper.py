#!/usr/bin/python

import argparse
import difflib
import os
import re
import signal
import subprocess
import sys

project_stage_tags = [
    "data",
    "explore",
    "baseline",
    "ablate",
    "hyperparam",
    "final",
]

run_type_tags = [
    "train",
    "pre-train",
    "post-train",
    "evaluate",
    "debug",
]

project_stage_info = """Project stage tags:
- `data`: build or process a dataset (does not require a 'run type' tag)
- `explore`: try ideas until something works
- `baseline`: run an in-house baseline or reproduce one from related work
- `ablate`: identify choices that do not have much of an impact
- `hyperparam`: hyperparameter search to improve performance
- `final`: final version (hopefully)
"""


run_type_info = """Run type tags:
- `train`: train a model in a single stage
- `pre-train`: pre-train a model on a large amount of data
- `post-train`: post-train or fine-tune the model
- `evaluate`: evaluate the performance of the model (includes probing and sample generation)
- `debug`: diagnose and fix a known issue
"""

standalone_tags = ["data"]


def signal_handler(sig, frame):
    print()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def parse_tag_string(tag_string: str):
    """Extract project name and tags from a string.

    Expects at least two comma-separated values: the project name and the
    project stage. If the project stage is not a standalone tag, expects one
    additional value indicating the run type.

    Args:
        tag_string: Comma-separated tag string, e.g. "proj,baseline,train".

    Returns:
        A comma-separated tag comment string like ("[project_name,]project_stage,run_type").
    """
    tags = tag_string.split(",")
    if len(tags) < 2:
        print(
            f"[ERROR] Expected at least two comma-separated values in comment field, but found: {tags}"
        )
        sys.exit(1)

    # Test if first tag is project stage or project name
    tmp_project_stage = verify_and_fix_tag(tags[0], project_stage_tags)
    if not tmp_project_stage:  # First tag is project name
        project_name = clean_project_name(tags[0])
        tags = tags[1:]  # Pop project name tag
        project_stage = verify_and_fix_tag(tags[0], project_stage_tags)
    else:  # First tag is project stage; project name is missing
        project_name = "default"
        project_stage = tmp_project_stage

    if not project_stage:
        print(f"[ERROR] Could not match {tags[0]} to any project stage tags")
        print(project_stage_info)
        sys.exit(1)

    if len(tags) < 1:
        print("[ERROR] Expected a run type tag, but there are no more tags left to parse")
        print(run_type_info)
        sys.exit(1)
        
    run_type = verify_and_fix_tag(tags[1], run_type_tags)
    if not run_type:
        print(f"[ERROR] Could not match {tags[1]} to any run type tags")
        print(run_type_info)
        sys.exit(1)

    return tag_comment(project_name, project_stage, run_type)


def verify_and_fix_tag(raw_tag: str, tag_list: list):
    """Find the closest match for `raw_tag` in `tag_list`.

    Args:
        raw_tag: User-supplied tag to match.
        tag_list: List of allowed tags to match against.

    Returns:
        The best matching tag from `tag_list` if one is found, otherwise an
        empty string.
    """
    raw_tag = raw_tag.strip()
    matched_tag = difflib.get_close_matches(raw_tag, tag_list, n=1)
    if not matched_tag:
        return ""
    return matched_tag[0]


def clean_project_name(raw_project_name: str):
    """Normalize and validate a user-provided project name.

    Normalization rules:
    - Convert to lowercase
    - Replace spaces with underscores

    Validation rules:
    - Only alphanumeric characters, dashes and underscores are allowed
    - At least one alphanumeric character must be present

    Args:
        raw_project_name: Raw project name provided by the user.

    Returns:
        The cleaned tag string.

    Exits:
        If the tag does not meet the validation conditions.
    """
    tag = raw_project_name.lower().replace(" ", "_")
    if re.search(r"[\w-]", tag) and re.search(r"[a-zA-Z0-9]", tag):
        return tag
    print(
        "[ERROR] Project names must contain at least one alphanumeric "
        "character, and optional dashes and underscores"
    )
    sys.exit(1)


def tag_comment(project_name: str, project_stage: str, run_type: str = None):
    """Construct and validate the final Slurm job comment string.

    Ensures the project name and project stage are present. For stages that
    are not considered standalone, a run type must also be provided. Prints a
    short summary to stdout and returns the comma-separated tag string.

    Args:
        project_name: Cleaned project name.
        project_stage: Validated project stage tag.
        run_type: Optional validated run type tag.

    Returns:
        A comma-separated string combining `project_name`, `project_stage`, and
        optionally `run_type`.

    Exits:
        If any of the required components are missing.
    """
    if not project_name:
        print("[ERROR] Project name missing!")
        sys.exit(1)
    if not project_stage:
        print("[ERROR] Project stage tag missing!")
        print(project_stage_info)
        sys.exit(1)
    if project_stage not in standalone_tags and not run_type:
        print("[ERROR] Run type tag missing!")
        print(run_type_info)
        sys.exit(1)
    tags = [project_name, project_stage]
    if run_type:
        tags.append(run_type)
    print(f"Project name: {project_name}")
    print(f"Job tags: {project_stage}, {run_type}")
    print()
    return ",".join(tags)


def prompt_index(tags: list, prompt_name: str):
    """Prompt the user to choose a tag by numeric index from `tags`.

    Displays the available tags with indices and accepts a numeric choice.

    Args:
        tags: List of tag strings to present to the user.
        prompt_name: Short tag name used in prompts (e.g. "project stage").

    Returns:
        The selected tag string (from `tags`).
    """
    print()
    for i, tag in enumerate(tags):
        print(f"{tag:.<25}{i}")
    print()
    while True:
        choice = input(f"\nSelect a {prompt_name.upper()} tag: ").strip()
        print()
        try:
            idx = int(choice)
        except ValueError:
            print("Please enter a valid integer index")
            continue
        if not (0 <= idx < len(tags)):
            print(f"Index out of range. Enter a number between 0 and {len(tags) - 1}")
            continue
        return tags[idx]


def save_tags(slurm_job_id: int, tags: str):
    """Attach tags to a Slurm job.

    Falls back to `SLURM_JOB_ID` environment variable if `slurm_job_id` is invalid.

    Args:
        slurm_job_id: Slurm job id. May be missing.
        tags: Comma-separated tag string to save as the job comment.

    Exits:
        If no job id can be found or if scontrol command fails.
    """
    job_id = slurm_job_id or os.getenv("SLURM_JOB_ID")
    if not job_id:
        print("[ERROR] Cannot save tags: No SLURM_JOB_ID found")
        sys.exit(1)
    cmd = ["scontrol", "update", "job", str(job_id), f"comment={tags}"]
    try:
        subprocess.run(cmd, check=True)
        print(f"Saved tags for job {job_id}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to run scontrol: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"""Slurm sbatch wrapper to enforce tag usage.
        If your script already has an '#SBATCH --comment <project name>,
        <project stage>,<run type>' directive, this wrapper will only verify your tags.
        Otherwise, you can specify the tags from the command line using
        the '--tags' option. The standard tag options
        are [{", ".join(project_stage_tags)}] for PROJECT STAGE, and
        [{", ".join(run_type_tags)}] for RUN TYPE. If you don't specify any
        tags, the script will prompt you to do so interactively. This may crash
        automatic launching scripts that make calls to sbatch, so remember to add your tags!
        """,
        add_help=True,
    )

    parser.add_argument(
        "--project",
        type=str,
        nargs="?",
        default="default",
        help="project name, overrides Slurm script comments",
    )

    parser.add_argument(
        "--tags",
        type=str,
        nargs="?",
        help=f"project stage tag and run type tag (comma-separated), overrides Slurm script comments. {project_stage_info}. {run_type_info}",
    )
    parser.add_argument("script_path", type=str, help="Slurm script path")
    parser.add_argument("script_args", nargs="*", help="Slurm script arguments")
    args = parser.parse_args()

    # Look for Slurm script comments
    with open(args.script_path, "r") as f:
        script_src = f.read()
    comment_match = re.search(r"#SBATCH --comment=[\"']?([-\w,]+)[\"']?", script_src)

    # Define tags
    if args.tags:
        tags = parse_tag_string(",".join([args.project, args.tags]))
    elif comment_match:
        tag_string = comment_match.group(1)
        tags = parse_tag_string(tag_string)
    else:
        print("[WARNING] No tags specified for the job!")
        project_stage = prompt_index(project_stage_tags, "project stage")
        run_type = ""
        if project_stage not in standalone_tags:
            run_type = prompt_index(run_type_tags, "run type")
        tags = tag_comment(args.project, project_stage, run_type)

    # Run original sbatch command and save tags
    result = subprocess.run(
        ["/usr/bin/sbatch", args.script_path, *args.script_args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")

    slurm_id_match = re.search(r"Submitted batch job (\d+)", result.stdout)
    if slurm_id_match:
        slurm_job_id = slurm_id_match.group(1)

    save_tags(slurm_job_id, tags)
    sys.exit(result.returncode)
