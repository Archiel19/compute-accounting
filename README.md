# Compute Accounting on Jean Zay

Following the [analysis](https://arxiv.org/abs/2604.11154) of the compute 
spent to develop [Moshi](https://arxiv.org/abs/2410.00037) by Kyutai, our goal is now to 
break down the compute that the members of the **[IMAGINE](https://imagine-lab.enpc.fr/)** 
computer vision laboratory spend on the **Jean Zay** supercomputing cluster.

The idea is simple: to tag every launched job indicating a **project name**, a **project stage**, and a **run type**.

The **project name** is of course flexible, but the **project stage** and the **run type** tags
should be taken from the following lists:

### Project stage tags
- `data`: build or process a dataset (does not require a **run type** tag)
- `explore`: try ideas until something works
- `baseline`: run an in-house baseline or reproduce one from related work
- `ablate`: identify choices that do not have much of an impact
- `hyperparam`: hyperparameter search to improve performance
- `final`: final version (hopefully)
- `other`: custom tag

### Run type tags
- `train`: train a model in a single stage
- `pre-train`: pre-train a model on a large amount of data
- `post-train`: post-train or fine-tune the model
- `evaluate`: evaluate the performance of the model (includes probing and sample generation)
- `debug`: diagnose and fix a known issue 
- `other`: custom tag

## How to do it?

At the most basic level, it is enough to add a comment to your Slurm script like so:
```
#SBATCH --comment=[<project_name>,]<project_stage>,<run_type>
```

But to make sure that everyone uses (valid) tags, we have written an **`sbatch` wrapper**
that checks your Slurm script for a comment like the one shown above, or otherwise
lets you define the tags from the command line or interactively.

## Sbatch wrapper documentation

> **WARNING**: This is a very first implementation of the wrapper, so bugs are likely to occur!

> **NOTE**: You can always run `sbatch --help` to display the information in this section once the wrapper is installed

### Project name
The **project name** is optional and defaults to `default`, but you can also specify it with:
```
sbatch --project <project name> ...
```

### Tags

After installing the wrapper, you can run `sbatch` as usual if your Slurm script already has appropriate tags.

Otherwise, you should use one of the following options to pass the tags in the command line:

- If the standard tags are enough in your case:
    ```
    sbatch --tags <project stage>,<run type> ...
    ```
    > **NOTE**: The wrapper has some typo tolerance, but the order of the tags is important

- If you want to use at least one custom tag:
    ```
    sbatch --project_stage <project stage> --run_type <run type> ...
    ```
If you do not specify any tags anywhere, the wrapper will prompt you for them interactively. This might break your fancy
launching scripts, so be careful!


## Install
To install the `sbatch` wrapper script, run this command after logging in to Jean Zay:
```
curl -sSL https://raw.githubusercontent.com/Archiel19/compute-accounting/main/install.sh | bash
```

## Uninstall
To uninstall the `sbatch` wrapper script, run this command after logging in to Jean Zay:
```
curl -sSL https://raw.githubusercontent.com/Archiel19/compute-accounting/main/uninstall.sh | bash
```
