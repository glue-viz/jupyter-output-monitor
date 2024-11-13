import click

from ._monitor import monitor_group
from ._report import report_group

main = click.CommandCollection(sources=[monitor_group, report_group])

if __name__ == "__main__":
    main()
