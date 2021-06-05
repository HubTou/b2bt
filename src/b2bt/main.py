#!/usr/bin/env python
""" b2bt - back-to-back testing
License: 3-clause BSD (see https://opensource.org/licenses/BSD-3-Clause)
Author: Hubert Tournier
"""

import ctypes
import difflib
import getopt
import getpass
import hashlib
import locale
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
import xml.dom.minidom

# Optional dependency upon colorama
# Use "pip install colorama" to install
try:
    import colorama

    COLORAMA = True
except ModuleNotFoundError:
    COLORAMA = False

# Version string used by the what(1) and ident(1) commands:
ID = "@(#) $Id: b2bt - back-to-back testing v1.0.1 (June 5, 2021) by Hubert Tournier $"

# Default parameters. Can be overcome by environment variables, then command line options
DEFAULT_TIMEOUT = 120.0
MINIMUM_DEFAULT_TIMEOUT = 30.0
parameters = {
    "Original command path": "",
    "New command path": "",
    "Keep results": False,
    "Overwrite results": False,
    "Quiet differences": False,
    "Skip original command": False,
    "Auto confirm": False,
    "No colors": False,
    "Timeout": DEFAULT_TIMEOUT,
}


################################################################################
def display_help():
    """Displays usage and help"""
    print("usage: b2bt [--debug] [-f|--force] [--help|-?] [-k|--keep]", file=sys.stderr)
    print(
        "       [-n|--newpath PATH] [-o|--origpath PATH] [-q|--quiet] [-s|--skip]",
        file=sys.stderr,
    )
    print(
        "       [-t|--timeout VALUE] [--version] [-y|--autoconfirm] [-N|--nocolors]",
        file=sys.stderr,
    )
    print("       [--] filename [...]", file=sys.stderr)
    print(
        "  ------------------  --------------------------------------------------",
        file=sys.stderr,
    )
    print("  -f|--force          Overwrite results directories", file=sys.stderr)
    print(
        "  -k|--keep           Keep results directories after running", file=sys.stderr
    )
    print("  -n|--newpath PATH   Path of the new command", file=sys.stderr)
    print(
        "  -o|--origpath PATH  Path of the original command if not in $PATH",
        file=sys.stderr,
    )
    print("  -q|--quiet          Don't detail run differences", file=sys.stderr)
    print("  -s|--skip           Skip original command processing", file=sys.stderr)
    print(
        "  -t|--timeout VALUE  Set default timeout (%0.1f s) to a new value"
        % DEFAULT_TIMEOUT,
        file=sys.stderr,
    )
    print(
        "  -y|--autoconfirm    Don't ask for confirmation before test case execution",
        file=sys.stderr,
    )
    print("  -N|--nocolors       Don't use colors in output", file=sys.stderr)
    print("  --debug             Enable debug mode", file=sys.stderr)
    print(
        "  --help|-?           Print usage and this help message and exit",
        file=sys.stderr,
    )
    print("  --version           Print version and exit", file=sys.stderr)
    print("  --                  Options processing terminator", file=sys.stderr)
    print(file=sys.stderr)


################################################################################
def process_environment_variables():
    """Process environment variables"""
    # pylint: disable=C0103
    global parameters
    # pylint: enable=C0103

    if "B2BT_OPTIONS" in os.environ.keys():
        if "f" in os.environ["B2BT_OPTIONS"]:
            parameters["Overwrite results"] = True
        if "k" in os.environ["B2BT_OPTIONS"]:
            parameters["Keep results"] = True
        if "q" in os.environ["B2BT_OPTIONS"]:
            parameters["Quiet differences"] = True
        if "s" in os.environ["B2BT_OPTIONS"]:
            parameters["Skip original command"] = True
        if "y" in os.environ["B2BT_OPTIONS"]:
            parameters["Auto confirm"] = True
        if "N" in os.environ["B2BT_OPTIONS"]:
            parameters["No colors"] = True

    if "B2BT_DEBUG" in os.environ.keys():
        logging.disable(logging.NOTSET)

    logging.debug("process_environment_variables(): parameters:")
    logging.debug(parameters)


