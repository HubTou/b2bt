# B2BT(5)

## NAME
b2bt XML files - back-to-back testing utility's format for test suites

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
  in an automatically generated test sub directory. We call this "pre" commands.
* optional standard input to be injected in the command tested
* mandatory one line shell command-line for the command to be tested
* optional shell commands to execute after the test, typically to analyze the tested command
  impact on the test environment. The output of these "post" commands is captured before
  automatic removal of the test sub directory

Each test case can have a name and a potential timeout (in seconds or fraction of seconds).

A b2bt XML file starts with a line indicating the XML version we use:
```XML
<?xml version="1.0"?>
```

Then, all the rest of the file is enclosed between 1 test-suite pair of tags: 
```XML
<test-suite program="COMMAND" processor="b2bt B2BT_VERSION" ID="@(#) $Id: COMMAND.xml - back to back test suite for COMMAND vVERSION (DATE) by AUTHOR $">
</test-suite>
```
Where:
* **COMMAND** is the name of the command to be tested
* **VERSION** is the version of the test suite
* **DATE** is the date of last modification to the file
* **AUTHOR** is the test suite author's name
* **B2BT_VERSION** is the minimal version required of **b2bt** required to process this file, or 1.0.0 if missing

You can then have 1 or more test-cases enclosed between test-case pair of tags:
```XML
<test-case name="CASE_NAME" timeout="TIMEOUT">
  <cmd>
    COMMAND
  </cmd>
</test-case>
```
Where:
* The **name** attribute is optional but recommended. If you don't provide it, the test will be referred to by its order rank in the file (starting at 1)
* The **timeout** attribute is optional and it's recommended NOT to use it, unless you have a good reason to do so. It takes a positive value, with an eventual decimal part, expressed in seconds. Whatever the Locale you are using, the decimal separator is the "." character
* **CASE_NAME** is a short string describing the test case
* **COMMAND** is the command to be shell executed:
  * the **cmd** tag expects exactly one line. Leading or trailing spaces and newline characters are stripped unless enclosed between double quotes
  * the command itself must be pathless. b2bt will replace the first occurrence it founds with the absolute path of the original or new command to be tested
  * the command is executed by a Shell. Its output can be piped to another command or redirected to a file, and it can be prefixed by environment variables definition
* There are 2 characters that you must escape in all XML tag contents:
  * The ampersand (&) is to be replaced by &amp;amp;
  * The "less than" operator (<) is to be replaced by &amp;lt;
* Also remember that, at least, the [predefined XML entities](https://en.wikipedia.org/wiki/List_of_XML_and_HTML_character_entity_references#Predefined_entities_in_XML) will be replaced in your tag contents. The 2 previous ones, plus:
  * &amp;quot; for the quote (")
  * &amp;apos; for the apostrophe (')
  * &amp;gt; for the "greater than" operator (>)

Apart from the mandatory **cmd** tags, a test-case can also include the following optional tags:
```XML
<test-case name="CASE_NAME" timeout="TIMEOUT">
  <pre>
    PRE_COMMANDS
  </pre> 
  <stdin>
    INPUT_LINES
  </stdin> 
  <cmd>
    COMMAND
  </cmd>
  <post>
    POST_COMMANDS
  </post> 
</test-case>
```
Where:
* **PRE_COMMANDS** is 0 to N lines of commands to be shell executed before the command to be tested:
  * These commands are independent from each other. This is not a shell script! Peculiarly, you can't use "here documents" or environment variables definition affecting succeeding lines...
  * This section is intended to create any files or directories with associated content needed for the test case. It will be executed twice, for the original and the new command, so that each one runs in a fresh environment
* **POST_COMMANDS** does the same, except its commands are executed after the command to be tested and their output is collected for later comparisons:
  * This section is intended to check additional effects of the command tested, for example in terms of files/directories creation/modification/deletion, execution duration, etc.
  * The temporary directory where the test happens will automatically be cleaned, and this doesn't need to be addressed by the user
* **INPUT_LINES** is 0 to N lines of text to be injected as standard input into the command to be tested. Again, leading or trailing spaces and newline characters are stripped

If you want portable test suites, please make sure that all commands you use
in the pre, cmd and post sections are available in all the operating systems
that you target...

## EXAMPLES
A minimal test suite would be:
```XML
<?xml version="1.0"?>
<test-suite program="basename" processor="b2bt" ID="@(#) $Id: basename.xml - back to back test suite for basename v1.0.0 (May 30, 2021) by Hubert Tournier $">
  <test-case name="Typical usage - removing directories and file extension">
    <cmd>
      basename /directory1/directory2/file1.ext .ext
    </cmd>
  </test-case>
</test-suite>
```

Another more sophisticated test suite would be:
```XML
<?xml version="1.0"?>
<test-suite program="cat" processor="b2bt" ID="@(#) $Id: cat.xml - back to back test suite for cat v1.0.0 (May 30, 2021) by Hubert Tournier $">
  <test-case name="Concatenate 2 files">
    <pre>
      printf "%s\n%s\n%s\n" a b c > 1
      printf "%s\n%s\n%s\n" d e f > 2
    </pre>
    <cmd>
      cat 1 2
    </cmd>
    <post>
     find .
     echo
     cat 1
     echo
     cat 2
    </post>
  </test-case>

  <test-case name="Basic filter - process standard input">
    <stdin>
      a
      b
      c
    </stdin>
    <cmd>
      cat
    </cmd>
  </test-case>
</test-suite>
```

## SEE ALSO
[b2bt(1)](https://github.com/HubTou/b2bt/blob/main/README.md)

## HISTORY
These files were made for the [PNU project](https://github.com/HubTou/PNU)
in order to test the rewritten commands against the installed ones.

This project will provide [b2bt test files for the usual POSIX and FreeBSD commands](https://github.com/HubTou/PNU/tree/main/tests).

## AUTHORS
[Hubert Tournier](https://github.com/HubTou)

