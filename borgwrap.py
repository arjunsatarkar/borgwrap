#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
from collections import defaultdict
from pathlib import Path
import argparse
import dataclasses
import subprocess
import sys
import tomllib


@dataclasses.dataclass
class RepoConfig:
    borg_repo: str
    borg_passphrase: str
    compression: str = "auto,lzma"

    def env(self):
        return {"BORG_REPO": self.borg_repo, "BORG_PASSPHRASE": self.borg_passphrase}


class Config:
    def __init__(self, config_path: Path):
        with open(config_path, "rb") as f:
            data: dict[str, list[dict[str, str | list[Path]]]] = tomllib.load(f)

        self.target_paths: defaultdict[str, list[RepoConfig]] = defaultdict(list)
        for repo_data in data["repos"]:
            repo_config = RepoConfig(
                repo_data["borg_repo"], repo_data["borg_passphrase"]
            )
            try:
                repo_config.compression = repo_data["compression"]
            except KeyError:
                pass
            target_path = repo_data.get("target_path", ".")
            self.target_paths[target_path].append(repo_config)


def main(config_path: Path, interactive: bool) -> None:
    config = Config(config_path)

    target_paths = list(config.target_paths)
    if interactive:
        for i, target_path in enumerate(target_paths):
            repos_num = len(config.target_paths[target_path])
            print(f"{i + 1}. {target_path}\n\t({repos_num} repo{'s' if repos_num != 1 else ''})")        
        try:
            input_text = input("Enter which of the above paths to back up (space-separated numbers or 'all'): ")
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if input_text.lower() != "all":
            target_paths = [target_paths[int(index) - 1] for index in input_text.split()]

    for target_path in target_paths:
        for repo_config in config.target_paths[target_path]:
            env = repo_config.env()

            subprocess.run(
                [
                    "borg",
                    "create",
                    "--compression",
                    "auto,lzma",
                    "--list",
                    "--show-rc",
                    "--stats",
                    "--verbose",
                    "::{utcnow}",
                    target_path,
                ],
                env=env,
            )

            subprocess.run(
                [
                    "borg",
                    "prune",
                    "--list",
                    "--show-rc",
                    "--stats",
                    "--keep-daily",
                    "2",
                    "--keep-weekly",
                    "1",
                    "--keep-monthly",
                    "1",
                    "--keep-yearly",
                    "1",
                ],
                env=env,
            )

            subprocess.run(["borg", "compact"], env=env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="borgwrap")
    parser.add_argument("-c", "--config_path", default="borgwrap.toml")
    parser.add_argument("-i", "--interactive", action="store_true")
    args = parser.parse_args()

    main(Path(args.config_path).resolve(), args.interactive)
