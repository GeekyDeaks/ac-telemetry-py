# AC Telemetry

Crude Assetto Corsa Telemetry logger, written specifically to address the lack of tools for the PS4/XB1

# get started

    python3 logger.py [IP address]

This will intiate the telemetry feed from an instance of AC running on the target IP.
It will log telemetry per lap into a subdirectory of the `log` directory, 
with one row per approximate meter travelled and a summary `laps.txt`

If the session is restarted, the logger should create a new sub-directory for the new set
of laps.  If you completely exit the session, it should detect the lack of updates and
stop the logging

# plotting

To plot you will need to install the [bokeh](https://docs.bokeh.org/en/latest/index.html) module. I recommend creating a `venv` e.g.

    python3 -m venv py
    py/bin/pip install bokeh numpy

The run the plot within the venv:

    py/bin/python plot-example-split.py

or

    py/bin/python plot.py [lap1] [lap2] -o output.html

This will create an output html file that looks something like this:

![example-split](example-split.png)

The plot uses `lap1` as the reference lap, so the `delta` is the amount `lap2` is ahead (-ve) or behind (+ve).
You can click on the legends to mute any trace and the bottom slider allows you to narrow down the
analysis to a specific range of measurements

# reference

* https://docs.google.com/document/d/1KfkZiIluXZ6mMhLWfDX1qAGbvhGRC3ZUzjVIt5FQpp4/pub
* https://docs.bokeh.org/en/latest/index.html