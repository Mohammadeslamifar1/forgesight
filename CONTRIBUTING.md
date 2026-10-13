# Contributing

Use the locked Python and npm environments from the README. Run the Python tests, formatters, TypeScript/build checks, and relevant real-model browser tests before proposing changes.

Describe the problem, resulting behavior, and validation. Model changes should record split/configuration, compare against the existing baseline, and report operating-point and shift behavior. Never select hyperparameters using the held-out test labels and then describe that test as unseen evaluation.

Do not commit datasets, model binaries, private uploads, inspection records, environment files, or local absolute paths. Keep upstream attribution and dataset licenses with any derived imagery. Review report diffs before committing a new experiment.
