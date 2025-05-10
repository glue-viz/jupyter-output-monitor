def pytest_addoption(parser):
    parser.addoption(
        "--output-path",
        action="store",
        default=None,
        help="Output directory to use for tests",
    )
