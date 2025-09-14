#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
import argparse
import dataclasses
from pathlib import Path
import subprocess
import tomllib


@dataclasses.dataclass
class RepoConfig:
    borg_repo: str
    borg_passphrase: str
    compression: str = "auto,lzma"
    target_paths: list[Path] = dataclasses.field(default_factory=lambda: [Path(".")])

    def env(self):
        return {"BORG_REPO": self.borg_repo, "BORG_PASSPHRASE": self.borg_passphrase}


class Config:
    def __init__(self, config_path: str):
        with open(config_path, "rb") as f:
            data: dict[str, list[dict[str, str | list[Path]]]] = tomllib.load(f)

        self.repos: list[RepoConfig] = []
        for repo_data in data["repos"]:
            repo_config = RepoConfig(
                repo_data["borg_repo"], repo_data["borg_passphrase"]
            )
            try:
                repo_config.compression = repo_data["compression"]
            except KeyError:
                pass
            try:
                repo_config.target_paths = repo_data["target_paths"]
            except KeyError:
                pass
            self.repos.append(repo_config)


def main(config_path: str) -> None:
    config = Config(config_path)

    for repo_config in config.repos:
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
                *repo_config.target_paths,
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
    args = parser.parse_args()

    main(args.config_path)