################################################################################
def process_command_line():
    """Process command line options"""
    # pylint: disable=C0103
    global parameters
    # pylint: enable=C0103

    # option letters followed by : expect an argument
    # same for option strings followed by =
    character_options = "dfhkn:o:qst:vyN?"
    string_options = [
        "autoconfirm",
        "debug",
        "force",
        "help",
        "keep",
        "newpath=",
        "nocolors",
        "origpath=",
        "quiet",
        "skip",
        "timeout=",
        "version",
    ]

    try:
        options, remaining_arguments = getopt.getopt(
            sys.argv[1:], character_options, string_options
        )
    except getopt.GetoptError as error:
        logging.critical("Syntax error: %s", error)
        display_help()
        sys.exit(1)

    for option, argument in options:

        if option == "--debug":
            logging.disable(logging.NOTSET)

        elif option in ("-f", "--force"):
            parameters["Overwrite results"] = True

        elif option in ("--help", "-?"):
            display_help()
            sys.exit(0)

        elif option in ("-k", "--keep"):
            parameters["Keep results"] = True

        elif option in ("-n", "--newpath"):
            if os.path.isdir(argument):
                parameters["New command path"] = os.path.abspath(argument)
            else:
                logging.critical("-n|--newpath argument is not a path")
                sys.exit(1)

        elif option in ("-o", "--origpath"):
            if os.path.isdir(argument):
                parameters["Original command path"] = os.path.abspath(argument)
            else:
                logging.critical("-o|--origpath argument is not a path")
                sys.exit(1)

        elif option in ("-q", "--quiet"):
            parameters["Quiet differences"] = True

        elif option in ("-s", "--skip"):
            parameters["Skip original command"] = True

        elif option in ("-t", "--timeout"):
            try:
                parameters["Timeout"] = float(argument)
            except ValueError:
                logging.critical("-t|--timeout argument is not a (floating) number")
                sys.exit(1)
            if parameters["Timeout"] < MINIMUM_DEFAULT_TIMEOUT:
                logging.critical(
                    "-t|--timeout argument must be >= %s seconds",
                    MINIMUM_DEFAULT_TIMEOUT,
                )
                sys.exit(1)

        elif option == "--version":
            print(ID.replace("@(" + "#)" + " $" + "Id" + ": ", "").replace(" $", ""))
            sys.exit(0)

        elif option in ("-y", "--autoconfirm"):
            parameters["Auto confirm"] = True

        elif option in ("-N", "--nocolors"):
            parameters["No colors"] = True

    logging.debug("process_command_line(): parameters:")
    logging.debug(parameters)
    logging.debug("process_command_line(): remaining_arguments:")
    logging.debug(remaining_arguments)

    return remaining_arguments


################################################################################
def is_privileged():
    """Return True if the utility is run with privileged accesses
    or if we don't know"""
    try:
        return os.geteuid() == 0
    except AttributeError:
        # Happens when not running on a Unix operating system
        # Assuming a Windows operating system:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            # Happens when on some Windows version (XP) and other operating systems
            # We return True when we don't know to stay on the safe side
            return True


################################################################################
def get_tag_lines(xml_node, tag_name):
    """Return a list of non-blank stripped lines from an XML node"""
    lines = []
    tag_content = xml_node.getElementsByTagName(tag_name)
    if tag_content:
        nodelist = tag_content[0].childNodes
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                for line in node.data.split(os.linesep):
                    if line.strip():
                        lines.append(line.strip())
    return lines


################################################################################
def read_test_case(case):
    """Check and return the contents of a test case XML node"""
    name = ""
    if case.hasAttribute("name"):
        name = case.getAttribute("name")
    timeout = str(parameters["Timeout"])
    if case.hasAttribute("timeout"):
        timeout = case.getAttribute("timeout")
    pre = get_tag_lines(case, "pre")
    stdin = get_tag_lines(case, "stdin")
    cmd = get_tag_lines(case, "cmd")
    post = get_tag_lines(case, "post")

    logging.debug("read_test_case(): name: %s", name)
    logging.debug("read_test_case(): pre: ['%s']", "', '".join(pre))
    logging.debug("read_test_case(): stdin: ['%s']", "', '".join(stdin))
    logging.debug("read_test_case(): cmd: ['%s']", "', '".join(cmd))
    logging.debug("read_test_case(): timeout: %s", timeout)
    logging.debug("read_test_case(): post: ['%s']", "', '".join(post))

    # Check the parameters:
    try:
        timeout_value = float(timeout)
    except ValueError:
        logging.critical(
            'In test case "%s": the timeout argument is not a (floating) number', name
        )
        sys.exit(1)
    if timeout_value <= 0:
        logging.critical(
            'In test case "%s": the timeout argument must be a positive number', name
        )
        sys.exit(1)
    if len(cmd) == 0:
        logging.critical('In test case "%s": a non empty cmd tag is mandatory', name)
        sys.exit(1)
    if len(cmd) > 1:
        logging.error('In test case "%s": the cmd tag must be 1 line only', name)
        sys.exit(1)

    return name, pre, stdin, cmd[0], timeout_value, post


