import os
import shutil

import asyncclick as click

import steak.commands
import steak.converter
import steak.images
import steak.search
import steak.tagger
import steak.uploader
from steak import cfg
from steak.common import commandgroup
from steak.errors import FilterError, LoginError, UploadError
from steak.release_notification import show_release_notification


def cleanup_tmp_dir():
    """Clean up the temporary directory if configured."""
    if cfg.directory.tmp_dir and cfg.directory.clean_tmp_dir:
        try:
            for item in os.listdir(cfg.directory.tmp_dir):
                item_path = os.path.join(cfg.directory.tmp_dir, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    click.secho(f"Failed to remove {item_path}: {e}", fg="yellow")
            click.secho(f"Cleaned temporary directory: {cfg.directory.tmp_dir}", fg="green")
        except Exception as e:
            click.secho(f"Failed to clean temporary directory: {e}", fg="yellow")


def main():
    try:
        cleanup_tmp_dir()
        show_release_notification()
        click.echo()

        commandgroup(obj={})
    except (UploadError, FilterError) as e:
        click.secho(f"There was an error: {e}", fg="red", bold=True)
    except ImportError as e:
        click.secho(f"You are missing required dependencies: {e}", fg="red")


if __name__ == "__main__":
    main()
