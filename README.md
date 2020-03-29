# Workflow log parser

## How to run parser?

You can use optional run parameters:
- -s - to specify logs source directory (by default `logs-hf` is set)
- -d - to specify logs destination directory (by default `./` is set)
- -f - to specify `file-sizes.log` file directory (by default `logs-hf` is set)

e.g.
`python3 parser.py -s logs-hf -d parsed-logs -f logs-hf`
