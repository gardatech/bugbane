# directories
Directories under `tools` dir correspond to names of BugBane tools, BUT the build tool uses directory "builder".<br>
This is because using "build" silently disables pytest test discovery under `tests` dir, so the tool directory was renamed to match tests directory.<br>
