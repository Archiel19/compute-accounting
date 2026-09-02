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

    Expects a project stage and, unless the stage is standalone, a run type.
    The project name is optional and defaults to ``default``.

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
    # Keep stdout identical to native sbatch output: Submitit parses the job id
    # from it. And might break some researchers fancy scripts, so send it to stderr instead.
    print(f"Project name: {project_name}", file=sys.stderr)
    print(f"Job tags: {project_stage}, {run_type}", file=sys.stderr)
    print(file=sys.stderr)
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


def extract_sbatch_comment(sbatch_args: list):
    """Extract one native ``sbatch --comment`` option.

    ``sbatch`` accepts both ``--comment=value`` and ``--comment value``.
    The option is removed from the returned argument list so the caller can
    add one validated, canonical comment when invoking the real ``sbatch``.
    Every other native option and script argument is preserved in its original
    order. Duplicate comments are rejected.

    Returns:
        A ``(comment, remaining_args)`` tuple. ``comment`` is ``None`` when no
        command-line comment was supplied.
    """
    comment = None
    remaining_args = []
    index = 0
    while index < len(sbatch_args):
        argument = sbatch_args[index]
        if argument == "--comment":
            if index + 1 == len(sbatch_args):
                print("[ERROR] --comment requires a value", file=sys.stderr)
                sys.exit(2)
            value = sbatch_args[index + 1]
            index += 2
        elif argument.startswith("--comment="):
            value = argument.removeprefix("--comment=")
            index += 1
        else:
            remaining_args.append(argument)
            index += 1
            continue

        if comment is not None:
            print("[ERROR] Specify at most one --comment option", file=sys.stderr)
            sys.exit(2)
        comment = value

    return comment, remaining_args


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
        default="default",
        help="project name, overrides Slurm script comments",
    )

    parser.add_argument(
        "--tags",
        type=str,
        help=f"project stage tag and run type tag (comma-separated), overrides Slurm script comments. {project_stage_info}. {run_type_info}",
    )
    args, sbatch_args = parser.parse_known_args()

    command_comment, sbatch_args = extract_sbatch_comment(sbatch_args)
    command_tags = parse_tag_string(command_comment) if command_comment else None

    # Command-line options take precedence over script directives in sbatch.
    # Native sbatch modes without a script, such as --wrap, remain usable with
    # --tags or --comment.
    comment_match = None
    script_path = None
    if not command_comment:
        for argument in sbatch_args:
            if os.path.isfile(argument):
                script_path = argument
                break
    if script_path:
        with open(script_path, "r") as f:
            script_src = f.read()
        comment_match = re.search(
            r"#SBATCH --comment=[\"']?([-\w,]+)[\"']?", script_src
        )

    # Define tags
    if args.tags:
        tags = parse_tag_string(",".join([args.project, args.tags]))
    elif command_tags:
        tags = command_tags
    elif comment_match:
        tag_string = comment_match.group(1)
        tags = parse_tag_string(tag_string)
    else:
        if not sys.stdin.isatty():
            print(
                "[ERROR] No tags specified and stdin is not interactive. "
                "Add an '#SBATCH --comment=<project>,<project-stage>,<run-type>' "
                "directive or pass --project and --tags.",
                file=sys.stderr,
            )
            sys.exit(1)

        print("[WARNING] No tags specified for the job!")
        project_stage = prompt_index(project_stage_tags, "project stage")
        run_type = ""
        if project_stage not in standalone_tags:
            run_type = prompt_index(run_type_tags, "run type")
        tags = tag_comment(args.project, project_stage, run_type)

    # Supply the comment to sbatch itself. This atomically stores it with the
    # job and avoids a race-prone post-submission ``scontrol update`` call.
    result = subprocess.run(["/usr/bin/sbatch", f"--comment={tags}", *sbatch_args])
    sys.exit(result.returncode)
