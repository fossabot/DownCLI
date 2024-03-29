"""
CLI-based downloader
"""
import os.path
import sys
from concurrent.futures import as_completed, ThreadPoolExecutor
import signal
from functools import partial
from threading import Event
from typing import Iterable
import requests
from rich import print as printf
from rich.progress import *

progress = Progress(
    TextColumn("[{task.fields[responsecode]}] <[bold yellow]{task.fields[contenttype]}[/]> [bold blue]{task.fields[filename]}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
    TimeElapsedColumn(),
    SpinnerColumn()
)


done_event = Event()


def handle_sigint(signum, frame):
    done_event.set()


signal.signal(signal.SIGINT, handle_sigint)


def copy_url(task_id: TaskID, url: str, path: str) -> None:
    """Copy data from a url to a local file."""
    
    progress.console.log(f"Requesting {url}")
    response = requests.get(url, stream=True)
    meta = requests.head(url)
    if "Content-Length" in meta.headers:
        progress.update(task_id, total=int(meta.headers["Content-Length"]))
    else:
        progress.update(task_id, total=int(len(response.content)))
    with open(path, "wb") as dest_file:
        progress.start_task(task_id)
        for data in response.iter_content(32768):
            dest_file.write(data)
            progress.update(task_id, advance=len(data))
            if done_event.is_set():
                return
    progress.console.log(f"Downloaded {path}")


def download(urls: Iterable[str], dest_dir: str):
    """Download multuple files to the given directory."""

    with progress:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for url in urls:
                filename = url.split("/")[-1]
                response = requests.head(url)
                contenttype = response.headers['Content-Type'].split(';')[0]
                if contenttype == "text/plain":
                    filename += '.txt'
                dest_path = os.path.join(dest_dir, filename)
                if response.status_code == requests.codes.ok:
                    responsecode = f"[green]{str(response.status_code)}[/]"
                else:
                    responsecode = f"[red]{str(response.status_code)}[/]"
                task_id = progress.add_task("download", filename=filename, contenttype=contenttype, responsecode=responsecode, start=False)
                pool.submit(copy_url, task_id, url, dest_path)
                # printf(f"[red]ERROR![/]\n[yellow]Status Code[/]: [red]{respone.status_code}[/] caused by [yellow]{url}[/]\n")

def print_help_msg():
    """Prints help message"""
    
    printf("""CLI-based downloader written in Python
\tUsage: [bold green]python[/] [blue]downloader[/].[green]py[/] [[italic]-h, --help[/]] [[italic]-d, --directory[/] [bold purple]DIRECTORY[/]] [yellow]URL[/] [[italic purple]URL2 URL3 ... etc[/]]

Optional Argument:
 [yellow]-h[/], [yellow]--help[/]                |  Prints [purple]help[/] message and [yellow]exits[/]
 [yellow]-d[/], [yellow]--directory[/] [bold italic]DIRECTORY[/] |  Downloads files in [purple]DIRECTORY[/] instead of default [yellow]./[/]
 """)

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        if sys.argv[1] in ["-h", "--help"]:
            print_help_msg()
            download(sys.argv[2:], "./")
        elif sys.argv[1] in ["-d", "--directory"]:
            download(sys.argv[3:], sys.argv[2])
        else:
            download(sys.argv[1:], "./")
    else:
        print_help_msg()
