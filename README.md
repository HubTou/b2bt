# Installation
pip install [pnu-b2bt](https://pypi.org/project/pnu-b2bt/)

# B2BT(1)

## NAME
b2bt - back-to-back testing

## SYNOPSIS
**b2bt**
\[-f|--force\]
\[-k|--keep\]
\[-n|--newpath PATH\]
\[-o|--origpath PATH\]
\[-q|--quiet\]
\[-s|--skip\]
\[-t|--timeout VALUE\]
\[-y|--autoconfirm\]
\[-N|--nocolors\]
\[--debug\]
\[--help|-?\]
\[--version\]
\[--\]
filename \[...\]

## DESCRIPTION
The **b2bt** utility aims to automate:
* back-to-back testing (testing a command-line utility against another implementation)
* non regression testing (testing a command-line utility against a previous version)

It processes one or more [XML](https://en.wikipedia.org/wiki/XML) files describing the test suite for a command-line utility,
with its different test cases, execute the 2 commands versions and report potential
differences (on return codes, standard output, standard error output, plus custom post
processing output in order to check other kind of impacts, on file systems, execution time, etc.).

In a test suite it is possible to specify:
* optional shell commands to execute before the test, typically to setup the test environment
  in an automatically generated test sub directory
* optional standard input to be injected in the command tested
* mandatory one line shell command-line for the command to be tested
* optional shell commands to execute after the test, typically to analyze the tested command
  impact on the test environment. The output of these "post" commands is captured before
  automatic removal of the test sub directory

Each test case can have a name and a potential timeout (in seconds or fraction of seconds).

By defaut, this utility:
* executes the original command, unless you use the **-s** option to skip it (useful when you are testing the new command on another system);
* executes the original command from the PATH, unless you use the **-o** option to specify another location;
* uses a 120.0 s timeout for commands execution, unless you use the **-t** option to modify it;
* discards the test results after each comparison, unless you use the **-k** option to keep them;
* details the differences between the 2 commands runs, unless you use the **-q** option to limit it;
* does not execute again tests when you have kept previous results, unless you use the **-f** option to overwrite them;
* asks for confirmation before each test case execution, unless you use the **-y** option to auto confirm them;
* uses ANSI colours in the output, unless you use the **-N** option to disable it;
* does not execute the new command if it has the same [MD5](https://en.wikipedia.org/wiki/MD5) digest than the original one.

The new command location has to be specified with the -n option if you want a comparison to occur.

### OPTIONS
Options | Use
------- | ---
-f\|--force|Overwrite results directories
-k\|--keep|Keep results directories after running
-n\|--newpath PATH|Path of the new command
-o\|--origpath PATH|Path of the original command if not in $PATH
-q\|--quiet|Don't detail run differences
-s\|--skip|Skip original command processing
-t\|--timeout VALUE|Set default timeout (120.0 s) to a new value, with a 30.0 s minimum
-y\|--autoconfirm|Don't ask for confirmation before test case execution
-N\|--nocolors|Don't use colors in output
--debug|Enable debug mode
--help\|-?|Print usage and a short help message and exit
--version|Print version and exit
--|Options processing terminator

## ENVIRONMENT
The B2BT_OPTIONS environment variable can be set with a combination of the following command-line options letters:
* **f** in order to overwrite results directories if they exist
* **k** in order to keep results directories after running
* **q** in order to disable details in run differences
* **s** in order to skip original command processing
* **y** in order to answer yes to all confirmation requests
* **N** in order to disable colors in output

The B2BT_DEBUG environment variable can also be set to any value to enable debug mode.

These 2 environment variables are superseded by command line options.

## FILES
The format of the XML files processed is described in the [b2bt(5)](https://github.com/HubTou/b2bt/blob/main/README.5.md) manual page.

## EXIT STATUS
The b2bt utility exits 0 on success, and >0 if an error occurs.

## SEE ALSO
[b2bt(5)](https://github.com/HubTou/b2bt/blob/main/README.5.md)

## STANDARDS
The b2bt utility is not a standard UNIX/POSIX command.

It tries to follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for [Python](https://www.python.org/) code.

## PORTABILITY
To be tested under Windows.

## HISTORY
This utility was made for [The PNU project / PyNIX](https://github.com/HubTou/PNU)
in order to test the rewritten commands against the installed ones.

## LICENSE
This utility is available under the [3-clause BSD license](https://opensource.org/licenses/BSD-3-Clause).

## AUTHORS
[Hubert Tournier](https://github.com/HubTou)

## CAVEATS
If you are comparing commands execution across operating systems, for example between Unix-like and Windows systems,
the output might be different due to the path separators ("/" versus "\\").

Comparing timeout interrupted commands output is hazardous...

## SECURITY CONSIDERATIONS
This utility processes XML files describing commands to be shell executed on your system.
If you are not the author of a test suite or are using an untrusted source, this can be dangerous!

To mitigate the risks, the utility will:
* Warn you if you are using a privileged account and advise you not to do so.
* Show you every command to be executed and ask for prior confirmation.

We also use the standard Python [xml.dom.minidom](https://docs.python.org/3/library/xml.dom.minidom.html) library which is known to be [vulnerable to several XML attacks](https://pypi.org/project/defusedxml/).

Visual inspection of the XML files to process is recommended, and useful anyway if you are rewriting an existing command.

The program is using MD5 file digests but not for security purposes.
It is also calling the [what(1)](https://www.freebsd.org/cgi/man.cgi?query=what) and [ident(1)](https://www.freebsd.org/cgi/man.cgi?query=ident) commands from their PATH location, if they are available, assuming system directories precede user directories in the PATH.