################################################################################
def get_file_size(file_path):
    """Return a file size in bytes"""
    file_stats = os.stat(file_path)
    return file_stats.st_size


################################################################################
def get_file_digest(file_path):
    """Return a file MD5 digest in hexadecimal"""
    chunk_size = 512 * 200
    digest = hashlib.md5()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


################################################################################
def describe_test_environment(test_directory, command_full_path):
    """Generate a test 0 sub-directory with system information
    Return the command MD5 digest"""

    # Making the test directories and getting inside:
    directory = test_directory + os.sep + "0"
    if not os.path.isdir(directory):
        try:
            os.makedirs(directory)
        except OSError as error:
            logging.critical(
                'Unable to create the "%s" directory: %s', directory, error
            )
            sys.exit(1)
    os.chdir(directory)

    with open("info", "w") as file:
        file.write("System/nodename = {}{}".format(os.uname().nodename, os.linesep))
        try:
            username = getpass.getuser()
        except:
            username = ""
        file.write("System/user = {}{}".format(username, os.linesep))
        file.write("Hardware/machine = {}{}".format(platform.machine(), os.linesep))
        file.write("Hardware/processor = {}{}".format(platform.processor(), os.linesep))
        file.write("Hardware/cpus = {}{}".format(os.cpu_count(), os.linesep))
        file.write(
            "OperatingSystem/system = {}{}".format(platform.system(), os.linesep)
        )
        file.write(
            "OperatingSystem/release = {}{}".format(platform.release(), os.linesep)
        )
        file.write("Environment/locale = {}{}".format(locale.getlocale(), os.linesep))
        file.write(
            "Python/implementation = {}{}".format(
                platform.python_implementation(), os.linesep
            )
        )
        file.write(
            "Python/version = {}{}".format(platform.python_version(), os.linesep)
        )
        file.write("Command/path = {}{}".format(command_full_path, os.linesep))
        file.write(
            "Command/size = {}{}".format(get_file_size(command_full_path), os.linesep)
        )
        command_md5 = get_file_digest(command_full_path)
        file.write("Command/md5 = {}{}".format(command_md5, os.linesep))
        if shutil.which("what"):
            results = subprocess.run(
                ["what", "-q", command_full_path],
                text=True,
                capture_output=True,
                check=False,
            )
            file.write("Command/what = {}{}".format(results.stdout, os.linesep))
        if shutil.which("ident"):
            results = subprocess.run(
                ["ident", "-q", command_full_path],
                text=True,
                capture_output=True,
                check=False,
            )
            file.write("Command/ident = {}{}".format(results.stdout, os.linesep))

    os.chdir(os.pardir + os.sep + os.pardir)

    return command_md5


################################################################################
def ask_for_confirmation(text, accepted):
    """Print the text and return True if user input is in the accepted list"""
    answer = input(text)
    return answer.lower() in accepted


################################################################################
def confirm_test(pre_commands, standard_input, command_line, post_commands):
    """Return True if a test is to be executed"""
    print("    About to execute the following commands:")
    if pre_commands:
        print("      pre:")
        for line in pre_commands:
            print("        %s" % line)
    if standard_input:
        print("      stdin:")
        for line in standard_input:
            print("        %s" % line)
    print("      cmd:")
    print("        %s" % command_line)
    if post_commands:
        print("      post:")
        for line in post_commands:
            print("        %s" % line)

    return ask_for_confirmation("    Please confirm execution (y[es]): ", ("y", "yes"))


