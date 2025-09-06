#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
from dataclasses import dataclass
from pathlib import Path
import subprocess
import tomllib


@dataclass
class RepoConfig:
    borg_repo: str
    borg_passphrase: str
    target_dir: Path = Path(".")

    def env(self):
        return {"BORG_REPO": self.borg_repo, "BORG_PASSPHRASE": self.borg_passphrase}


class Config:
    def __init__(self):
        with open("borgwrap.toml", "rb") as f:
            data: dict[str, list[dict[str, str]]] = tomllib.load(f)

        self.repos: list[RepoConfig] = []
        for repo_data in data["repos"]:
            repo_config = RepoConfig(
                repo_data["borg_repo"], repo_data["borg_passphrase"]
            )
            try:
                repo_config.target_dir = repo_data["target_dir"]
            except KeyError:
                pass
            self.repos.append(repo_config)


def main() -> None:
    config = Config()

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
                str(repo_config.target_dir),
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
    main()
