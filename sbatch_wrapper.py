import argparse
import difflib
import os
import re
import subprocess
import sys

project_stage_tags = [
    "data",
    "explore",
    "baseline",
    "ablate",
    "hyperparam",
    "final",
    "other",
]

run_type_tags = [
    "train",
    "pre-train",
    "post-train",
    "evaluate",
    "debug",
    "other",
]

standalone_tags = ["data"]


def parse_tag_string(tag_string: str, strict: bool = True):
    """Extract project name and tags from a string.

    Expects at least two comma-separated values: the project name and the
    project stage. If the project stage is not a standalone tag, expects one
    additional value indicating the run type.

    Args:
        tag_string: Comma-separated tag string, e.g. "proj,baseline,train".
        strict: If True, fail on unrecognized project stage/run type tags;
            otherwise accept them as custom tags.

    Returns:
        A comma-separated tag comment string like ("project_name,project_stage[,run_type]").
    """
    tags = tag_string.split(",")
    if len(tags) < 2:
        print(
            f"[ERROR] Expected at least two comma-separated values in comment field, but found: {tags}"
        )
        sys.exit(1)

    # Test if first tag is project stage or project name
    tmp_project_stage = verify_and_fix_tag(tags[0], project_stage_tags)
    if not tmp_project_stage: # First tag is project name
        project_name = clean_custom_tag(tags[0])
        tags = tags[1:]  # Pop project name tag
        project_stage = verify_and_fix_tag(tags[0], project_stage_tags)
    else: # First tag is project stage; project name is missing
        project_name = 'default'
        project_stage = tmp_project_stage
        
    if not project_stage:
        if strict:
            print(f"[ERROR] Could not match {tags[0]} to any project stage tags")
            sys.exit(1)
        project_stage = clean_custom_tag(tags[0])
        print(f"Using custom project stage tag: {project_stage}")

    run_type = ""
    if len(tags) > 1:  # Still a tag remaining
        run_type = verify_and_fix_tag(tags[1], run_type_tags)
        if not run_type:
            if strict:
                print(f"[ERROR] Could not match {tags[1]} to any run type tags")
                sys.exit(1)
            run_type = clean_custom_tag(tags[1])
            print(f"Using custom run type tag: {run_type}")

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


def clean_custom_tag(raw_tag: str):
    """Normalize and validate a user-provided custom tag or project name.

    Normalization rules:
    - Convert to lowercase
    - Replace spaces with underscores
    
    Validation rules:
    - Only alphanumeric characters, dashes and underscores are allowed
    - At least one alphanumeric character must be present

    Args:
        raw_tag: Raw tag string provided by the user.

    Returns:
        The cleaned tag string.

    Exits:
        If the tag does not meet the validation conditions.
    """
    tag = raw_tag.lower().replace(" ", "_")
    if re.search(r"[\w-]", tag) and re.search(r"[a-zA-Z0-9]", tag):
        return tag
    print(
        "[ERROR] Tags and project names must contain at least one" +
        "alphanumeric character, and optional dashes and underscores"
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
        sys.exit(1)
    if project_stage not in standalone_tags and not run_type:
        print("[ERROR] Run type tag missing!")
        sys.exit(1)
    tags = [project_name, project_stage]
    if run_type:
        tags.append(run_type)
    print(f"Project name: {project_name}")
    print(f"Job tags: {project_stage}, {run_type}")
    return ",".join(tags)


def prompt_index(tags: list, prompt_name: str):
    """Prompt the user to choose a tag by numeric index from `tags`.

    Displays the available tags with indices and accepts a numeric choice. If
    the chosen tag is the literal "other", prompts for a custom tag.

    Args:
        tags: List of tag strings to present to the user.
        prompt_name: Short tag name used in prompts (e.g. "project stage").

    Returns:
        The selected tag string (either one from `tags` or a validated custom
        tag entered by the user).
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
        return selected


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
        Otherwise, you can specify the tags from the command line using either 
        the '--tags' option for standard tags, or the '--project_stage' and 
        '--run_type' options together for custom tags. The standard tag options 
        are [{", ".join(project_stage_tags[:-1])}] for PROJECT STAGE, and 
        [{", ".join(run_type_tags[:-1])}] for RUN TYPE. If you don't specify any 
        tags, the script will prompt you to do so interactively. This may crash 
        automatic launching scripts that make calls to sbatch, so remember to add your tags!
        """,
        add_help=True,
    )

    tags_help_msg = f"""
    Project stage tags: [{", ".join(project_stage_tags[:-1])}];
    Run type tags:      [{", ".join(run_type_tags[:-1])}]"""
    
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
        help=f"project stage tag and run type tag (comma-separated), overrides Slurm script comments. {tags_help_msg}",
    )
    parser.add_argument(
        "--project_stage",
        type=str,
        nargs="?",
        help="custom project stage tag name, mutually exclusive with --tags",
    )
    parser.add_argument(
        "--run_type",
        type=str,
        nargs="?",
        help="custom run type tag name, mutually exclusive with --tags",
    )
    parser.add_argument("script_path", type=str, help="Slurm script path")
    parser.add_argument("script_args", nargs="*", help="Slurm script arguments")
    args = parser.parse_args()

    # Look for Slurm script comments
    with open(args.script_path, "r") as f:
        script_src = f.read()
    comment_match = re.search(r"#SBATCH --comment\s+[\"']?([-\w,]+)[\"']?", script_src)

    # Define tags
    if args.tags:
        tags = parse_tag_string(",".join([args.project, args.tags]))
    elif args.project_stage or args.run_type:
        tag_string = ",".join([args.project, args.project_stage, args.run_type])
        tags = parse_tag_string(tag_string, strict=False)
    elif comment_match:
        tag_string = comment_match.group(1)
        tags = parse_tag_string(tag_string, strict=False)
    else:
        print("[WARNING] No tags specified for the job!")
        project_stage = prompt_index(project_stage_tags, "project stage")
        run_type = ""
        if project_stage not in standalone_tags:
            run_type = prompt_index(run_type_tags, "run type")
        tags = tag_comment(args.project, project_stage, run_type)

    # Run original sbatch command and save tags
    result = subprocess.run(
        [args.script_path, *args.script_args],
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

    # print(f"If you want to update the tags, run:\n\n    scontrol update job  comment=<project name>,<project stage>,<run type>\n{tags_help_msg}")
    save_tags(slurm_job_id, tags)
    sys.exit(result.returncode)