################################################################################
def execute_test(
    test_directory,
    test_number,
    pre_commands,
    standard_input,
    full_command_path,
    command_line,
    timeout,
    post_commands,
):
    """Execute a test in a subdirectory"""
    logging.debug("execute_test(): test_directory=%s", test_directory)
    logging.debug("execute_test(): test_number=%s", str(test_number))
    logging.debug("execute_test(): pre_commands=%s", " ".join(pre_commands))
    logging.debug("execute_test(): standard_input=%s", " ".join(standard_input))
    logging.debug("execute_test(): full_command_path=%s", full_command_path)
    logging.debug("execute_test(): command_line=%s", command_line)
    logging.debug("execute_test(): timeout=%d", timeout)
    logging.debug("execute_test(): post_commands=%s", " ".join(post_commands))

    # Making the test directories and getting inside:
    directory = test_directory + os.sep + str(test_number) + os.sep + "tmp"
    if not os.path.isdir(directory):
        try:
            os.makedirs(directory)
        except OSError as error:
            logging.critical(
                'Unable to create the "%s" directory: %s', directory, error
            )
            sys.exit(1)
    os.chdir(directory)

    # Executing commands defined in the "pre" section:
    for line in pre_commands:
        pre_results = subprocess.run(line, shell=True, check=False)
        if pre_results.returncode != 0:
            logging.warning(
                "Pre command '%s' returned %d", line, pre_results.returncode
            )

    # Inserting the full command path in the command line at the first command reference:
    command_basename = os.path.basename(full_command_path)
    command_dirname = os.path.dirname(full_command_path)
    line = ""
    if command_line.startswith(command_basename):
        line = command_dirname + os.sep + command_line
    elif " " + command_basename in command_line:
        line = command_line.replace(
            " " + command_basename, " " + command_dirname + os.sep + command_basename, 1
        )
    elif "\t" + command_basename in command_line:
        line = command_line.replace(
            "\t" + command_basename,
            "\t" + command_dirname + os.sep + command_basename,
            1,
        )
    elif ";" + command_basename in command_line:
        line = command_line.replace(
            ";" + command_basename, ";" + command_dirname + os.sep + command_basename, 1
        )
    logging.debug("execute_test(): modified command_line=%s", line)

    # Executing command defined in the "cmd" section, keeping results if requested:
    if not timeout:
        timeout = parameters["Timeout"]
    start_time = time.time_ns()
    try:
        if standard_input:
            one_line_input = os.linesep.join(standard_input) + os.linesep
            results = subprocess.run(
                line,
                shell=True,
                text=True,
                input=one_line_input,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        else:
            results = subprocess.run(
                line,
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
    except subprocess.TimeoutExpired as status:
        standard_output = ""
        if status.stdout:
            standard_output = status.stdout.decode("utf-8")
        standard_error_output = ""
        if status.stderr:
            standard_error_output = status.stderr.decode("utf-8")
        results = subprocess.CompletedProcess(
            status.cmd, 0, standard_output, standard_error_output
        )
    elapsed_time = time.time_ns() - start_time
    logging.debug("execute_test(): results:")
    logging.debug(results)
    if parameters["Keep results"]:
        with open(os.pardir + os.sep + "returncode", "w") as file:
            file.write(str(results.returncode))
        with open(os.pardir + os.sep + "stdout", "w") as file:
            file.write(results.stdout)
        with open(os.pardir + os.sep + "stderr", "w") as file:
            file.write(results.stderr)
        with open(os.pardir + os.sep + "time", "w") as file:
            file.write(
                "Elapsed time in s = {}{}".format(elapsed_time / 1000000000, os.linesep)
            )
            file.write("Load average = {}{}".format(os.getloadavg(), os.linesep))

    # Executing commands defined in the "post" section and collecting their output:
    post_output = ""
    for line in post_commands:
        post_results = subprocess.run(
            line, shell=True, text=True, capture_output=True, check=False
        )
        if post_results.returncode != 0:
            logging.warning(
                "Post command '%s' returned %d", line, post_results.returncode
            )
        if post_results.stdout:
            post_output = post_output + post_results.stdout
    if parameters["Keep results"]:
        with open(os.pardir + os.sep + "post", "w") as file:
            file.write(post_output)

    # Removing unneeded directories
    if parameters["Keep results"]:
        os.chdir(os.pardir)
        shutil.rmtree("tmp")
        os.chdir(os.pardir + os.sep + os.pardir)
    else:
        os.chdir(os.pardir + os.sep + os.pardir + os.sep + os.pardir)
        shutil.rmtree(test_directory)

    return results, post_output


################################################################################
def load_previous_results(test_directory, test_number):
    """Load results from a previous run
    Return a CompletedProcess object and a text string"""

    if not os.path.isdir(test_directory + os.sep + str(test_number)):
        return None, ""

    with open(
        test_directory + os.sep + str(test_number) + os.sep + "returncode", "r"
    ) as file:
        returncode = int(file.readline())
    with open(
        test_directory + os.sep + str(test_number) + os.sep + "stdout", "r"
    ) as file:
        stdout = file.read()
    with open(
        test_directory + os.sep + str(test_number) + os.sep + "stderr", "r"
    ) as file:
        stderr = file.read()
    with open(
        test_directory + os.sep + str(test_number) + os.sep + "post", "r"
    ) as file:
        post = file.read()

    return subprocess.CompletedProcess([], returncode, stdout, stderr), post


################################################################################
def color_print(text, color):
    """Print a text in color if possible"""
    if COLORAMA and not parameters["No colors"]:
        print(color + text + colorama.Style.RESET_ALL)
    else:
        print(text)


################################################################################
def remind_command(same_command, command):
    """Print the command tested on the first difference encountered"""
    if same_command:
        same_command = False
        if not parameters["Quiet differences"]:
            print("    Command:")
            print("      %s" % command)
    return same_command


################################################################################
def main():
    """The program's main entry point"""
    program_name = os.path.basename(sys.argv[0])
    console_log_format = program_name + ": %(levelname)s: %(message)s"
    logging.basicConfig(format=console_log_format, level=logging.DEBUG)
    logging.disable(logging.INFO)

    process_environment_variables()
    arguments = process_command_line()

    if len(arguments) == 0:
        logging.warning("Please specify at least 1 test file to process")
        display_help()
        sys.exit(0)

    if is_privileged():
        print("It's not recommended to run this utility as a privileged user")
        print(
            "and you should definitely avoid doing so when running unverified test suites!"
        )
        if not parameters["Auto confirm"]:
            print(
                "However you'll get the chance to review each command to be executed..."
            )
            if not ask_for_confirmation(
                "Please confirm execution (y[es]): ", ("y", "yes")
            ):
                print("Better safe than sorry!")
                sys.exit(0)

    for filename in arguments:
        if not os.path.isfile(filename):
            logging.error("'%s' is not a file name", filename)
        else:
            try:
                test_file = xml.dom.minidom.parse(filename)
            except xml.parsers.expat.ExpatError as error:
                logging.critical("XML file error: %s", error)
                sys.exit(1)

            # Get the root element of the document:
            test_suite = test_file.documentElement

            # Get the name of the program we'll be testing:
            program_tested = os.path.basename(filename).replace(".xml", "")
            if test_suite.hasAttribute("program"):
                program_tested = test_suite.getAttribute("program").strip()
            color_print("Testing the '%s' command:" % program_tested, colorama.Style.BRIGHT)

            # Determine if the original command will have to be executed:
            execute_original_command = False
            original_command_full_path = ""
            if not parameters["Skip original command"]:
                if (
                    not os.path.isdir(program_tested + ".orig")
                    or parameters["Overwrite results"]
                ):
                    execute_original_command = True
                    if parameters["Original command path"] == "":
                        original_command_full_path = shutil.which(program_tested)
                    else:
                        original_command_full_path = shutil.which(
                            program_tested, path=parameters["Original command path"]
                        )
                    if original_command_full_path is None:
                        logging.critical("Original command not found")
                        sys.exit(1)
                    else:
                        logging.debug(
                            "Original command found at: %s", original_command_full_path
                        )

            # Determine if the new command will have to be executed:
            execute_new_command = False
            new_command_full_path = ""
            if parameters["New command path"] != "":
                if (
                    not os.path.isdir(program_tested + ".new")
                    or parameters["Overwrite results"]
                ):
                    execute_new_command = True
                    new_command_full_path = shutil.which(
                        program_tested, path=parameters["New command path"]
                    )
                    if new_command_full_path is None:
                        logging.critical("New command not found")
                        sys.exit(1)
                    else:
                        logging.debug("New command found at: %s", new_command_full_path)

            # Get all the test cases in the test suite:
            test_cases = test_suite.getElementsByTagName("test-case")

            # If we are to keep results, note some system information for next time & place we'll make comparisons:
            original_command_md5 = ""
            new_command_md5 = ""
            if parameters["Keep results"]:
                if execute_original_command:
                    original_command_md5 = describe_test_environment(
                        program_tested + ".orig", original_command_full_path
                    )
                if execute_new_command:
                    new_command_md5 = describe_test_environment(
                        program_tested + ".new", new_command_full_path
                    )

            # But at the minimum check that we are not testing the same command:
            else:
                if execute_original_command:
                    original_command_md5 = get_file_digest(original_command_full_path)
                if execute_new_command:
                    new_command_md5 = get_file_digest(new_command_full_path)
            if original_command_md5 == new_command_md5:
                logging.warning("The commands are the same! Disabling new command run")
                execute_new_command = False

            # Process each test case:
            test_number = 0
            skipped_count = 0
            different_count = 0
            same_count = 0
            for test_case in test_cases:
                test_name, pre, stdin, cmd, timeout, post = read_test_case(test_case)
                test_number += 1
                print('  Test #{} "{}"'.format(test_number, test_name))

                # Confirm test execution (in case you are not the author of the test suite):
                if not parameters["Auto confirm"]:
                    if not confirm_test(pre, stdin, cmd, post):
                        color_print("    Skipping test", colorama.Fore.YELLOW)
                        skipped_count += 1
                        continue

                # Execute tests:
                results1 = None
                if execute_original_command:
                    results1, post_output1 = execute_test(
                        program_tested + ".orig",
                        test_number,
                        pre,
                        stdin,
                        original_command_full_path,
                        cmd,
                        timeout,
                        post,
                    )
                elif not parameters["Skip original command"]:
                    results1, post_output1 = load_previous_results(
                        program_tested + ".orig", test_number
                    )
                results2 = None
                if execute_new_command:
                    results2, post_output2 = execute_test(
                        program_tested + ".new",
                        test_number,
                        pre,
                        stdin,
                        new_command_full_path,
                        cmd,
                        timeout,
                        post,
                    )

                # Compare tests results:
                if results1 and results2:
                    same = True
                    if results1.returncode != results2.returncode:
                        same = remind_command(same, cmd)
                        color_print(
                            "    Return codes are different!",
                            colorama.Fore.RED + colorama.Style.BRIGHT,
                        )
                        if not parameters["Quiet differences"]:
                            print("      Original = {}".format(results1.returncode))
                            print("      New = {}".format(results2.returncode))
                    if results1.stdout != results2.stdout:
                        same = remind_command(same, cmd)
                        color_print(
                            "    Standard output is different!",
                            colorama.Fore.RED + colorama.Style.BRIGHT,
                        )
                        if not parameters["Quiet differences"]:
                            diff = difflib.unified_diff(
                                str(results1.stdout).split(os.linesep),
                                str(results2.stdout).split(os.linesep),
                                fromfile="Original stdout",
                                tofile="New stdout",
                            )
                            for line in diff:
                                print(line)
                    if results1.stderr != results2.stderr:
                        same = remind_command(same, cmd)
                        color_print(
                            "    Standard error output is different!",
                            colorama.Fore.RED + colorama.Style.BRIGHT,
                        )
                        if not parameters["Quiet differences"]:
                            diff = difflib.unified_diff(
                                str(results1.stderr).split(os.linesep),
                                str(results2.stderr).split(os.linesep),
                                fromfile="Original stderr",
                                tofile="New stderr",
                            )
                            for line in diff:
                                print(line)
                    if post_output1 != post_output2:
                        same = remind_command(same, cmd)
                        color_print(
                            "    Post commands output is different!",
                            colorama.Fore.RED + colorama.Style.BRIGHT,
                        )
                        if not parameters["Quiet differences"]:
                            diff = difflib.unified_diff(
                                str(post_output1).split(os.linesep),
                                str(post_output2).split(os.linesep),
                                fromfile="Original post output",
                                tofile="New post output",
                            )
                            for line in diff:
                                print(line)
                    if same:
                        same_count += 1
                        color_print("    Same results", colorama.Fore.GREEN)
                    else:
                        different_count += 1

            # Print test suite results:
            if not parameters["Skip original command"] and execute_new_command:
                color_print("Results:", colorama.Style.BRIGHT)
                if different_count:
                    color_print(
                        "  {} out of {} test cases have different results".format(
                            different_count, same_count + different_count
                        ),
                        colorama.Style.BRIGHT,
                    )
                else:
                    color_print(
                        "  All {} test cases have the same results".format(same_count),
                        colorama.Fore.GREEN,
                    )
                if skipped_count:
                    color_print(
                        "  {} test cases skipped".format(skipped_count),
                        colorama.Fore.YELLOW,
                    )

    sys.exit(0)


if __name__ == "__main__":
    main()
